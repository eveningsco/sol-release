"""Metadata Generation Tests for SOL Release System.

These tests validate metadata generation logic for releases,
component version tracking, and build information collection.
"""

import pytest
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import Mock, patch, MagicMock
import json
import hashlib
import tempfile
import os


class ReleaseMetadataCollector:
    """Collects and manages release metadata."""

    def __init__(self):
        """Initialize metadata collector."""
        self.releases: dict = {}
        self.metadata_log: list = []

    def collect_release_metadata(
        self,
        release_id: int,
        tag_name: str,
        name: str,
        body: str,
        created_at: str,
        commit_sha: str,
        branch: str,
        assets: Optional[list] = None
    ):
        """Collect metadata for a single release.

        Args:
            release_id: GitHub release ID
            tag_name: Git tag name
            name: Release title
            body: Release body text
            created_at: ISO timestamp of creation
            commit_sha: Commit SHA associated with release
            branch: Git branch
            assets: List of assets in the release
        """
        asset_list = assets or []
        metadata = {
            "release_id": release_id,
            "tag_name": tag_name,
            "name": name,
            "body": body,
            "created_at": created_at,
            "commit_sha": commit_sha,
            "branch": branch,
            "assets": asset_list,
            "asset_count": len(asset_list)
        }

        self.releases[tag_name] = metadata
        self.metadata_log.append({
            "action": "collect",
            "tag": tag_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        return metadata

    def get_latest_release(self, tag_prefix: str = "") -> dict:
        """Get the latest release matching prefix.

        Args:
            tag_prefix: Optional prefix to filter tags

        Returns:
            Latest release metadata or None
        """
        if not self.releases:
            return None

        candidate_tags = [
            tag for tag in self.releases.keys()
            if tag.startswith(tag_prefix)
        ]

        if not candidate_tags:
            return None

        # Sort by created_at descending
        sorted_tags = sorted(
            candidate_tags,
            key=lambda t: self.releases[t].get("created_at", ""),
            reverse=True
        )

        latest_tag = sorted_tags[0]
        return self.releases[latest_tag]

    def get_all_releases_sorted(self) -> list:
        """Get all releases sorted by creation date.

        Returns:
            List of release metadata dictionaries
        """
        sorted_releases = sorted(
            self.releases.values(),
            key=lambda r: r.get("created_at", ""),
            reverse=True
        )
        return sorted_releases

    def get_release_by_tag(self, tag_name: str) -> dict:
        """Get release metadata by tag name.

        Args:
            tag_name: Git tag name

        Returns:
            Release metadata or None
        """
        return self.releases.get(tag_name)

    def get_releases_by_branch(self, branch: str) -> list:
        """Get all releases for a specific branch.

        Args:
            branch: Git branch name

        Returns:
            List of release metadata dictionaries
        """
        return [
            r for r in self.releases.values()
            if r.get("branch") == branch
        ]

    def export_to_json(self, filepath: str):
        """Export all metadata to JSON file.

        Args:
            filepath: Path to output file
        """
        data = {
            "collected_at": datetime.now(timezone.utc).isoformat(),
            "total_releases": len(self.releases),
            "releases": self.releases,
            "metadata_log": self.metadata_log
        }

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def generate_metadata_hash(metadata: dict) -> str:
        """Generate a hash for metadata verification.

        Args:
            metadata: Metadata dictionary to hash

        Returns:
            SHA256 hash of metadata
        """
        metadata_str = json.dumps(metadata, sort_keys=True)
        return hashlib.sha256(metadata_str.encode()).hexdigest()


class WorkflowMetadataTracker:
    """Tracks metadata for workflow executions."""

    def __init__(self):
        """Initialize workflow metadata tracker."""
        self.workflows: dict = {}
        self.workflow_log: list = []

    def record_workflow(
        self,
        workflow_id: str,
        event_type: str,
        triggered_at: str,
        components: list,
        status: str = "completed"
    ):
        """Record a workflow execution.

        Args:
            workflow_id: Unique workflow execution ID
            event_type: GitHub event type that triggered workflow
            triggered_at: ISO timestamp
            components: List of component names involved
            status: Workflow status (completed, failed, running)
        """
        metadata = {
            "workflow_id": workflow_id,
            "event_type": event_type,
            "triggered_at": triggered_at,
            "components": components,
            "status": status,
            "duration": None,
            "result": {}
        }

        self.workflows[workflow_id] = metadata
        self.workflow_log.append({
            "action": "record",
            "workflow_id": workflow_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    def complete_workflow(
        self,
        workflow_id: str,
        completed_at: str,
        result: dict
    ):
        """Mark a workflow as completed.

        Args:
            workflow_id: Workflow execution ID
            completed_at: Completion timestamp
            result: Workflow result data
        """
        if workflow_id not in self.workflows:
            return

        self.workflows[workflow_id]["status"] = "completed"
        self.workflows[workflow_id]["completed_at"] = completed_at
        self.workflows[workflow_id]["result"] = result

        # Calculate duration
        if "triggered_at" in self.workflows[workflow_id]:
            start = datetime.fromisoformat(
                self.workflows[workflow_id]["triggered_at"]
            )
            end = datetime.fromisoformat(completed_at)
            self.workflows[workflow_id]["duration"] = (end - start).total_seconds()

    def get_workflow_by_id(self, workflow_id: str) -> dict:
        """Get workflow metadata by ID.

        Args:
            workflow_id: Workflow execution ID

        Returns:
            Workflow metadata or None
        """
        return self.workflows.get(workflow_id)

    def get_workflows_by_event_type(self, event_type: str) -> list:
        """Get all workflows triggered by specific event type.

        Args:
            event_type: GitHub event type

        Returns:
            List of workflow metadata
        """
        return [
            w for w in self.workflows.values()
            if w.get("event_type") == event_type
        ]

    def get_workflow_statistics(self) -> dict:
        """Get workflow execution statistics.

        Returns:
            Statistics dictionary
        """
        if not self.workflows:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "avg_duration": 0
            }

        completed = [
            w for w in self.workflows.values()
            if w.get("status") == "completed"
        ]

        failed = [
            w for w in self.workflows.values()
            if w.get("status") == "failed"
        ]

        durations = [
            w.get("duration") for w in completed
            if w.get("duration") is not None
        ]

        return {
            "total": len(self.workflows),
            "completed": len(completed),
            "failed": len(failed),
            "avg_duration": sum(durations) / len(durations) if durations else 0
        }


class DispatchEventParser:
    """Parses GitHub repository dispatch events."""

    EVENT_MAPPING = {
        "sol_software_release": {
            "component": "sol-software",
            "owner": "eveningsco",
            "repo": "sol-software"
        },
        "sol_server_release": {
            "component": "sol-server",
            "owner": "eveningsco",
            "repo": "sol-server"
        },
        "sol_utils_release": {
            "component": "sol-utils",
            "owner": "eveningsco",
            "repo": "sol-utils"
        }
    }

    def __init__(self, payload: dict):
        """Initialize dispatch event parser.

        Args:
            payload: GitHub webhook payload dictionary
        """
        self.payload = payload
        self.parsed_data: dict = {}

    def parse(self) -> dict:
        """Parse the dispatch event.

        Returns:
            Parsed event data
        """
        event_type = self.payload.get("client_payload", {}).get("event_type", "")

        if event_type not in self.EVENT_MAPPING:
            raise ValueError(f"Unknown event type: {event_type}")

        config = self.EVENT_MAPPING[event_type]

        client_payload = self.payload.get("client_payload", {})

        self.parsed_data = {
            "event_type": event_type,
            "component": config["component"],
            "owner": config["owner"],
            "repo": config["repo"],
            "branch": client_payload.get("branch", ""),
            "commit_sha": client_payload.get("commit_sha", ""),
            "tag_name": client_payload.get("tag_name", ""),
            "pr_number": self._extract_pr_number(client_payload.get("body", ""))
        }

        return self.parsed_data

    def _extract_pr_number(self, body: str) -> int:
        """Extract PR number from body text.

        Args:
            body: Text body to search

        Returns:
            PR number if found, None otherwise
        """
        import re
        match = re.search(r"PR\s*#?(\d+)", body)
        if match:
            return int(match.group(1))
        return None

    def is_valid_dispatch(self) -> bool:
        """Check if this is a valid dispatch event.

        Returns:
            True if event is valid
        """
        return "client_payload" in self.payload and \
               "event_type" in self.payload.get("client_payload", {})

    def get_component_info(self) -> dict:
        """Get component information from parsed event.

        Returns:
            Component information dictionary
        """
        self.parse()
        return {
            "name": self.parsed_data.get("component", ""),
            "branch": self.parsed_data.get("branch", ""),
            "commit": self.parsed_data.get("commit_sha", ""),
            "tag": self.parsed_data.get("tag_name", "")
        }


class ReleaseBodyGenerator:
    """Generates release body text from metadata."""

    ASSET_CATEGORIES = {
        "executables": [
            "sol-server", "sol_software", "sol_update_gui",
            "sol_update_backend", "sol_update_manager",
            "mass_gadget_watchdog", "provision", "mp2624"
        ],
        "services": [
            "sol-server.service", "sol_software.service",
            "mass_gadget_watchdog.service"
        ],
        "config": ["filebeat.yml"],
        "logrotate": []
    }

    def __init__(self, metadata: dict, component_metadata: dict = None):
        """Initialize release body generator.

        Args:
            metadata: Release metadata dictionary
            component_metadata: Optional component metadata
        """
        self.metadata = metadata
        self.component_metadata = component_metadata or {}

    def generate(self) -> str:
        """Generate release body text.

        Returns:
            Formatted release body string
        """
        lines = [
            "SOL Release Package",
            f"Build Date: {self._format_date(self.metadata.get('created_at', ''))}",
            "",
            "## Component Information"
        ]

        if self.component_metadata:
            lines.append("")
            for component, comp_data in self.component_metadata.items():
                tag = comp_data.get("tag_name", "N/A")
                branch = comp_data.get("branch", "N/A")
                commit = comp_data.get("commit_sha", "")[:8] if comp_data.get("commit_sha") else "N/A"
                lines.append(f"- **{component}**: {tag} (branch: {branch}, commit: {commit})")

        lines.extend([
            "",
            "## Release Information",
            f"- Release ID: {self.metadata.get('release_id', 'N/A')}",
            f"- Tag: {self.metadata.get('tag_name', 'N/A')}",
            f"- Commit: {self.metadata.get('commit_sha', 'N/A')[:8] if self.metadata.get('commit_sha') else 'N/A'}",
            f"- Assets: {self.metadata.get('asset_count', 0)} files"
        ])

        lines.extend([
            "",
            "## Included Files"
        ])

        # Add assets if available
        assets = self.metadata.get("assets", [])
        if assets:
            for i, asset in enumerate(assets[:10], 1):
                lines.append(f"{i}. {asset.get('name', 'Unknown')}")
            if len(assets) > 10:
                lines.append(f"... and {len(assets) - 10} more assets")

        return "\n".join(lines)

    def _format_date(self, date_str: str) -> str:
        """Format date string for display.

        Args:
            date_str: ISO date string

        Returns:
            Formatted date string
        """
        if not date_str:
            return "N/A"

        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except:
            return date_str[:19]


class ComponentMetadataFetcher:
    """Simulates fetching metadata from component repositories."""

    COMPONENTS = {
        "sol-software": {
            "latest_tag": "v1.2.3",
            "branch": "main",
            "commit_sha": "abc123def456",
            "releases": [
                {"tag": "v1.2.3", "date": "2026-03-25"},
                {"tag": "v1.2.2", "date": "2026-03-20"},
                {"tag": "v1.2.1", "date": "2026-03-15"}
            ]
        },
        "sol-server": {
            "latest_tag": "v2.1.0",
            "branch": "main",
            "commit_sha": "xyz789abc123",
            "releases": [
                {"tag": "v2.1.0", "date": "2026-03-26"},
                {"tag": "v2.0.0", "date": "2026-03-18"},
                {"tag": "v1.9.0", "date": "2026-03-10"}
            ]
        },
        "sol-utils": {
            "latest_tag": "v1.0.5",
            "branch": "main",
            "commit_sha": "def456xyz789",
            "releases": [
                {"tag": "v1.0.5", "date": "2026-03-24"},
                {"tag": "v1.0.4", "date": "2026-03-12"}
            ]
        }
    }

    def __init__(self):
        """Initialize component metadata fetcher."""
        self.fetched_metadata: dict = {}

    def fetch_component_metadata(self, component: str) -> dict:
        """Fetch metadata for a component.

        Args:
            component: Component name

        Returns:
            Component metadata dictionary
        """
        if component not in self.COMPONENTS:
            raise ValueError(f"Unknown component: {component}")

        comp_data = self.COMPONENTS[component]

        metadata = {
            "component": component,
            "included": True,
            "branch": comp_data["branch"],
            "commit_sha": comp_data["commit_sha"],
            "tag_name": comp_data["latest_tag"],
            "release_url": f"https://github.com/eveningsco/{component}/releases/tag/{comp_data['latest_tag']}",
            "pr_number": None,
            "history": comp_data["releases"]
        }

        self.fetched_metadata[component] = metadata
        return metadata

    def fetch_all_components(self) -> dict:
        """Fetch metadata for all components.

        Returns:
            Dictionary of component metadata
        """
        for component in self.COMPONENTS:
            self.fetch_component_metadata(component)

        return self.fetched_metadata

    def get_component_history(self, component: str, limit: int = 5) -> list:
        """Get release history for a component.

        Args:
            component: Component name
            limit: Maximum number of releases to return

        Returns:
            List of release information
        """
        if component not in self.COMPONENTS:
            return []

        return self.COMPONENTS[component]["releases"][:limit]

    def compare_components(self, components: list) -> dict:
        """Compare metadata across components.

        Args:
            components: List of component names to compare

        Returns:
            Comparison results
        """
        comparison = {}

        for component in components:
            if component in self.COMPONENTS:
                comp_data = self.COMPONENTS[component]
                comparison[component] = {
                    "latest_tag": comp_data["latest_tag"],
                    "commit_sha": comp_data["commit_sha"],
                    "branch": comp_data["branch"],
                    "release_count": len(comp_data["releases"])
                }

        return comparison


# ============================================================================
# TESTS
# ============================================================================

class TestReleaseMetadataCollector:
    """Tests for release metadata collector."""

    def test_collect_release_metadata(self):
        """Test collecting release metadata."""
        collector = ReleaseMetadataCollector()

        metadata = collector.collect_release_metadata(
            release_id=123,
            tag_name="v1.0.0",
            name="Release 1.0.0",
            body="Release body",
            created_at="2026-03-25T10:00:00Z",
            commit_sha="abc123def",
            branch="main",
            assets=["file1.zip", "file2.zip"]
        )

        assert metadata["release_id"] == 123
        assert metadata["tag_name"] == "v1.0.0"
        assert metadata["asset_count"] == 2

    def test_get_latest_release(self):
        """Test getting latest release."""
        collector = ReleaseMetadataCollector()

        collector.collect_release_metadata(
            release_id=1, tag_name="v1.0.0", name="v1.0.0",
            body="", created_at="2026-01-01T00:00:00Z",
            commit_sha="abc", branch="main",
            assets=["file1.zip"]
        )
        collector.collect_release_metadata(
            release_id=2, tag_name="v2.0.0", name="v2.0.0",
            body="", created_at="2026-03-25T00:00:00Z",
            commit_sha="def", branch="main",
            assets=["file2.zip"]
        )

        latest = collector.get_latest_release()

        assert latest["tag_name"] == "v2.0.0"
        assert latest["release_id"] == 2

    def test_get_latest_release_with_prefix(self):
        """Test getting latest release with tag prefix."""
        collector = ReleaseMetadataCollector()

        collector.collect_release_metadata(
            release_id=1, tag_name="v1.0.0", name="v1.0.0",
            body="", created_at="2026-01-01T00:00:00Z",
            commit_sha="abc", branch="main",
            assets=["file1.zip"]
        )
        collector.collect_release_metadata(
            release_id=2, tag_name="v2.0.0", name="v2.0.0",
            body="", created_at="2026-03-25T00:00:00Z",
            commit_sha="def", branch="main",
            assets=["file2.zip"]
        )

        latest = collector.get_latest_release(tag_prefix="v1.")

        assert latest["tag_name"] == "v1.0.0"

    def test_get_release_by_tag(self):
        """Test getting release by tag name."""
        collector = ReleaseMetadataCollector()

        collector.collect_release_metadata(
            release_id=123, tag_name="v1.0.0", name="v1.0.0",
            body="Test", created_at="2026-03-25T00:00:00Z",
            commit_sha="abc123", branch="main"
        )

        release = collector.get_release_by_tag("v1.0.0")

        assert release is not None
        assert release["release_id"] == 123

    def test_get_release_by_tag_not_found(self):
        """Test getting non-existent release by tag."""
        collector = ReleaseMetadataCollector()

        release = collector.get_release_by_tag("nonexistent")

        assert release is None

    def test_get_releases_by_branch(self):
        """Test getting releases by branch."""
        collector = ReleaseMetadataCollector()

        collector.collect_release_metadata(
            release_id=1, tag_name="v1.0.0", name="v1.0.0",
            body="", created_at="2026-01-01T00:00:00Z",
            commit_sha="abc", branch="main"
        )
        collector.collect_release_metadata(
            release_id=2, tag_name="v2.0.0", name="v2.0.0",
            body="", created_at="2026-03-25T00:00:00Z",
            commit_sha="def", branch="develop"
        )
        collector.collect_release_metadata(
            release_id=3, tag_name="v1.1.0", name="v1.1.0",
            body="", created_at="2026-03-20T00:00:00Z",
            commit_sha="ghi", branch="main"
        )

        main_releases = collector.get_releases_by_branch("main")

        assert len(main_releases) == 2
        assert all(r["branch"] == "main" for r in main_releases)

    def test_get_all_releases_sorted(self):
        """Test getting all releases sorted by date."""
        collector = ReleaseMetadataCollector()

        collector.collect_release_metadata(
            release_id=1, tag_name="v1.0.0", name="v1.0.0",
            body="", created_at="2026-01-01T00:00:00Z",
            commit_sha="abc", branch="main"
        )
        collector.collect_release_metadata(
            release_id=2, tag_name="v2.0.0", name="v2.0.0",
            body="", created_at="2026-03-25T00:00:00Z",
            commit_sha="def", branch="main"
        )

        sorted_releases = collector.get_all_releases_sorted()

        assert len(sorted_releases) == 2
        assert sorted_releases[0]["tag_name"] == "v2.0.0"

    def test_generate_metadata_hash(self):
        """Test generating metadata hash."""
        collector = ReleaseMetadataCollector()

        metadata = {
            "release_id": 123,
            "tag_name": "v1.0.0",
            "name": "Test"
        }

        hash1 = collector.generate_metadata_hash(metadata)
        hash2 = collector.generate_metadata_hash(metadata)

        assert len(hash1) == 64  # SHA256 hex length
        assert hash1 == hash2

        metadata["name"] = "Different"
        hash3 = collector.generate_metadata_hash(metadata)

        assert hash1 != hash3

    def test_export_to_json(self):
        """Test exporting metadata to JSON."""
        collector = ReleaseMetadataCollector()

        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            collector.collect_release_metadata(
                release_id=1, tag_name="v1.0.0", name="v1.0.0",
                body="", created_at="2026-03-25T00:00:00Z",
                commit_sha="abc", branch="main"
            )

            collector.export_to_json(temp_path)

            with open(temp_path, 'r') as f:
                data = json.load(f)

            assert "collected_at" in data
            assert data["total_releases"] == 1
            assert "v1.0.0" in data["releases"]

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestWorkflowMetadataTracker:
    """Tests for workflow metadata tracker."""

    def test_record_workflow(self):
        """Test recording a workflow execution."""
        tracker = WorkflowMetadataTracker()

        tracker.record_workflow(
            workflow_id="wf-001",
            event_type="sol_software_release",
            triggered_at="2026-03-25T10:00:00Z",
            components=["sol-software"],
            status="completed"
        )

        workflow = tracker.get_workflow_by_id("wf-001")

        assert workflow["event_type"] == "sol_software_release"
        assert workflow["status"] == "completed"
        assert "sol-software" in workflow["components"]

    def test_complete_workflow(self):
        """Test completing a workflow."""
        tracker = WorkflowMetadataTracker()

        # Record workflow
        tracker.record_workflow(
            workflow_id="wf-001",
            event_type="sol_software_release",
            triggered_at="2026-03-25T10:00:00Z",
            components=["sol-software"]
        )

        # Complete workflow
        tracker.complete_workflow(
            workflow_id="wf-001",
            completed_at="2026-03-25T10:05:00Z",
            result={"success": True, "assets": 5}
        )

        workflow = tracker.get_workflow_by_id("wf-001")

        assert workflow["status"] == "completed"
        assert workflow["duration"] == 300.0  # 5 minutes in seconds
        assert workflow["result"]["success"] is True

    def test_get_workflows_by_event_type(self):
        """Test getting workflows by event type."""
        tracker = WorkflowMetadataTracker()

        tracker.record_workflow("wf-1", "sol_software_release", "2026-03-25T10:00:00Z", [])
        tracker.record_workflow("wf-2", "sol_server_release", "2026-03-25T11:00:00Z", [])
        tracker.record_workflow("wf-3", "sol_software_release", "2026-03-25T12:00:00Z", [])

        software_workflows = tracker.get_workflows_by_event_type("sol_software_release")

        assert len(software_workflows) == 2

    def test_get_workflow_statistics(self):
        """Test getting workflow statistics."""
        tracker = WorkflowMetadataTracker()

        tracker.record_workflow("wf-1", "event", "2026-03-25T10:00:00Z", [], status="completed")
        tracker.record_workflow("wf-2", "event", "2026-03-25T10:00:00Z", [], status="completed")
        tracker.record_workflow("wf-3", "event", "2026-03-25T10:00:00Z", [], status="running")

        stats = tracker.get_workflow_statistics()

        assert stats["total"] == 3
        assert stats["completed"] == 2
        assert stats["failed"] == 0

    def test_get_workflow_by_id_not_found(self):
        """Test getting non-existent workflow."""
        tracker = WorkflowMetadataTracker()

        workflow = tracker.get_workflow_by_id("nonexistent")

        assert workflow is None


class TestDispatchEventParser:
    """Tests for dispatch event parser."""

    def test_parse_valid_dispatch(self):
        """Test parsing valid dispatch event."""
        payload = {
            "event_type": "repository_dispatch",
            "client_payload": {
                "event_type": "sol_software_release",
                "branch": "main",
                "commit_sha": "abc123def456",
                "tag_name": "v1.0.0"
            }
        }

        parser = DispatchEventParser(payload)
        parsed = parser.parse()

        assert parsed["event_type"] == "sol_software_release"
        assert parsed["component"] == "sol-software"
        assert parsed["branch"] == "main"
        assert parsed["commit_sha"] == "abc123def456"

    def test_parse_invalid_event_type(self):
        """Test parsing invalid event type."""
        payload = {
            "client_payload": {
                "event_type": "unknown_event"
            }
        }

        parser = DispatchEventParser(payload)

        with pytest.raises(ValueError):
            parser.parse()

    def test_extract_pr_number(self):
        """Test extracting PR number from body."""
        payload = {
            "client_payload": {
                "event_type": "sol_software_release",
                "body": "Release v1.0.0 - PR #123"
            }
        }

        parser = DispatchEventParser(payload)
        parsed = parser.parse()

        assert parsed["pr_number"] == 123

    def test_extract_pr_number_no_pr(self):
        """Test parsing when no PR number in body."""
        payload = {
            "client_payload": {
                "event_type": "sol_server_release",
                "body": "Release v2.0.0"
            }
        }

        parser = DispatchEventParser(payload)
        parsed = parser.parse()

        assert parsed["pr_number"] is None

    def test_is_valid_dispatch(self):
        """Test dispatch validation."""
        valid_payload = {
            "client_payload": {
                "event_type": "sol_software_release",
                "branch": "main"
            }
        }
        invalid_payload = {}

        assert DispatchEventParser(valid_payload).is_valid_dispatch() is True
        assert DispatchEventParser(invalid_payload).is_valid_dispatch() is False

    def test_get_component_info(self):
        """Test getting component information."""
        payload = {
            "client_payload": {
                "event_type": "sol_server_release",
                "branch": "develop",
                "commit_sha": "xyz789",
                "tag_name": "v1.5.0"
            }
        }

        parser = DispatchEventParser(payload)
        component_info = parser.get_component_info()

        assert component_info["name"] == "sol-server"
        assert component_info["branch"] == "develop"


class TestReleaseBodyGenerator:
    """Tests for release body generator."""

    def test_generate_basic(self):
        """Test generating basic release body."""
        metadata = {
            "release_id": "123",
            "tag_name": "v1.0.0",
            "commit_sha": "abc123def",
            "asset_count": 5,
            "created_at": "2026-03-25T10:00:00Z"
        }

        generator = ReleaseBodyGenerator(metadata)
        body = generator.generate()

        assert "SOL Release Package" in body
        assert "Build Date:" in body
        assert "v1.0.0" in body
        # Commit SHA is truncated to 8 characters
        assert "abc123de" in body

    def test_generate_with_component_metadata(self):
        """Test generating release body with component info."""
        metadata = {
            "release_id": "123",
            "tag_name": "v1.0.0",
            "commit_sha": "abc123",
            "asset_count": 5,
            "created_at": "2026-03-25T10:00:00Z"
        }

        component_metadata = {
            "sol-software": {
                "tag_name": "v1.2.3",
                "branch": "main",
                "commit_sha": "xyz789"
            },
            "sol-server": {
                "tag_name": "v2.0.0",
                "branch": "develop",
                "commit_sha": "abc456"
            }
        }

        generator = ReleaseBodyGenerator(metadata, component_metadata)
        body = generator.generate()

        assert "sol-software" in body
        assert "sol-server" in body
        assert "v1.2.3" in body
        assert "v2.0.0" in body

    def test_generate_with_assets(self):
        """Test generating release body with assets."""
        metadata = {
            "release_id": "123",
            "tag_name": "v1.0.0",
            "commit_sha": "abc123",
            "asset_count": 3,
            "assets": [
                {"name": "sol-server.zip"},
                {"name": "sol_software"},
                {"name": "filebeat.yml"}
            ],
            "created_at": "2026-03-25T10:00:00Z"
        }

        generator = ReleaseBodyGenerator(metadata)
        body = generator.generate()

        assert "sol-server.zip" in body
        assert "1. sol-server.zip" in body

    def test_format_date(self):
        """Test date formatting."""
        generator = ReleaseBodyGenerator({})

        # Test valid ISO date
        formatted = generator._format_date("2026-03-25T10:00:00Z")
        assert "2026-03-25" in formatted
        assert "UTC" in formatted

        # Test invalid date
        formatted = generator._format_date("not-a-date")
        assert "not-a-date" in formatted

        # Test empty date
        formatted = generator._format_date("")
        assert "N/A" in formatted


class TestComponentMetadataFetcher:
    """Tests for component metadata fetcher."""

    def test_fetch_component_metadata(self):
        """Test fetching component metadata."""
        fetcher = ComponentMetadataFetcher()

        metadata = fetcher.fetch_component_metadata("sol-software")

        assert metadata["component"] == "sol-software"
        assert metadata["tag_name"] == "v1.2.3"
        assert metadata["branch"] == "main"
        assert "abc123def456" in metadata["commit_sha"]

    def test_fetch_invalid_component(self):
        """Test fetching metadata for invalid component."""
        fetcher = ComponentMetadataFetcher()

        with pytest.raises(ValueError):
            fetcher.fetch_component_metadata("invalid-component")

    def test_fetch_all_components(self):
        """Test fetching all components."""
        fetcher = ComponentMetadataFetcher()

        metadata = fetcher.fetch_all_components()

        assert "sol-software" in metadata
        assert "sol-server" in metadata
        assert "sol-utils" in metadata

    def test_get_component_history(self):
        """Test getting component release history."""
        fetcher = ComponentMetadataFetcher()

        history = fetcher.get_component_history("sol-server", limit=2)

        assert len(history) == 2
        assert history[0]["tag"] == "v2.1.0"

    def test_get_component_history_no_component(self):
        """Test getting history for invalid component."""
        fetcher = ComponentMetadataFetcher()

        history = fetcher.get_component_history("invalid-component")

        assert history == []

    def test_compare_components(self):
        """Test comparing components."""
        fetcher = ComponentMetadataFetcher()

        comparison = fetcher.compare_components(["sol-software", "sol-server"])

        assert "sol-software" in comparison
        assert "sol-server" in comparison
        assert comparison["sol-software"]["latest_tag"] == "v1.2.3"
        assert comparison["sol-server"]["latest_tag"] == "v2.1.0"

    def test_compare_components_mixed(self):
        """Test comparing with mix of valid and invalid components."""
        fetcher = ComponentMetadataFetcher()

        comparison = fetcher.compare_components([
            "sol-software",
            "invalid-component",
            "sol-server"
        ])

        assert "sol-software" in comparison
        assert "invalid-component" not in comparison
        assert "sol-server" in comparison


class TestMetadataIntegration:
    """Integration tests for metadata generation."""

    def test_full_metadata_workflow(self):
        """Test complete metadata workflow."""
        # Collect releases with proper asset format
        collector = ReleaseMetadataCollector()
        collector.collect_release_metadata(
            release_id=1, tag_name="v1.0.0", name="v1.0.0",
            body="", created_at="2026-01-01T00:00:00Z",
            commit_sha="abc123", branch="main",
            assets=[{"name": "file1.zip"}]
        )
        collector.collect_release_metadata(
            release_id=2, tag_name="v2.0.0", name="v2.0.0",
            body="", created_at="2026-03-25T00:00:00Z",
            commit_sha="def456", branch="main",
            assets=[{"name": "file2.zip"}, {"name": "file3.zip"}]
        )

        # Generate release body
        latest = collector.get_latest_release()
        generator = ReleaseBodyGenerator(latest)
        body = generator.generate()

        # Verify body contains expected content
        assert "v2.0.0" in body
        assert "Build Date:" in body
        # Note: asset_count is the count of assets, not the string "3 files"
        assert "file2.zip" in body or "file3.zip" in body

    def test_workflow_and_dispatch_integration(self):
        """Test integrating workflow tracking with dispatch events."""
        # Parse dispatch event
        payload = {
            "event_type": "repository_dispatch",
            "client_payload": {
                "event_type": "sol_software_release",
                "branch": "main",
                "commit_sha": "xyz789",
                "tag_name": "v1.0.0"
            }
        }

        parser = DispatchEventParser(payload)
        parsed = parser.parse()

        # Record workflow
        tracker = WorkflowMetadataTracker()
        tracker.record_workflow(
            workflow_id="wf-001",
            event_type=parsed["event_type"],
            triggered_at="2026-03-25T10:00:00Z",
            components=[parsed["component"]]
        )

        # Complete workflow
        tracker.complete_workflow(
            workflow_id="wf-001",
            completed_at="2026-03-25T10:05:00Z",
            result={"component": parsed["component"]}
        )

        # Verify
        workflow = tracker.get_workflow_by_id("wf-001")
        assert workflow["status"] == "completed"
        assert "sol-software" in workflow["components"]

    def test_metadata_consistency_across_components(self):
        """Test metadata consistency across multiple components."""
        fetcher = ComponentMetadataFetcher()

        # Fetch all components
        all_metadata = fetcher.fetch_all_components()

        # Verify each component has required fields
        for component, metadata in all_metadata.items():
            assert "component" in metadata
            assert "tag_name" in metadata
            assert "branch" in metadata
            assert "commit_sha" in metadata
            assert "history" in metadata

        # Verify versions are correct
        assert all_metadata["sol-software"]["tag_name"] == "v1.2.3"
        assert all_metadata["sol-server"]["tag_name"] == "v2.1.0"
        assert all_metadata["sol-utils"]["tag_name"] == "v1.0.5"

    def test_metadata_persistence(self):
        """Test metadata persistence across operations."""
        collector = ReleaseMetadataCollector()

        # Collect releases with assets
        collector.collect_release_metadata(
            release_id=1, tag_name="v1.0.0", name="v1.0.0",
            body="", created_at="2026-03-25T00:00:00Z",
            commit_sha="abc123", branch="main",
            assets=[{"name": "test.zip"}]
        )

        # Export to JSON
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name

        try:
            collector.export_to_json(temp_path)

            # Re-import and verify
            with open(temp_path, 'r') as f:
                imported_data = json.load(f)

            assert "releases" in imported_data
            assert "v1.0.0" in imported_data["releases"]
            assert imported_data["releases"]["v1.0.0"]["tag_name"] == "v1.0.0"
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def test_metadata_hash_verification(self):
        """Test metadata hash for integrity verification."""
        collector = ReleaseMetadataCollector()

        # Create and hash metadata
        metadata = {
            "release_id": 1,
            "tag_name": "v1.0.0",
            "commit_sha": "abc123def"
        }

        hash1 = collector.generate_metadata_hash(metadata)

        # Verify same metadata produces same hash
        hash2 = collector.generate_metadata_hash(metadata)
        assert hash1 == hash2

        # Verify different metadata produces different hash
        metadata["tag_name"] = "v1.1.0"
        hash3 = collector.generate_metadata_hash(metadata)
        assert hash1 != hash3


class TestMetadataEdgeCases:
    """Tests for metadata edge cases."""

    def test_empty_metadata_collector(self):
        """Test operations on empty metadata collector."""
        collector = ReleaseMetadataCollector()

        latest = collector.get_latest_release()
        assert latest is None

        sorted_releases = collector.get_all_releases_sorted()
        assert sorted_releases == []

    def test_workflow_tracker_with_no_workflows(self):
        """Test workflow tracker with no workflows."""
        tracker = WorkflowMetadataTracker()

        stats = tracker.get_workflow_statistics()

        assert stats["total"] == 0
        assert stats["completed"] == 0
        assert stats["avg_duration"] == 0

    def test_dispatch_parser_invalid_payload(self):
        """Test dispatch parser with invalid payload."""
        parser = DispatchEventParser({})

        with pytest.raises(ValueError):
            parser.parse()

    def test_release_body_generator_empty_metadata(self):
        """Test release body generator with empty metadata."""
        generator = ReleaseBodyGenerator({})
        body = generator.generate()

        # Should still generate valid body with N/A values
        assert "SOL Release Package" in body
        assert "N/A" in body

    def test_component_fetcher_partial_history(self):
        """Test component fetcher with limited history."""
        fetcher = ComponentMetadataFetcher()

        history = fetcher.get_component_history("sol-utils", limit=1)

        assert len(history) == 1
        assert history[0]["tag"] == "v1.0.5"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
