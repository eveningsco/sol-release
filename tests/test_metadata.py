"""Tests for metadata generation logic.

These tests validate the workflow's metadata collection and component tracking.
"""

import json
import pytest
from tests.mocks import (
    ReleaseMetadata,
    WorkflowMetadataCollector,
    ReleaseBodyGenerator,
    ReleasePackageCreator,
    ArtifactDownloaderSimulator
)


class TestReleaseMetadata:
    """Tests for the ReleaseMetadata class."""
    
    def test_initialize_empty_metadata(self):
        """Test that metadata initializes with empty values."""
        metadata = ReleaseMetadata()
        assert metadata.release_version == ""
        assert metadata.build_date == ""
        assert metadata.triggered_by == ""
        assert metadata.components == {}
    
    def test_to_dict_returns_correct_structure(self):
        """Test that to_dict returns a properly structured dictionary."""
        metadata = ReleaseMetadata()
        metadata.release_version = "Release-01012025_12-00-00"
        metadata.build_date = "2025-01-01T12:00:00Z"
        metadata.triggered_by = "repository_dispatch"
        metadata.components = {"sol-software": {"included": True}}
        
        result = metadata.to_dict()
        assert result["release_version"] == "Release-01012025_12-00-00"
        assert result["build_date"] == "2025-01-01T12:00:00Z"
        assert result["triggered_by"] == "repository_dispatch"
        assert "sol-software" in result["components"]
    
    def test_to_json_serializes_correctly(self):
        """Test that to_json produces valid JSON."""
        import json
        metadata = ReleaseMetadata()
        metadata.release_version = "Release-01012025_12-00-00"
        metadata.build_date = "2025-01-01T12:00:00Z"
        metadata.triggered_by = "repository_dispatch"
        
        json_str = metadata.to_json()
        parsed = json.loads(json_str)
        
        assert parsed["release_version"] == "Release-01012025_12-00-00"
        assert "components" in parsed
    
    def test_from_json_deserializes_correctly(self):
        """Test that from_json correctly parses JSON string."""
        json_str = json.dumps({
            "release_version": "Release-01012025_12-00-00",
            "build_date": "2025-01-01T12:00:00Z",
            "triggered_by": "repository_dispatch",
            "components": {
                "sol-software": {"included": True, "branch": "main"},
                "sol-server": {"included": True}
            }
        })
        
        metadata = ReleaseMetadata.from_json(json_str)
        
        assert metadata.release_version == "Release-01012025_12-00-00"
        assert "sol-software" in metadata.components
        assert metadata.components["sol-software"]["branch"] == "main"
        assert "sol-server" in metadata.components
    
    def test_metadata_persistence(self):
        """Test that metadata survives to_json/from_json round-trip."""
        original = ReleaseMetadata()
        original.release_version = "Release-01012025_12-00-00"
        original.triggered_by = "workflow_dispatch"
        original.components["test-component"] = {"branch": "test"}
        
        serialized = original.to_json()
        deserialized = ReleaseMetadata.from_json(serialized)
        
        assert original.release_version == deserialized.release_version
        assert original.triggered_by == deserialized.triggered_by
        assert "test-component" in deserialized.components


class TestWorkflowMetadataCollector:
    """Tests for the WorkflowMetadataCollector class."""
    
    def test_initialize_with_dispatch(self):
        """Test initialization with repository_dispatch trigger."""
        collector = WorkflowMetadataCollector()
        collector.initialize("repository_dispatch")
        
        assert collector.metadata.triggered_by == "repository_dispatch"
        assert "202" in collector.metadata.build_date  # Valid ISO timestamp
        assert len(collector.workflow_steps) >= 1
    
    def test_initialize_with_manual_trigger(self):
        """Test initialization with workflow_dispatch trigger."""
        collector = WorkflowMetadataCollector()
        collector.initialize("workflow_dispatch")
        
        assert collector.metadata.triggered_by == "workflow_dispatch"
    
    def test_parse_dispatch_event_sol_software(self):
        """Test parsing sol-software release dispatch event."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        payload = {
            "sol_software_branch": "main",
            "sol_software_commit": "abc123def456",
            "sol_software_tag": "v1.0.0",
            "sol_software_url": "https://github.com/eveningsco/sol-software/releases/123"
        }
        
        result = collector.parse_dispatch_event("sol_software_release", payload)
        
        assert result is True
        assert "sol-software" in collector.metadata.components
        assert collector.metadata.components["sol-software"]["branch"] == "main"
        assert collector.metadata.components["sol-software"]["commit_sha"] == "abc123def456"
    
    def test_parse_dispatch_event_sol_server(self):
        """Test parsing sol-server release dispatch event."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        payload = {
            "sol_server_branch": "develop",
            "sol_server_commit": "xyz789",
            "sol_server_tag": "v2.0.0",
            "sol_server_url": "https://github.com/eveningsco/sol-server/releases/456"
        }
        
        result = collector.parse_dispatch_event("sol_server_release", payload)
        
        assert result is True
        assert "sol-server" in collector.metadata.components
    
    def test_parse_dispatch_event_sol_utils(self):
        """Test parsing sol-utils release dispatch event."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        payload = {
            "sol_utils_branch": "feature/update",
            "sol_utils_commit": "feat123",
            "sol_utils_tag": "v1.5.0",
            "sol_utils_url": "https://github.com/eveningsco/sol-utils/releases/789"
        }
        
        result = collector.parse_dispatch_event("sol_utils_release", payload)
        
        assert result is True
        assert "sol-utils" in collector.metadata.components
    
    def test_parse_dispatch_event_with_missing_payload(self):
        """Test handling dispatch event with no payload."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        result = collector.parse_dispatch_event("sol_software_release", None)
        
        assert result is False
    
    def test_parse_dispatch_event_unknown_action(self):
        """Test handling unknown dispatch event action."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        payload = {
            "sol_software_branch": "main",
            "sol_software_commit": "abc123",
            "sol_software_tag": "v1.0.0"
        }
        
        result = collector.parse_dispatch_event("unknown_event", payload)
        
        assert result is False
    
    def test_mark_component_included(self):
        """Test marking a component as included."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        result = collector.mark_component_included("sol-server")
        
        assert result is True
        assert "sol-server" in collector.metadata.components
        assert collector.metadata.components["sol-server"]["included"] is True
    
    def test_workflow_steps_logging(self):
        """Test that workflow steps are properly logged."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        collector.log_step("Test step 1")
        collector.log_step("Test step 2")
        
        assert len(collector.workflow_steps) == 3  # initialize + 2 steps
        assert "Test step 1" in collector.workflow_steps
        assert "Test step 2" in collector.workflow_steps
    
    def test_get_workflow_summary(self):
        """Test workflow summary generation."""
        collector = WorkflowMetadataCollector()
        collector.initialize("repository_dispatch")
        
        payload = {
            "sol_software_branch": "main",
            "sol_software_commit": "abc123",
            "sol_software_tag": "v1.0.0"
        }
        collector.parse_dispatch_event("sol_software_release", payload)
        
        summary = collector.get_workflow_summary()
        
        assert summary["triggered_by"] == "repository_dispatch"
        assert "sol-software" in summary["components"]
        assert summary["steps_count"] >= 2


class TestReleaseBodyGenerator:
    """Tests for the ReleaseBodyGenerator class."""
    
    def test_generate_body_contains_components_section(self):
        """Test that generated body includes component sources."""
        metadata = ReleaseMetadata()
        metadata.build_date = "2025-01-01T12:00:00Z"
        metadata.components["sol-software"] = {
            "branch": "main",
            "commit_sha": "abc123def456",
            "tag_name": "v1.0.0"
        }
        
        generator = ReleaseBodyGenerator(metadata)
        body = generator.generate_body()
        
        assert "## Component Sources" in body
        assert "sol-software" in body
    
    def test_generate_body_contains_all_sections(self):
        """Test that generated body has all expected sections."""
        metadata = ReleaseMetadata()
        metadata.build_date = "2025-01-01T12:00:00Z"
        
        generator = ReleaseBodyGenerator(metadata)
        body = generator.generate_body()
        
        assert "## Component Sources" in body
        assert "## Included Files" in body
        assert "### Executables:" in body
        assert "### Service Files:" in body
        assert "### Config Files:" in body
        assert "### Logrotate Files:" in body
    
    def test_generate_body_contains_executables(self):
        """Test that generated body lists all executables."""
        metadata = ReleaseMetadata()
        metadata.build_date = "2025-01-01T12:00:00Z"
        
        generator = ReleaseBodyGenerator(metadata)
        body = generator.generate_body()
        
        assert "sol-server.zip" in body
        assert "sol_software" in body
        assert "sol_update_gui" in body
        assert "mass_gadget_watchdog" in body
        assert "provision" in body
    
    def test_generate_body_contains_service_files(self):
        """Test that generated body lists service files."""
        metadata = ReleaseMetadata()
        metadata.build_date = "2025-01-01T12:00:00Z"
        
        generator = ReleaseBodyGenerator(metadata)
        body = generator.generate_body()
        
        assert "sol-server.service" in body
        assert "sol-connectivity.service" in body
        assert "update_version_info.timer" in body
        assert "filebeat.service" in body
    
    def test_generate_body_contains_config_and_logrotate(self):
        """Test that generated body includes config and logrotate files."""
        metadata = ReleaseMetadata()
        metadata.build_date = "2025-01-01T12:00:00Z"
        
        generator = ReleaseBodyGenerator(metadata)
        body = generator.generate_body()
        
        assert "filebeat.yml" in body
        assert "mp2624-logrotate" in body
        assert "sol-server-logrotate" in body
    
    def test_generate_body_hash(self):
        """Test that body hash is generated correctly."""
        metadata = ReleaseMetadata()
        metadata.build_date = "2025-01-01T12:00:00Z"
        
        generator = ReleaseBodyGenerator(metadata)
        body_hash = generator.get_body_hash()
        
        assert len(body_hash) == 16
        assert all(c in "0123456789abcdef" for c in body_hash)
    
    def test_body_hash_consistency(self):
        """Test that same metadata produces same body hash."""
        metadata = ReleaseMetadata()
        metadata.build_date = "2025-01-01T12:00:00Z"
        
        generator = ReleaseBodyGenerator(metadata)
        hash1 = generator.get_body_hash()
        hash2 = generator.get_body_hash()
        
        assert hash1 == hash2


class TestIntegration:
    """Integration tests for metadata workflow."""
    
    def test_full_metadata_collection_workflow(self):
        """Test complete metadata collection for all components."""
        collector = WorkflowMetadataCollector()
        collector.initialize("repository_dispatch")
        
        # Process all three component releases
        for action, payload_data in [
            ("sol_software_release", {
                "sol_software_branch": "main",
                "sol_software_commit": "abc123",
                "sol_software_tag": "v1.0.0"
            }),
            ("sol_utils_release", {
                "sol_utils_branch": "develop",
                "sol_utils_commit": "def456",
                "sol_utils_tag": "v2.0.0"
            }),
            ("sol_server_release", {
                "sol_server_branch": "release",
                "sol_server_commit": "ghi789",
                "sol_server_tag": "v1.5.0"
            })
        ]:
            collector.parse_dispatch_event(action, payload_data)
        
        collector.finalize_release_version()
        
        summary = collector.get_workflow_summary()
        
        assert len(summary["components"]) == 3
        assert "sol-software" in summary["components"]
        assert "sol-utils" in summary["components"]
        assert "sol-server" in summary["components"]
        assert summary["triggered_by"] == "repository_dispatch"
    
    def test_metadata_with_missing_component(self):
        """Test handling when one component is missing."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        # Only process sol-software and sol-utils
        collector.parse_dispatch_event("sol_software_release", {
            "sol_software_branch": "main",
            "sol_software_commit": "abc123",
            "sol_software_tag": "v1.0.0"
        })
        collector.parse_dispatch_event("sol_utils_release", {
            "sol_utils_branch": "develop",
            "sol_utils_commit": "def456",
            "sol_utils_tag": "v2.0.0"
        })
        
        # Mark sol-server as included without details
        collector.mark_component_included("sol-server")
        
        collector.finalize_release_version()
        
        summary = collector.get_workflow_summary()
        
        # Should have 2 components with details + 1 marked included
        assert len(summary["components"]) == 3
    
    def test_body_generation_for_collected_metadata(self):
        """Test that body generator correctly uses collected metadata."""
        collector = WorkflowMetadataCollector()
        collector.initialize()

        collector.parse_dispatch_event("sol_software_release", {
            "sol_software_branch": "main",
            "sol_software_commit": "abc123def",
            "sol_software_tag": "v1.0.0",
            "pr_number": "42"
        })
        collector.mark_component_included("sol-utils")

        collector.finalize_release_version()

        generator = ReleaseBodyGenerator(collector.metadata)
        body = generator.generate_body()

        assert "v1.0.0" in body
        assert "sol-software" in body
        assert "main" in body
        assert "abc123d" in body  # Commit prefix should be visible
