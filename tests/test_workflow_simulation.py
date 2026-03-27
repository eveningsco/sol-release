"""
Test module for simulating GitHub Actions workflow orchestration.

This module provides simulation classes that replicate the behavior of
the create-combined-release.yml workflow without requiring actual GitHub Actions execution.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RepositoryDispatchEvent:
    """Represents a repository_dispatch event from a component repository."""
    
    event_type: str  # e.g., "sol_software_release"
    client_payload: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_type": self.event_type,
            "client_payload": self.client_payload,
            "timestamp": self.timestamp,
            "id": self.id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepositoryDispatchEvent":
        """Create from dictionary."""
        return cls(
            event_type=data["event_type"],
            client_payload=data.get("client_payload", {}),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            id=data.get("id", str(uuid.uuid4()))
        )


@dataclass
class WorkflowEventSimulator:
    """
    Simulates GitHub repository dispatch events.
    
    This class mimics how component repositories trigger the sol-release workflow
    via repository_dispatch events.
    """
    
    event_types = {
        "sol_software": "sol_software_release",
        "sol_server": "sol_server_release",
        "sol_utils": "sol_utils_release"
    }
    
    def create_dispatch_event(
        self,
        component: str,
        branch: str,
        commit_sha: str,
        tag_name: Optional[str] = None,
        pr_number: Optional[str] = None,
        release_url: Optional[str] = None
    ) -> RepositoryDispatchEvent:
        """Create a repository dispatch event for a component release."""
        if component not in self.event_types:
            raise ValueError(f"Unknown component: {component}. Valid: {list(self.event_types.keys())}")
        
        event_type = self.event_types[component]
        
        payload = {
            "branch": branch,
            "commit_sha": commit_sha
        }
        
        if tag_name:
            payload["tag_name"] = tag_name
        if pr_number:
            payload["pr_number"] = str(pr_number)
        if release_url:
            payload["release_url"] = release_url
        
        return RepositoryDispatchEvent(
            event_type=event_type,
            client_payload=payload
        )
    
    def create_events_from_releases(self, releases: List[Dict[str, Any]]) -> List[RepositoryDispatchEvent]:
        """
        Create dispatch events from a list of release information.
        
        Args:
            releases: List of dicts with keys: component, branch, commit_sha, tag_name, pr_number
        
        Returns:
            List of RepositoryDispatchEvent objects
        """
        events = []
        for release in releases:
            event = self.create_dispatch_event(
                component=release["component"],
                branch=release["branch"],
                commit_sha=release["commit_sha"],
                tag_name=release.get("tag_name"),
                pr_number=release.get("pr_number"),
                release_url=release.get("release_url")
            )
            events.append(event)
        return events


@dataclass
class WorkflowStep:
    """Represents a single step in the workflow execution."""
    
    name: str
    status: str  # "pending", "running", "success", "failure", "skipped"
    output: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    logs: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "status": self.status,
            "output": self.output,
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "logs": self.logs
        }


@dataclass
class WorkflowRun:
    """Simulates a complete workflow run."""
    
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    triggered_by: Optional[str] = None  # "repository_dispatch" or "workflow_dispatch"
    event: Optional[RepositoryDispatchEvent] = None
    steps: List[WorkflowStep] = field(default_factory=list)
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    status: str = "pending"
    
    def add_step(self, step: WorkflowStep) -> None:
        """Add a step to the workflow run."""
        self.steps.append(step)
    
    def complete_step(self, step_name: str, status: str, output: Optional[str] = None) -> None:
        """Mark a step as complete."""
        for step in self.steps:
            if step.name == step_name:
                step.status = status
                step.end_time = datetime.now(timezone.utc).isoformat()
                if output:
                    step.output = output
                if status == "success":
                    step.logs.append(f"Step '{step_name}' completed successfully")
                elif status == "failure":
                    step.logs.append(f"Step '{step_name}' failed: {output}")
                break
    
    def mark_running_step(self, step_name: str) -> None:
        """Mark a step as running."""
        for step in self.steps:
            if step.name == step_name:
                step.status = "running"
                step.start_time = datetime.now(timezone.utc).isoformat()
                break
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "run_id": self.run_id,
            "triggered_by": self.triggered_by,
            "event": self.event.to_dict() if self.event else None,
            "steps": [s.to_dict() for s in self.steps],
            "start_time": self.start_time,
            "end_time": self.end_time,
            "status": self.status
        }


class WorkflowStepSimulator:
    """
    Simulates the execution of individual workflow steps.
    
    This class provides methods to simulate each step in the
    create-combined-release.yml workflow.
    """
    
    def __init__(self, workflow_run: WorkflowRun):
        self.workflow_run = workflow_run
        self.working_dir = "/tmp/sol-release-workflow"
        self.downloads_dir = os.path.join(self.working_dir, "downloads")
    
    def capture_dispatch_metadata(self, event: RepositoryDispatchEvent) -> Dict[str, Any]:
        """
        Simulate the 'Capture dispatch metadata' step.
        
        Extracts metadata from the repository dispatch event.
        """
        result = {
            "has_metadata": False,
            "captured_fields": {}
        }
        
        if event.event_type in WorkflowEventSimulator.event_types.values():
            result["has_metadata"] = True
            
            # Map event types to field prefixes
            prefix_map = {
                "sol_software_release": "sol_software",
                "sol_server_release": "sol_server",
                "sol_utils_release": "sol_utils"
            }
            
            prefix = prefix_map.get(event.event_type, "")
            
            payload = event.client_payload
            result["captured_fields"] = {
                f"{prefix}_branch": payload.get("branch"),
                f"{prefix}_commit": payload.get("commit_sha"),
                f"{prefix}_tag": payload.get("tag_name"),
                f"{prefix}_url": payload.get("release_url")
            }
        
        self.workflow_run.event = event
        return result
    
    def create_directory_structure(self) -> str:
        """Simulate the 'Create working directory structure' step."""
        dirs = [
            "bin",
            "services",
            "config",
            "logrotate"
        ]
        
        # Create directory structure in working dir
        for d in dirs:
            path = os.path.join(self.downloads_dir, d)
            os.makedirs(path, exist_ok=True)
        
        # Log the created structure
        output = "\n".join([
            f"Created directory: {os.path.join(self.downloads_dir, d)}"
            for d in dirs
        ])
        
        return output
    
    def simulate_download_artifact(
        self,
        component: str,
        asset_name: str,
        asset_id: str,
        output_path: str
    ) -> Dict[str, Any]:
        """
        Simulate downloading a single artifact.
        
        Returns download result with success/failure status.
        """
        result = {
            "component": component,
            "asset_name": asset_name,
            "asset_id": asset_id,
            "output_path": output_path,
            "success": True,
            "chmod_applied": not asset_name.endswith(".service") and not asset_name.endswith(".timer")
        }
        
        # Create a simulated file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(f"Simulated {asset_name} content")
        
        return result
    
    def download_component_releases(
        self,
        component: str,
        releases: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Simulate downloading all assets for a component.
        
        Args:
            component: Component name (sol-software, sol-server, sol-utils)
            releases: List of release info dicts
        
        Returns:
            List of download results
        """
        results = []
        
        for release_info in releases:
            for asset in release_info.get("assets", []):
                output_path = os.path.join(self.downloads_dir, asset["path"])
                result = self.simulate_download_artifact(
                    component=component,
                    asset_name=asset["name"],
                    asset_id=asset.get("id", "simulated"),
                    output_path=output_path
                )
                results.append(result)
        
        return results
    
    def create_metadata_file(
        self,
        release_version: str,
        build_date: str,
        components_metadata: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Simulate creating the metadata.json file."""
        metadata = {
            "release_version": release_version,
            "build_date": build_date,
            "triggered_by": self.workflow_run.triggered_by,
            "components": {}
        }
        
        for comp_meta in components_metadata:
            component_name = comp_meta["component"]
            # Normalize component name for metadata
            normalized_name = component_name.replace("-", "")
            if normalized_name not in metadata["components"]:
                metadata["components"][normalized_name] = {
                    "included": True,
                    "branch": comp_meta.get("branch"),
                    "commit_sha": comp_meta.get("commit_sha"),
                    "tag_name": comp_meta.get("tag_name")
                }
        
        # Write metadata file
        metadata_path = os.path.join(self.downloads_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return {
            "path": metadata_path,
            "metadata": metadata,
            "success": True
        }
    
    def create_release_package(self) -> Dict[str, Any]:
        """Simulate creating the ZIP release package."""
        package_name = f"sol-release-{datetime.now(timezone.utc).strftime('%m%d%Y_%H-%M-%S')}.zip"
        package_path = os.path.join(self.working_dir, package_name)
        
        # Simulate creating the zip
        with open(package_path, "w") as f:
            f.write("Simulated ZIP package")
        
        return {
            "package_name": package_name,
            "package_path": package_path,
            "size_bytes": os.path.getsize(package_path),
            "success": True
        }
    
    def generate_release_body(
        self,
        metadata_path: str
    ) -> str:
        """Simulate generating the release body text."""
        with open(metadata_path, "r") as f:
            metadata = json.load(f)
        
        lines = [
            "Combined SOL release package",
            f"Build date: {metadata.get('release_version', 'Unknown')}",
            "",
            "## Component Sources"
        ]
        
        for component, comp_data in metadata.get("components", {}).items():
            branch = comp_data.get("branch", "unknown")
            commit = comp_data.get("commit_sha", "")[:7] if comp_data.get("commit_sha") else ""
            tag = comp_data.get("tag_name", "latest")
            
            lines.append(f"\n- **{component}** {tag} (branch: {branch}, commit: {commit})")
        
        lines.extend([
            "",
            "## Included Files",
            "",
            "### Executables",
            "- sol-server.zip",
            "- sol_software",
            "- sol_update_*",
            "",
            "### Service Files",
            "- *.service",
            "- *.timer"
        ])
        
        return "\n".join(lines)


class CombinedReleaseSimulator:
    """
    High-level simulator for the complete combined release workflow.
    
    Orchestrates the entire release creation process from trigger to final package.
    """
    
    def __init__(self):
        self.event_simulator = WorkflowEventSimulator()
        self.workflow_run: Optional[WorkflowRun] = None
        self.step_simulator: Optional[WorkflowStepSimulator] = None
    
    def trigger_workflow(
        self,
        event_type: Optional[str] = None,
        component: Optional[str] = None,
        branch: Optional[str] = None,
        commit_sha: Optional[str] = None,
        tag_name: Optional[str] = None,
        pr_number: Optional[str] = None
    ) -> WorkflowRun:
        """
        Trigger a workflow run.
        
        Args:
            event_type: Repository dispatch event type
            component: Component name triggering the release
            branch: Branch name
            commit_sha: Commit SHA
            tag_name: Release tag
            pr_number: Pull request number
        
        Returns:
            The WorkflowRun object
        """
        if event_type == "repository_dispatch":
            if not component or not branch or not commit_sha:
                raise ValueError("Component, branch, and commit_sha required for repository_dispatch")
            
            event = self.event_simulator.create_dispatch_event(
                component=component,
                branch=branch,
                commit_sha=commit_sha,
                tag_name=tag_name,
                pr_number=pr_number
            )
            
            self.workflow_run = WorkflowRun(
                triggered_by="repository_dispatch",
                event=event
            )
        else:
            self.workflow_run = WorkflowRun(triggered_by="workflow_dispatch")
        
        return self.workflow_run
    
    def execute_workflow(self, releases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Execute the complete workflow simulation.
        
        Args:
            releases: List of release information for each component
        
        Returns:
            Dictionary with workflow execution results
        """
        if not self.workflow_run:
            raise RuntimeError("Workflow not triggered. Call trigger_workflow() first.")
        
        self.step_simulator = WorkflowStepSimulator(self.workflow_run)
        
        # Simulate steps
        metadata_result = self.step_simulator.capture_dispatch_metadata(
            self.workflow_run.event
        ) if self.workflow_run.event else {"has_metadata": False}
        
        dir_structure = self.step_simulator.create_directory_structure()
        
        # Process each component release
        components_metadata = []
        all_downloads = []
        for release_info in releases:
            downloads = self.step_simulator.download_component_releases(
                component=release_info["component"],
                releases=[release_info]
            )
            all_downloads.extend(downloads)
            
            components_metadata.append({
                "component": release_info["component"],
                "branch": release_info.get("branch"),
                "commit_sha": release_info.get("commit_sha"),
                "tag_name": release_info.get("tag_name")
            })
        
        # Create metadata file
        metadata_file = self.step_simulator.create_metadata_file(
            release_version=f"Release-{datetime.now(timezone.utc).strftime('%m%d%Y_%H-%M-%S')}",
            build_date=datetime.now(timezone.utc).isoformat(),
            components_metadata=components_metadata
        )
        
        # Create release package
        package = self.step_simulator.create_release_package()
        
        # Generate release body
        release_body = self.step_simulator.generate_release_body(metadata_file["path"])
        
        return {
            "workflow_run": self.workflow_run.to_dict(),
            "metadata_captured": metadata_result,
            "directory_structure": dir_structure,
            "downloads": all_downloads,
            "metadata_file": metadata_file,
            "package": package,
            "release_body": release_body
        }
    
    def reset(self) -> None:
        """Reset the simulator state."""
        self.workflow_run = None
        self.step_simulator = None


# Module-level convenience functions
def create_dispatch_event(
    component: str,
    branch: str,
    commit_sha: str,
    tag_name: Optional[str] = None
) -> RepositoryDispatchEvent:
    """Create a repository dispatch event."""
    simulator = WorkflowEventSimulator()
    return simulator.create_dispatch_event(component, branch, commit_sha, tag_name)


def simulate_release_workflow(
    releases: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Simulate a complete release workflow.
    
    Convenience function for testing.
    
    Args:
        releases: List of release information dictionaries
    
    Returns:
        Workflow execution results
    """
    simulator = CombinedReleaseSimulator()
    
    # Trigger with repository_dispatch
    simulator.trigger_workflow(
        event_type="repository_dispatch",
        component=releases[0]["component"] if releases else "sol-software",
        branch=releases[0]["branch"] if releases else "main",
        commit_sha=releases[0]["commit_sha"] if releases else "abc123"
    )
    
    return simulator.execute_workflow(releases)


def test_workflow_simulation():
    """Test the workflow simulation with sample data."""
    sample_releases = [
        {
            "component": "sol-software",
            "branch": "main",
            "commit_sha": "abc123def456",
            "tag_name": "v1.2.3",
            "pr_number": "42",
            "assets": [
                {"name": "sol_software", "path": "bin/sol_software"},
                {"name": "sol_software.service", "path": "services/sol_software.service"}
            ]
        },
        {
            "component": "sol-server",
            "branch": "develop",
            "commit_sha": "789ghi012jkl",
            "tag_name": "v2.0.0",
            "assets": [
                {"name": "sol-server.zip", "path": "bin/sol-server.zip"},
                {"name": "sol-server.service", "path": "services/sol-server.service"}
            ]
        },
        {
            "component": "sol-utils",
            "branch": "main",
            "commit_sha": "mno345pqr678",
            "tag_name": "v1.0.0",
            "assets": [
                {"name": "sol_update_gui", "path": "bin/sol_update_gui"},
                {"name": "mass_gadget_watchdog.service", "path": "services/mass_gadget_watchdog.service"}
            ]
        }
    ]
    
    simulator = CombinedReleaseSimulator()
    
    # Trigger workflow first
    simulator.trigger_workflow(
        event_type="repository_dispatch",
        component="sol_software",  # Use underscore for internal naming
        branch="main",
        commit_sha="abc123def456"
    )
    
    result = simulator.execute_workflow(sample_releases)
    
    # Assertions
    assert result["metadata_captured"]["has_metadata"]
    assert len(result["downloads"]) == len(sum([r.get("assets", []) for r in sample_releases], []))
    assert result["metadata_file"]["success"]
    assert result["package"]["success"]


# ============================================================================
# Unit Tests for Workflow Simulation
# ============================================================================

def test_workflow_event_simulator_create_dispatch_event():
    """Test creating dispatch events for different components."""
    simulator = WorkflowEventSimulator()
    
    # Test sol_software component
    event = simulator.create_dispatch_event(
        component="sol_software",
        branch="main",
        commit_sha="abc123",
        tag_name="v1.0.0"
    )
    assert event.event_type == "sol_software_release"
    assert event.client_payload["branch"] == "main"
    assert event.client_payload["commit_sha"] == "abc123"
    assert event.client_payload["tag_name"] == "v1.0.0"
    
    # Test invalid component
    try:
        simulator.create_dispatch_event(
            component="invalid",
            branch="main",
            commit_sha="abc123"
        )
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown component" in str(e)


def test_workflow_event_simulator_event_types():
    """Test that all event types are correctly mapped."""
    simulator = WorkflowEventSimulator()
    
    assert simulator.event_types["sol_software"] == "sol_software_release"
    assert simulator.event_types["sol_server"] == "sol_server_release"
    assert simulator.event_types["sol_utils"] == "sol_utils_release"


def test_repository_dispatch_event_serialization():
    """Test RepositoryDispatchEvent to_dict and from_dict."""
    event = RepositoryDispatchEvent(
        event_type="sol_software_release",
        client_payload={
            "branch": "main",
            "commit_sha": "abc123",
            "tag_name": "v1.0.0"
        }
    )
    
    data = event.to_dict()
    restored = RepositoryDispatchEvent.from_dict(data)
    
    assert restored.event_type == event.event_type
    assert restored.client_payload == event.client_payload


def test_workflow_run_step_management():
    """Test adding and managing workflow steps."""
    workflow_run = WorkflowRun()
    
    step1 = WorkflowStep(name="Step 1", status="pending")
    step2 = WorkflowStep(name="Step 2", status="pending")
    
    workflow_run.add_step(step1)
    workflow_run.add_step(step2)
    
    assert len(workflow_run.steps) == 2
    assert workflow_run.steps[0].name == "Step 1"
    assert workflow_run.steps[1].name == "Step 2"


def test_workflow_run_complete_step():
    """Test completing a workflow step."""
    workflow_run = WorkflowRun()
    
    step = WorkflowStep(name="Test Step", status="pending")
    workflow_run.add_step(step)
    
    workflow_run.complete_step("Test Step", "success", "All tasks completed")
    
    assert step.status == "success"
    assert "completed successfully" in step.logs[0]


def test_workflow_step_simulator_directory_structure():
    """Test creating directory structure in step simulator."""
    workflow_run = WorkflowRun(triggered_by="workflow_dispatch")
    simulator = WorkflowStepSimulator(workflow_run)
    
    result = simulator.create_directory_structure()
    
    assert "bin" in result
    assert "services" in result
    assert "config" in result
    assert "logrotate" in result


def test_workflow_step_simulator_metadata_capture():
    """Test capturing dispatch metadata."""
    event = RepositoryDispatchEvent(
        event_type="sol_software_release",
        client_payload={
            "branch": "feature",
            "commit_sha": "def456",
            "tag_name": "v2.0.0",
            "release_url": "https://github.com/..."
        }
    )
    
    workflow_run = WorkflowRun(triggered_by="repository_dispatch", event=event)
    simulator = WorkflowStepSimulator(workflow_run)
    
    result = simulator.capture_dispatch_metadata(event)
    
    assert result["has_metadata"] is True
    assert result["captured_fields"]["sol_software_branch"] == "feature"
    assert result["captured_fields"]["sol_software_commit"] == "def456"
    assert result["captured_fields"]["sol_software_tag"] == "v2.0.0"


def test_combined_release_simulator_reset():
    """Test that reset clears simulator state."""
    simulator = CombinedReleaseSimulator()
    
    # Trigger workflow
    simulator.trigger_workflow(
        event_type="repository_dispatch",
        component="sol_software",
        branch="main",
        commit_sha="abc123"
    )
    
    assert simulator.workflow_run is not None
    assert simulator.step_simulator is None
    
    # Reset
    simulator.reset()
    
    assert simulator.workflow_run is None
    assert simulator.step_simulator is None


def test_dispatch_event_without_optional_fields():
    """Test creating events with minimal required fields."""
    simulator = WorkflowEventSimulator()
    
    event = simulator.create_dispatch_event(
        component="sol_server",
        branch="main",
        commit_sha="simple"
    )
    
    assert event.event_type == "sol_server_release"
    assert event.client_payload["branch"] == "main"
    assert "tag_name" not in event.client_payload
    assert "pr_number" not in event.client_payload


def test_workflow_run_to_dict():
    """Test converting WorkflowRun to dictionary."""
    workflow_run = WorkflowRun(
        run_id="test-run-id",
        triggered_by="repository_dispatch"
    )
    
    step = WorkflowStep(name="Test", status="success")
    workflow_run.add_step(step)
    
    data = workflow_run.to_dict()
    
    assert data["run_id"] == "test-run-id"
    assert data["triggered_by"] == "repository_dispatch"
    assert len(data["steps"]) == 1


def test_simulate_download_artifact_with_chmod():
    """Test artifact download with and without chmod."""
    workflow_run = WorkflowRun(triggered_by="workflow_dispatch")
    simulator = WorkflowStepSimulator(workflow_run)
    
    # Executable - should apply chmod
    result1 = simulator.simulate_download_artifact(
        component="sol-utils",
        asset_name="sol_update_gui",
        asset_id="123",
        output_path="/tmp/test/executable"
    )
    assert result1["chmod_applied"] is True
    
    # Service file - should NOT apply chmod
    result2 = simulator.simulate_download_artifact(
        component="sol-server",
        asset_name="sol-server.service",
        asset_id="124",
        output_path="/tmp/test/service"
    )
    assert result2["chmod_applied"] is False


def test_create_metadata_file_with_components():
    """Test creating metadata file with multiple components."""
    workflow_run = WorkflowRun(
        triggered_by="repository_dispatch",
        event=RepositoryDispatchEvent(
            event_type="sol_software_release",
            client_payload={}
        )
    )
    simulator = WorkflowStepSimulator(workflow_run)
    
    components_metadata = [
        {
            "component": "sol-software",
            "branch": "main",
            "commit_sha": "abc123",
            "tag_name": "v1.0.0"
        },
        {
            "component": "sol-server",
            "branch": "develop",
            "commit_sha": "def456",
            "tag_name": "v2.0.0"
        }
    ]
    
    result = simulator.create_metadata_file(
        release_version="Release-03272025",
        build_date="2025-03-27T10:30:00Z",
        components_metadata=components_metadata
    )
    
    assert result["success"] is True
    assert "components" in result["metadata"]
    assert "solsoftware" in result["metadata"]["components"]


if __name__ == "__main__":
    # Run all tests
    test_workflow_event_simulator_create_dispatch_event()
    test_workflow_event_simulator_event_types()
    test_repository_dispatch_event_serialization()
    test_workflow_run_step_management()
    test_workflow_run_complete_step()
    test_workflow_step_simulator_directory_structure()
    test_workflow_step_simulator_metadata_capture()
    test_combined_release_simulator_reset()
    test_dispatch_event_without_optional_fields()
    test_workflow_run_to_dict()
    test_simulate_download_artifact_with_chmod()
    test_create_metadata_file_with_components()
    test_workflow_simulation()
