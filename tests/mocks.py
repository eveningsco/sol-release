"""Test suite for SOL release workflow logic simulation.

This module provides tests for the workflow orchestration logic,
metadata generation, and artifact handling simulation.
"""

import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


class ReleaseMetadata:
    """Simulates the metadata.json structure created by the workflow."""
    
    def __init__(self):
        self.release_version: str = ""
        self.build_date: str = ""
        self.triggered_by: str = ""
        self.components: Dict[str, Any] = {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "release_version": self.release_version,
            "build_date": self.build_date,
            "triggered_by": self.triggered_by,
            "components": self.components
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ReleaseMetadata':
        data = json.loads(json_str)
        metadata = cls()
        metadata.release_version = data.get("release_version", "")
        metadata.build_date = data.get("build_date", "")
        metadata.triggered_by = data.get("triggered_by", "")
        metadata.components = data.get("components", {})
        return metadata


class WorkflowMetadataCollector:
    """Simulates the metadata collection and merging logic from the workflow."""
    
    SUPPORTED_COMPONENTS = {
        "sol-software": {
            "branch_key": "sol_software_branch",
            "commit_key": "sol_software_commit",
            "tag_key": "sol_software_tag",
            "url_key": "sol_software_url",
            "metadata_file": "sol-software-metadata.json"
        },
        "sol-utils": {
            "branch_key": "sol_utils_branch",
            "commit_key": "sol_utils_commit",
            "tag_key": "sol_utils_tag",
            "url_key": "sol_utils_url",
            "metadata_file": "sol-utils-metadata.json"
        },
        "sol-server": {
            "branch_key": "sol_server_branch",
            "commit_key": "sol_server_commit",
            "tag_key": "sol_server_tag",
            "url_key": "sol_server_url",
            "metadata_file": "sol-server-metadata.json"
        }
    }
    
    def __init__(self):
        self.metadata = ReleaseMetadata()
        self.workflow_steps: List[str] = []
    
    def log_step(self, step: str):
        """Log a workflow step."""
        self.workflow_steps.append(step)
    
    def initialize(self, triggered_by: str = "repository_dispatch"):
        """Initialize the metadata collector."""
        self.metadata = ReleaseMetadata()
        self.metadata.triggered_by = triggered_by
        self.metadata.build_date = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.log_step("Metadata initialization")
    
    def parse_dispatch_event(self, event_action: str, event_payload: Optional[Dict[str, str]]) -> bool:
        """Parse repository_dispatch event metadata."""
        if not event_payload:
            self.log_step("No dispatch event payload")
            return False
        
        component = self._get_component_from_action(event_action)
        if not component:
            self.log_step(f"Unknown event action: {event_action}")
            return False
        
        component_config = self.SUPPORTED_COMPONENTS[component]
        
        self.metadata.components[component] = {
            "included": True,
            "branch": event_payload.get(component_config["branch_key"], ""),
            "commit_sha": event_payload.get(component_config["commit_key"], ""),
            "tag_name": event_payload.get(component_config["tag_key"], ""),
            "release_url": event_payload.get(component_config["url_key"], ""),
        }
        
        self.log_step(f"Parsed {component} dispatch metadata")
        return True
    
    def _get_component_from_action(self, action: str) -> Optional[str]:
        """Map event action to component name."""
        mapping = {
            "sol_software_release": "sol-software",
            "sol_utils_release": "sol-utils",
            "sol_server_release": "sol-server"
        }
        return mapping.get(action)
    
    def merge_component_metadata(self, component: str, metadata_file_path: str):
        """Simulate merging component metadata file."""
        if component not in self.SUPPORTED_COMPONENTS:
            self.log_step(f"Unknown component: {component}")
            return False
        
        self.log_step(f"Merging metadata for {component} from {metadata_file_path}")
        return True
    
    def mark_component_included(self, component: str):
        """Mark a component as included when no metadata file exists."""
        if component not in self.SUPPORTED_COMPONENTS:
            return False
        
        self.metadata.components[component] = {"included": True}
        self.log_step(f"Marked {component} as included (no metadata)")
        return True
    
    def finalize_release_version(self):
        """Finalize the release version string."""
        timestamp = datetime.now(timezone.utc).strftime("%m%d%Y_%H-%M-%S")
        self.metadata.release_version = f"Release-{timestamp}"
        self.log_step(f"Release version finalized: {self.metadata.release_version}")
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get a summary of the workflow execution."""
        return {
            "steps_count": len(self.workflow_steps),
            "steps": self.workflow_steps,
            "components": list(self.metadata.components.keys()),
            "build_date": self.metadata.build_date,
            "triggered_by": self.metadata.triggered_by
        }


class ReleaseBodyGenerator:
    """Simulates the release body generation logic from the workflow."""
    
    COMPONENTS_ORDER = ["sol-software", "sol-utils", "sol-server"]
    
    def __init__(self, metadata: ReleaseMetadata):
        self.metadata = metadata
    
    def generate_body(self) -> str:
        """Generate the release body text."""
        lines = []
        lines.append("Combined SOL release package")
        lines.append(f"Build date: {self.metadata.build_date}")
        lines.append("")
        lines.append("## Component Sources")
        
        for component in self.COMPONENTS_ORDER:
            if component in self.metadata.components:
                comp_data = self.metadata.components[component]
                if isinstance(comp_data, dict) and "branch" in comp_data:
                    branch = comp_data.get("branch", "")
                    commit = comp_data.get("commit_sha", "")[:7] if comp_data.get("commit_sha") else ""
                    tag = comp_data.get("tag_name", "")
                    pr_number = comp_data.get("pr_number", "")
                    
                    line = f"- **{component}** {tag} (branch: {branch}, commit: {commit}"
                    if pr_number:
                        line += f", PR: #{pr_number}"
                    line += ")"
                    lines.append(line)
        
        lines.append("")
        lines.append("## Included Files")
        lines.append("")
        lines.append("### Executables:")
        lines.append("- sol-server.zip")
        lines.append("- sol_software")
        lines.append("- sol_update_gui")
        lines.append("- sol_update_backend")
        lines.append("- sol_update_manager")
        lines.append("- sol_update_manager_gui")
        lines.append("- mass_gadget_watchdog")
        lines.append("- update_version_info")
        lines.append("- gpio_shutdown_trigger")
        lines.append("- off_mass_gadget")
        lines.append("- on_mass_gadget")
        lines.append("- expand_exfat")
        lines.append("- provision")
        lines.append("- mp2624")
        
        lines.append("")
        lines.append("### Service Files:")
        lines.append("- sol-server.service")
        lines.append("- sol_software.service")
        lines.append("- sol-connectivity.service")
        lines.append("- sol-connectivity.timer")
        lines.append("- mass_gadget_watchdog.service")
        lines.append("- update_version_info.service")
        lines.append("- update_version_info.timer")
        lines.append("- filebeat.service")
        lines.append("- fbcp.service")
        lines.append("- mp2624_watchdog.service")
        lines.append("- sol_update_manager.service")
        
        lines.append("")
        lines.append("### Config Files:")
        lines.append("- filebeat.yml")
        
        lines.append("")
        lines.append("### Logrotate Files:")
        lines.append("- mp2624-logrotate")
        lines.append("- sol-server-logrotate")
        lines.append("- sol_software-logrotate")
        lines.append("- mass_gadget_watchdog-logrotate")
        lines.append("- sol_update_manager-logrotate")
        
        return "\n".join(lines)
    
    def get_body_hash(self) -> str:
        """Get a hash of the release body for verification."""
        body = self.generate_body()
        return hashlib.sha256(body.encode()).hexdigest()[:16]


class ArtifactDownloaderSimulator:
    """Simulates the artifact downloading logic from the workflow."""
    
    COMPONENT_ARTIFACTS = {
        "sol-server": {
            "executables": ["sol-server.zip"],
            "services": ["sol-connectivity.service", "sol-connectivity.timer", "sol-server.service"],
            "metadata_file": "sol-server-metadata.json"
        },
        "sol-software": {
            "executables": ["sol_software"],
            "services": ["sol_software.service"],
            "metadata_file": "sol-software-metadata.json"
        },
        "sol-utils": {
            "executables": [
                "sol_update_gui", "sol_update_backend", "sol_update_manager",
                "sol_update_manager_gui", "mass_gadget_watchdog", "update_version_info",
                "gpio_shutdown_trigger", "off_mass_gadget", "on_mass_gadget",
                "expand_exfat", "provision", "mp2624"
            ],
            "services": [
                "mp2624_watchdog.service", "mass_gadget_watchdog.service",
                "update_version_info.service", "update_version_info.timer",
                "fbcp.service", "filebeat.service", "sol_update_manager.service"
            ],
            "metadata_file": "sol-utils-metadata.json",
            "config": ["filebeat.yml"],
            "logrotate": [
                "mp2624-logrotate", "sol-server-logrotate", "sol_software-logrotate",
                "mass_gadget_watchdog-logrotate", "sol_update_manager-logrotate"
            ]
        }
    }
    
    def __init__(self):
        self.downloaded_files: List[str] = []
        self.steps: List[str] = []
    
    def log_step(self, step: str):
        """Log a download step."""
        self.steps.append(step)
    
    def download_component(self, component: str, base_dir: str = "downloads"):
        """Simulate downloading a component's artifacts."""
        if component not in self.COMPONENT_ARTIFACTS:
            self.log_step(f"Unknown component: {component}")
            return False
        
        self.log_step(f"Downloading {component}...")
        
        for artifact in self.COMPONENT_ARTIFACTS[component].get("executables", []):
            file_path = f"{base_dir}/bin/{artifact}"
            self.downloaded_files.append(file_path)
        
        for artifact in self.COMPONENT_ARTIFACTS[component].get("services", []):
            file_path = f"{base_dir}/services/{artifact}"
            self.downloaded_files.append(file_path)
        
        if "config" in self.COMPONENT_ARTIFACTS[component]:
            for config in self.COMPONENT_ARTIFACTS[component]["config"]:
                file_path = f"{base_dir}/config/{config}"
                self.downloaded_files.append(file_path)
        
        if "logrotate" in self.COMPONENT_ARTIFACTS[component]:
            for logrotate in self.COMPONENT_ARTIFACTS[component]["logrotate"]:
                file_path = f"{base_dir}/logrotate/{logrotate}"
                self.downloaded_files.append(file_path)
        
        self.log_step(f"Downloaded {len([f for f in self.downloaded_files if component in f])} {component} artifacts")
        return True
    
    def get_download_summary(self) -> Dict[str, Any]:
        """Get a summary of downloaded files."""
        return {
            "total_files": len(self.downloaded_files),
            "files": self.downloaded_files,
            "steps": self.steps
        }


class ReleasePackageCreator:
    """Simulates the ZIP packaging logic from the workflow."""
    
    def __init__(self, downloaded_files: List[str], metadata: ReleaseMetadata):
        self.downloaded_files = downloaded_files
        self.metadata = metadata
        self.package_files: List[str] = []
    
    def create_package(self, zip_filename: str) -> str:
        """Simulate creating the ZIP package."""
        self.package_files = list(set(self.downloaded_files))
        return zip_filename
    
    def cleanup_old_releases(self, releases_to_keep: int = 5) -> List[str]:
        """Simulate cleanup of old pre-releases."""
        # In real workflow, this would use GitHub API
        return []
    
    def get_package_summary(self) -> Dict[str, Any]:
        """Get a summary of the created package."""
        return {
            "package_files_count": len(self.package_files),
            "package_files": self.package_files
        }
