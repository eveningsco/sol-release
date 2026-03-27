"""GitHub API integration for SOL release management.

This module provides real GitHub API interactions for:
- Creating releases
- Downloading release assets
- Managing release history
- Fetching component metadata
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


class GitHubAPIError(Exception):
    """Exception raised for GitHub API errors."""
    pass


class GitHubReleaseManager:
    """Manages GitHub releases for the SOL ecosystem."""

    def __init__(
        self,
        token: str,
        owner: str = "eveningsco",
        repo: str = "sol-release"
    ):
        """Initialize the GitHub release manager.
        
        Args:
            token: GitHub personal access token with repo scope
            owner: GitHub repository owner (default: eveningsco)
            repo: GitHub repository name (default: sol-release)
        """
        self.token = token
        self.owner = owner
        self.repo = repo
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }

    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a GitHub API request.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/repos/{owner}/{repo}/releases")
            data: Request body data
            
        Returns:
            Response data as dictionary
            
        Raises:
            GitHubAPIError: If API request fails
        """
        url = f"{self.api_base}{endpoint}"
        request = Request(url, headers=self.headers, method=method)
        
        if data:
            request.data = json.dumps(data).encode("utf-8")

        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            error_data = json.loads(e.read().decode("utf-8")) if e.fp else {}
            raise GitHubAPIError(
                f"GitHub API error {e.code}: {error_data.get('message', str(e))}"
            )
        except URLError as e:
            raise GitHubAPIError(f"Network error: {e.reason}")

    def create_release(
        self,
        tag_name: str,
        name: str,
        body: str,
        draft: bool = False,
        prerelease: bool = True
    ) -> Dict[str, Any]:
        """Create a new GitHub release.
        
        Args:
            tag_name: Git tag for the release
            name: Release title/name
            body: Release body text
            draft: Whether to create as draft (default: False)
            prerelease: Whether to create as prerelease (default: True)
            
        Returns:
            Release data dictionary
        """
        release_data = {
            "tag_name": tag_name,
            "name": name,
            "body": body,
            "draft": draft,
            "prerelease": prerelease
        }

        response = self._make_request(
            "POST",
            f"/repos/{self.owner}/{self.repo}/releases",
            release_data
        )

        return response

    def list_releases(
        self,
        per_page: int = 30,
        page: int = 1
    ) -> List[Dict[str, Any]]:
        """List all releases for the repository.
        
        Args:
            per_page: Number of releases per page (default: 30)
            page: Page number (default: 1)
            
        Returns:
            List of release data dictionaries
        """
        params = f"?per_page={per_page}&page={page}"
        response = self._make_request("GET", f"/repos/{self.owner}/{self.repo}/releases{params}")
        return response

    def get_release(self, release_id: int) -> Dict[str, Any]:
        """Get a specific release by ID.
        
        Args:
            release_id: GitHub release ID
            
        Returns:
            Release data dictionary
        """
        return self._make_request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/releases/{release_id}"
        )

    def get_release_by_tag(self, tag_name: str) -> Optional[Dict[str, Any]]:
        """Get a release by its tag name.
        
        Args:
            tag_name: Git tag name to search for
            
        Returns:
            Release data dictionary or None if not found
        """
        releases = self.list_releases(per_page=100)
        for release in releases:
            if release.get("tag_name") == tag_name:
                return release
        return None

    def delete_release(self, release_id: int) -> bool:
        """Delete a release by ID.
        
        Args:
            release_id: GitHub release ID
            
        Returns:
            True if deletion successful
            
        Raises:
            GitHubAPIError: If deletion fails
        """
        self._make_request(
            "DELETE",
            f"/repos/{self.owner}/{self.repo}/releases/{release_id}"
        )
        return True

    def cleanup_old_releases(self, keep_count: int = 5) -> List[Dict[str, Any]]:
        """Remove old releases keeping only the most recent ones.
        
        Args:
            keep_count: Number of recent releases to keep (default: 5)
            
        Returns:
            List of deleted release information
        """
        all_releases = self.list_releases(per_page=100)
        
        # Sort by creation date (newest first)
        sorted_releases = sorted(
            all_releases,
            key=lambda r: r.get("created_at", ""),
            reverse=True
        )

        releases_to_delete = sorted_releases[keep_count:]
        deleted_releases = []

        for release in releases_to_delete:
            try:
                self.delete_release(release["id"])
                deleted_releases.append({
                    "id": release["id"],
                    "tag": release.get("tag_name", ""),
                    "name": release.get("name", "")
                })
            except GitHubAPIError as e:
                # Log error but continue with other deletions
                print(f"Failed to delete release {release['id']}: {e}")

        return deleted_releases

    def get_release_assets(self, release_id: int) -> List[Dict[str, Any]]:
        """Get all assets for a specific release.
        
        Args:
            release_id: GitHub release ID
            
        Returns:
            List of asset data dictionaries
        """
        return self._make_request(
            "GET",
            f"/repos/{self.owner}/{self.repo}/releases/{release_id}/assets"
        )

    def download_asset(
        self,
        asset_id: int,
        destination: str
    ) -> str:
        """Download a release asset to a local file.
        
        Args:
            asset_id: GitHub asset ID
            destination: Local file path to save the asset
            
        Returns:
            Path to downloaded file
            
        Raises:
            GitHubAPIError: If download fails
        """
        url = f"https://github.com/{self.owner}/{self.repo}/releases/download/{asset_id}"
        headers = {"Accept": "application/octet-stream"}
        
        request = Request(url, headers=headers)
        
        try:
            with urlopen(request) as response:
                with open(destination, "wb") as f:
                    f.write(response.read())
                return destination
        except HTTPError as e:
            raise GitHubAPIError(f"Failed to download asset {asset_id}: {e}")

    def cleanup_assets(
        self,
        keep_count: int = 100,
        pattern: Optional[str] = None
    ) -> List[int]:
        """Remove old assets from releases, keeping only the most recent ones.
        
        Args:
            keep_count: Number of assets to keep per release
            pattern: Optional pattern to filter assets (e.g., "*.zip")
            
        Returns:
            List of deleted asset IDs
        """
        all_releases = self.list_releases(per_page=100)
        deleted_asset_ids = []

        for release in all_releases:
            assets = self.get_release_assets(release["id"])
            
            if pattern:
                assets = [a for a in assets if pattern in a.get("name", "")]

            if len(assets) > keep_count:
                assets_to_delete = assets[keep_count:]
                for asset in assets_to_delete:
                    try:
                        self._make_request(
                            "DELETE",
                            f"/repos/{self.owner}/{self.repo}/releases/assets/{asset['id']}"
                        )
                        deleted_asset_ids.append(asset["id"])
                    except GitHubAPIError as e:
                        print(f"Failed to delete asset {asset['id']}: {e}")

        return deleted_asset_ids


class ComponentMetadataFetcher:
    """Fetches metadata from component repository releases."""

    COMPONENT_MAP = {
        "sol-software": {
            "owner": "eveningsco",
            "repo": "sol-software",
            "event_type": "sol_software_release"
        },
        "sol-server": {
            "owner": "eveningsco",
            "repo": "sol-server",
            "event_type": "sol_server_release"
        },
        "sol-utils": {
            "owner": "eveningsco",
            "repo": "sol-utils",
            "event_type": "sol_utils_release"
        }
    }

    def __init__(self, token: str):
        """Initialize the component metadata fetcher.
        
        Args:
            token: GitHub personal access token
        """
        self.token = token
        self.api_base = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def _make_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a GitHub API request."""
        request = Request(url, headers=self.headers, method=method)
        
        if data:
            request.data = json.dumps(data).encode("utf-8")

        try:
            with urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as e:
            error_text = e.read().decode("utf-8") if e.fp and e.read(1) != b'' else ""
            try:
                error_data = json.loads(error_text) if error_text else {}
            except json.JSONDecodeError:
                error_data = {}
            raise GitHubAPIError(
                f"GitHub API error {e.code}: {error_data.get('message', str(e))}"
            )
        except URLError as e:
            raise GitHubAPIError(f"Network error: {e.reason}")

    def get_latest_release(self, component: str) -> Optional[Dict[str, Any]]:
        """Get the latest release for a component repository.
        
        Args:
            component: Component name (e.g., "sol-software", "sol-server")
            
        Returns:
            Latest release data or None if not found
        """
        if component not in self.COMPONENT_MAP:
            raise ValueError(f"Unknown component: {component}")

        config = self.COMPONENT_MAP[component]
        url = f"{self.api_base}/repos/{config['owner']}/{config['repo']}/releases/latest"

        try:
            response = self._make_request("GET", url)
            return response
        except GitHubAPIError as e:
            print(f"Failed to get latest release for {component}: {e}")
            return None

    def fetch_component_metadata(self, component: str) -> Optional[Dict[str, Any]]:
        """Fetch complete metadata for a component's latest release.
        
        Args:
            component: Component name (e.g., "sol-software")
            
        Returns:
            Component metadata dictionary or None
        """
        release = self.get_latest_release(component)
        if not release:
            return None

        config = self.COMPONENT_MAP[component]

        # Extract metadata fields
        metadata = {
            "component": component,
            "included": True,
            "branch": release.get("target_commitish", ""),
            "commit_sha": release.get("target_commitish", ""),
            "tag_name": release.get("tag_name", ""),
            "release_url": release.get("html_url", ""),
            "pr_number": None  # Not available in release data
        }

        # Try to extract PR number from body (if present)
        body = release.get("body", "")
        if "PR #" in body:
            import re
            match = re.search(r"PR #(\d+)", body)
            if match:
                metadata["pr_number"] = match.group(1)

        return metadata

    def fetch_all_component_metadata(self) -> Dict[str, Any]:
        """Fetch metadata for all supported components.
        
        Returns:
            Dictionary mapping component names to their metadata
        """
        all_metadata = {}

        for component in self.COMPONENT_MAP:
            metadata = self.fetch_component_metadata(component)
            if metadata:
                all_metadata[component] = metadata

        return all_metadata


class ReleaseWorkflowOrchestrator:
    """Orchestrates the complete release workflow using GitHub API.
    
    This class combines release management, artifact downloading,
    and metadata collection into a cohesive workflow.
    """

    def __init__(
        self,
        github_token: str,
        owner: str = "eveningsco",
        repo: str = "sol-release"
    ):
        """Initialize the release workflow orchestrator.
        
        Args:
            github_token: GitHub personal access token
            owner: Repository owner
            repo: Repository name
        """
        self.release_manager = GitHubReleaseManager(github_token, owner, repo)
        self.component_fetcher = ComponentMetadataFetcher(github_token)
        self.workflow_steps: List[str] = []

    def log_step(self, step: str):
        """Log a workflow step."""
        self.workflow_steps.append(step)
        print(f"[{step}]")

    def create_release_from_components(
        self,
        components: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a release with metadata from components.
        
        Args:
            components: Optional component metadata dictionary.
                       If None, fetches from component repos.
                       
        Returns:
            Created release information
        """
        self.log_step("Starting release creation workflow")

        # Fetch component metadata if not provided
        if components is None:
            self.log_step("Fetching component metadata from repositories")
            components = self.component_fetcher.fetch_all_component_metadata()

        if not components:
            raise GitHubAPIError("No component metadata available")

        # Generate release body
        body = self._generate_release_body(components)
        
        # Create release version
        timestamp = datetime.now(timezone.utc).strftime("%m%d%Y_%H-%M-%S")
        release_name = f"Release-{timestamp}"
        tag_name = release_name

        self.log_step(f"Creating release: {release_name}")

        # Create the release
        release = self.release_manager.create_release(
            tag_name=tag_name,
            name=release_name,
            body=body,
            prerelease=True
        )

        self.log_step(f"Release created: {release.get('html_url', 'N/A')}")

        return {
            "release": release,
            "components": components,
            "steps": self.workflow_steps
        }

    def _generate_release_body(self, components: Dict[str, Any]) -> str:
        """Generate release body text from component metadata.
        
        Args:
            components: Component metadata dictionary
            
        Returns:
            Release body string
        """
        lines = []
        lines.append("Combined SOL release package")
        lines.append(f"Build date: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        lines.append("")
        lines.append("## Component Sources")

        for component, metadata in components.items():
            branch = metadata.get("branch", "")
            commit = metadata.get("commit_sha", "")[:7] if metadata.get("commit_sha") else ""
            tag = metadata.get("tag_name", "")
            
            lines.append(
                f"- **{component}** {tag} (branch: {branch}, commit: {commit})"
            )

        lines.extend([
            "",
            "## Included Files",
            "",
            "### Executables:",
            "- sol-server.zip",
            "- sol_software",
            "- sol_update_gui",
            "- sol_update_backend",
            "- sol_update_manager",
            "- sol_update_manager_gui",
            "- mass_gadget_watchdog",
            "- update_version_info",
            "- gpio_shutdown_trigger",
            "- off_mass_gadget",
            "- on_mass_gadget",
            "- expand_exfat",
            "- provision",
            "- mp2624",
            "",
            "### Service Files:",
            "- sol-server.service",
            "- sol_software.service",
            "- sol-connectivity.service",
            "- mass_gadget_watchdog.service",
            "- update_version_info.service",
            "- filebeat.service",
            "",
            "### Config Files:",
            "- filebeat.yml",
            "",
            "### Logrotate Files:",
            "- mp2624-logrotate",
            "- sol-server-logrotate",
            "- sol_software-logrotate",
            "- mass_gadget_watchdog-logrotate",
            "- sol_update_manager-logrotate"
        ])

        return "\n".join(lines)

    def cleanup_old_releases(self, keep_count: int = 5) -> List[Dict[str, Any]]:
        """Remove old releases, keeping only the most recent ones.
        
        Args:
            keep_count: Number of releases to keep
            
        Returns:
            List of deleted release information
        """
        self.log_step(f"Cleaning up old releases (keeping {keep_count})")
        return self.release_manager.cleanup_old_releases(keep_count)

    def get_release_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent release history.
        
        Args:
            limit: Number of recent releases to fetch
            
        Returns:
            List of recent release information
        """
        self.log_step(f"Fetching recent release history (limit: {limit})")
        releases = self.release_manager.list_releases(per_page=limit)
        
        return [
            {
                "tag": r.get("tag_name", ""),
                "name": r.get("name", ""),
                "created_at": r.get("created_at", ""),
                "html_url": r.get("html_url", ""),
                "is_prerelease": r.get("prerelease", False)
            }
            for r in releases
        ]


# Export main classes
__all__ = [
    "GitHubAPIError",
    "GitHubReleaseManager",
    "ComponentMetadataFetcher",
    "ReleaseWorkflowOrchestrator"
]
