"""
Test module for sol-release metadata generation and handling.
Simulates the metadata merging logic from create-combined-release.yml workflow.
"""

import json
import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any


class ComponentMetadata:
    """Represents metadata from a component repository release."""
    
    def __init__(
        self,
        branch: Optional[str] = None,
        commit_sha: Optional[str] = None,
        tag_name: Optional[str] = None,
        release_url: Optional[str] = None,
        pr_number: Optional[str] = None,
        pr_commits: Optional[list] = None,
        included: bool = False
    ):
        self.branch = branch
        self.commit_sha = commit_sha
        self.tag_name = tag_name
        self.release_url = release_url
        self.pr_number = pr_number
        self.pr_commits = pr_commits or []
        self.included = included
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "tag_name": self.tag_name,
            "release_url": self.release_url,
            "pr_number": self.pr_number,
            "pr_commits": self.pr_commits,
            "included": self.included
        }
        # Remove None values
        return {k: v for k, v in data.items() if v is not None}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ComponentMetadata":
        """Create from dictionary."""
        return cls(
            branch=data.get("branch"),
            commit_sha=data.get("commit_sha"),
            tag_name=data.get("tag_name"),
            release_url=data.get("release_url"),
            pr_number=data.get("pr_number"),
            pr_commits=data.get("pr_commits", []),
            included=data.get("included", False)
        )


class CombinedMetadata:
    """Represents the combined metadata for a release package."""
    
    VALID_COMPONENTS = ["sol-software", "sol-server", "sol-utils"]
    
    def __init__(self, release_version: str, build_date: str):
        self.release_version = release_version
        self.build_date = build_date
        self.triggered_by: Optional[str] = None
        self.components: Dict[str, Dict[str, Any]] = {}
    
    def add_component(self, component_name: str, metadata: ComponentMetadata) -> None:
        """Add component metadata to the combined metadata."""
        if component_name not in self.VALID_COMPONENTS:
            raise ValueError(f"Invalid component: {component_name}. Valid: {self.VALID_COMPONENTS}")
        
        self.components[component_name] = metadata.to_dict()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = {
            "release_version": self.release_version,
            "build_date": self.build_date,
            "components": self.components
        }
        if self.triggered_by:
            data["triggered_by"] = self.triggered_by
        return data
    
    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    @classmethod
    def from_json(cls, json_str: str) -> "CombinedMetadata":
        """Create from JSON string."""
        data = json.loads(json_str)
        metadata = cls(
            release_version=data["release_version"],
            build_date=data["build_date"]
        )
        metadata.triggered_by = data.get("triggered_by")
        for comp_name, comp_data in data.get("components", {}).items():
            metadata.components[comp_name] = comp_data
        return metadata


class MetadataMerger:
    """
    Handles merging of component metadata files.
    
    This simulates the logic in the "Create combined metadata file" step
    of the GitHub Actions workflow.
    """
    
    def __init__(self):
        self.metadata = CombinedMetadata("", "")
        self.component_files: Dict[str, str] = {
            "sol-software": "sol-software-metadata.json",
            "sol-server": "sol-server-metadata.json",
            "sol-utils": "sol-utils-metadata.json"
        }
    
    def initialize(
        self,
        release_version: str,
        build_date: str,
        triggered_by: Optional[str] = None
    ) -> None:
        """Initialize the metadata object."""
        self.metadata = CombinedMetadata(release_version, build_date)
        self.metadata.triggered_by = triggered_by
    
    def _handle_component(
        self,
        component_name: str,
        metadata_file: str
    ) -> bool:
        """
        Handle a single component metadata file.
        
        Returns True if the component was successfully processed, False otherwise.
        """
        if not os.path.exists(metadata_file):
            # Mark as included without detailed metadata
            component_meta = ComponentMetadata(included=True)
            self.metadata.add_component(component_name, component_meta)
            return True
        
        try:
            with open(metadata_file, "r") as f:
                component_data = json.load(f)
            
            # Handle both dictionary and list formats
            if isinstance(component_data, list):
                # If it's a list, find the relevant fields
                for item in component_data:
                    if component_name.replace("-", "") in item.get("name", "").lower():
                        component_data = item
                        break
            
            component_meta = ComponentMetadata.from_dict(component_data)
            self.metadata.add_component(component_name, component_meta)
            return True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error processing {metadata_file}: {e}")
            # Fallback to included=True
            component_meta = ComponentMetadata(included=True)
            self.metadata.add_component(component_name, component_meta)
            return True
    
    def merge_all_components(
        self,
        working_dir: Optional[str] = None
    ) -> CombinedMetadata:
        """
        Merge all component metadata files.
        
        Args:
            working_dir: Directory to look for metadata files. If None, uses current directory.
        
        Returns:
            The combined metadata object.
        """
        if working_dir:
            original_cwd = os.getcwd()
            os.chdir(working_dir)
        
        try:
            for component_name, filename in self.component_files.items():
                self._handle_component(component_name, filename)
        finally:
            if working_dir:
                os.chdir(original_cwd)
        
        return self.metadata
    
    def get_component_status(self, component_name: str) -> Dict[str, Any]:
        """Get the status of a specific component in the combined metadata."""
        if component_name not in self.metadata.components:
            return {"exists": False, "data": None}
        
        data = self.metadata.components[component_name]
        return {
            "exists": True,
            "included": data.get("included", False),
            "has_branch": "branch" in data and data["branch"] is not None,
            "has_commit": "commit_sha" in data and data["commit_sha"] is not None,
            "has_tag": "tag_name" in data and data["tag_name"] is not None
        }


class MetadataBuilder:
    """
    Builder pattern for constructing CombinedMetadata objects.
    
    Provides a fluent interface for creating metadata structures.
    """
    
    def __init__(self):
        self._release_version = ""
        self._build_date = ""
        self._triggered_by = None
        self._components: Dict[str, ComponentMetadata] = {}
    
    def set_release_version(self, version: str) -> "MetadataBuilder":
        """Set the release version."""
        self._release_version = version
        return self
    
    def set_build_date(self, date: str) -> "MetadataBuilder":
        """Set the build date in ISO format."""
        self._build_date = date
        return self
    
    def set_triggered_by(self, event_type: str) -> "MetadataBuilder":
        """Set the trigger event type."""
        self._triggered_by = event_type
        return self
    
    def add_component(
        self,
        name: str,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        tag: Optional[str] = None,
        pr_number: Optional[str] = None,
        pr_commits: Optional[list] = None,
        included: bool = False
    ) -> "MetadataBuilder":
        """Add a component with its metadata."""
        self._components[name] = ComponentMetadata(
            branch=branch,
            commit_sha=commit,
            tag_name=tag,
            pr_number=pr_number,
            pr_commits=pr_commits,
            included=included
        )
        return self
    
    def build(self) -> CombinedMetadata:
        """Build the CombinedMetadata object."""
        metadata = CombinedMetadata(self._release_version, self._build_date)
        metadata.triggered_by = self._triggered_by
        
        for name, component in self._components.items():
            metadata.add_component(name, component)
        
        return metadata


def test_metadata_builder_fluent_interface():
    """Test that the metadata builder provides a fluent interface."""
    metadata = (
        MetadataBuilder()
        .set_release_version("Release-03272025_10-30-00")
        .set_build_date("2025-03-27T10:30:00Z")
        .set_triggered_by("repository_dispatch")
        .add_component(
            "sol-software",
            branch="main",
            commit="abc123def456",
            tag="v1.2.3",
            pr_number="42"
        )
        .add_component(
            "sol-server",
            branch="develop",
            commit="789ghi012jkl"
        )
        .build()
    )
    
    assert metadata.release_version == "Release-03272025_10-30-00"
    assert metadata.build_date == "2025-03-27T10:30:00Z"
    assert metadata.triggered_by == "repository_dispatch"
    assert "sol-software" in metadata.components
    assert "sol-server" in metadata.components
    assert "sol-utils" not in metadata.components


def test_component_metadata_serialization():
    """Test that component metadata can be serialized and deserialized."""
    component = ComponentMetadata(
        branch="main",
        commit_sha="abcdef123456",
        tag_name="v2.0.0",
        pr_number="15",
        pr_commits=["commit1", "commit2"]
    )
    
    # Test to_dict
    data = component.to_dict()
    assert data["branch"] == "main"
    assert data["commit_sha"] == "abcdef123456"
    assert data["tag_name"] == "v2.0.0"
    assert data["pr_number"] == "15"
    assert data["pr_commits"] == ["commit1", "commit2"]
    
    # Test from_dict
    component2 = ComponentMetadata.from_dict(data)
    assert component2.branch == component.branch
    assert component2.commit_sha == component.commit_sha
    assert component2.tag_name == component.tag_name


def test_combined_metadata_json_roundtrip():
    """Test that CombinedMetadata can be serialized to JSON and back."""
    original = (
        CombinedMetadata("Release-03272025", "2025-03-27T10:30:00Z")
    )
    original.triggered_by = "repository_dispatch"
    
    component = ComponentMetadata(
        branch="main",
        commit_sha="test123",
        tag_name="v1.0.0"
    )
    original.add_component("sol-software", component)
    
    # Serialize to JSON
    json_str = original.to_json()
    
    # Deserialize from JSON
    restored = CombinedMetadata.from_json(json_str)
    
    assert restored.release_version == original.release_version
    assert restored.build_date == original.build_date
    assert restored.triggered_by == original.triggered_by
    assert "sol-software" in restored.components


def test_metadata_merger_with_missing_files():
    """Test that the merger handles missing metadata files gracefully."""
    merger = MetadataMerger()
    merger.initialize(
        release_version="Release-03272025",
        build_date="2025-03-27T10:30:00Z",
        triggered_by="workflow_dispatch"
    )
    
    # Create a temporary directory with no metadata files
    with tempfile.TemporaryDirectory() as tmpdir:
        merged = merger.merge_all_components(working_dir=tmpdir)
        
        # All components should be marked as included
        for component_name in CombinedMetadata.VALID_COMPONENTS:
            status = merger.get_component_status(component_name)
            assert status["exists"], f"Component {component_name} should exist"
            assert status["included"], f"Component {component_name} should be included"


def test_metadata_merger_with_partial_files():
    """Test merger when some components have metadata files."""
    merger = MetadataMerger()
    merger.initialize(
        release_version="Release-03272025",
        build_date="2025-03-27T10:30:00Z"
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create only one metadata file
        software_meta = {
            "branch": "main",
            "commit_sha": "abc123",
            "tag_name": "v1.0.0",
            "pr_number": "10"
        }
        software_file = os.path.join(tmpdir, "sol-software-metadata.json")
        with open(software_file, "w") as f:
            json.dump(software_meta, f)
        
        merged = merger.merge_all_components(working_dir=tmpdir)
        
        # sol-software should have full metadata
        software_status = merger.get_component_status("sol-software")
        assert software_status["has_branch"], "Should have branch"
        assert software_status["has_commit"], "Should have commit"
        assert software_status["has_tag"], "Should have tag"
        
        # Other components should be marked as included
        utils_status = merger.get_component_status("sol-utils")
        server_status = merger.get_component_status("sol-server")
        assert utils_status["included"], "sol-utils should be included"
        assert server_status["included"], "sol-server should be included"


def test_component_metadata_with_none_values():
    """Test that None values are properly excluded from serialized data."""
    component = ComponentMetadata(included=True)
    data = component.to_dict()
    
    assert "branch" not in data
    assert "commit_sha" not in data
    assert "tag_name" not in data
    assert "included" in data
    assert data["included"] is True


def test_invalid_component_rejected():
    """Test that invalid component names are rejected."""
    metadata = CombinedMetadata("Release-03272025", "2025-03-27T10:30:00Z")
    component = ComponentMetadata(included=True)
    
    try:
        metadata.add_component("invalid-component", component)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Invalid component" in str(e)


def test_release_version_format():
    """Test that release versions follow the expected format."""
    # Valid format: Release-MMDDYYYY_HH-MM-SS
    valid_versions = [
        "Release-01252025_14-30-45",
        "Release-03272025_10-30-00",
        "Release-12312024_23-59-59"
    ]
    
    for version in valid_versions:
        metadata = CombinedMetadata(version, "2025-03-27T10:30:00Z")
        assert version in metadata.to_json()


def test_component_with_pr_commits():
    """Test component metadata with PR commits information."""
    component = ComponentMetadata(
        branch="feature-branch",
        commit_sha="def456",
        tag_name="v1.1.0",
        pr_number="100",
        pr_commits=[
            {"sha": "abc1", "message": "First commit"},
            {"sha": "def2", "message": "Second commit"}
        ]
    )
    
    data = component.to_dict()
    assert data["pr_number"] == "100"
    assert len(data["pr_commits"]) == 2
    assert data["pr_commits"][0]["sha"] == "abc1"


def test_combined_metadata_empty_components():
    """Test that combined metadata handles empty component list."""
    metadata = CombinedMetadata("Release-03272025", "2025-03-27T10:30:00Z")
    data = metadata.to_dict()
    
    assert data["release_version"] == "Release-03272025"
    assert data["build_date"] == "2025-03-27T10:30:00Z"
    assert data["components"] == {}


def test_metadata_builder_chaining():
    """Test that builder methods return self for chaining."""
    builder = MetadataBuilder()
    
    result1 = builder.set_release_version("test")
    assert result1 is builder
    
    result2 = builder.set_build_date("2025-01-01")
    assert result2 is builder
    
    result3 = builder.add_component("sol-software", branch="main")
    assert result3 is builder


if __name__ == "__main__":
    # Run all test functions
    test_metadata_builder_fluent_interface()
    test_component_metadata_serialization()
    test_combined_metadata_json_roundtrip()
    test_metadata_merger_with_missing_files()
    test_metadata_merger_with_partial_files()
    test_component_metadata_with_none_values()
    test_invalid_component_rejected()
    test_release_version_format()
    test_component_with_pr_commits()
    test_combined_metadata_empty_components()
    test_metadata_builder_chaining()
    print("All metadata tests passed!")
