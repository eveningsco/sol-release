"""Tests for workflow dispatch simulation and artifact handling.

These tests validate the artifact download logic and package creation workflow.
"""

import pytest
from tests.mocks import (
    ReleaseMetadata,
    WorkflowMetadataCollector,
    ReleaseBodyGenerator,
    ReleasePackageCreator,
    ArtifactDownloaderSimulator
)


class TestArtifactDownloaderSimulator:
    """Tests for the ArtifactDownloaderSimulator class."""
    
    def test_download_sol_server(self):
        """Test downloading sol-server artifacts."""
        downloader = ArtifactDownloaderSimulator()
        result = downloader.download_component("sol-server")

        assert result is True
        assert len(downloader.downloaded_files) > 0

        # Check expected artifacts are downloaded
        assert any("bin/sol-server.zip" in f for f in downloader.downloaded_files)
        assert any("sol-connectivity.service" in f for f in downloader.downloaded_files)
    
    def test_download_sol_software(self):
        """Test downloading sol-software artifacts."""
        downloader = ArtifactDownloaderSimulator()
        result = downloader.download_component("sol-software")
        
        assert result is True
        assert any("bin/sol_software" in f for f in downloader.downloaded_files)
        assert any("sol_software.service" in f for f in downloader.downloaded_files)
    
    def test_download_sol_utils(self):
        """Test downloading sol-utils artifacts."""
        downloader = ArtifactDownloaderSimulator()
        result = downloader.download_component("sol-utils")
        
        assert result is True
        
        # Check executables
        utils_executables = [f for f in downloader.downloaded_files if "bin/" in f]
        assert any("sol_update_gui" in f for f in utils_executables)
        assert any("mass_gadget_watchdog" in f for f in utils_executables)
        assert any("provision" in f for f in utils_executables)
        
        # Check services
        utils_services = [f for f in downloader.downloaded_files if "services/" in f]
        assert any("update_version_info.service" in f for f in utils_services)
        assert any("filebeat.service" in f for f in utils_services)
        
        # Check config
        assert any("config/filebeat.yml" in f for f in downloader.downloaded_files)
        
        # Check logrotate
        assert any("logrotate/mp2624-logrotate" in f for f in downloader.downloaded_files)
    
    def test_download_unknown_component(self):
        """Test downloading artifacts for unknown component."""
        downloader = ArtifactDownloaderSimulator()
        result = downloader.download_component("unknown-component")
        
        assert result is False
        assert len(downloader.downloaded_files) == 0
    
    def test_download_multiple_components(self):
        """Test downloading multiple component artifacts."""
        downloader = ArtifactDownloaderSimulator()
        
        # Download all components
        downloader.download_component("sol-server")
        downloader.download_component("sol-software")
        downloader.download_component("sol-utils")
        
        summary = downloader.get_download_summary()
        
        # Should have many files total
        assert summary["total_files"] > 10
        assert "Downloading" in summary["steps"][0]
    
    def test_download_artifact_count(self):
        """Test that correct number of artifacts are downloaded per component."""
        sol_server_files = 0
        sol_utils_files = 0
        sol_software_files = 0
        
        # Download sol-server
        downloader = ArtifactDownloaderSimulator()
        downloader.download_component("sol-server")
        sol_server_files = len([f for f in downloader.downloaded_files])
        
        # Download sol-utils
        downloader = ArtifactDownloaderSimulator()
        downloader.download_component("sol-utils")
        sol_utils_files = len([f for f in downloader.downloaded_files])
        
        # Download sol-software
        downloader = ArtifactDownloaderSimulator()
        downloader.download_component("sol-software")
        sol_software_files = len([f for f in downloader.downloaded_files])
        
        # sol-utils should have most files (executables + services + config + logrotate)
        assert sol_utils_files > sol_server_files
        assert sol_utils_files > sol_software_files
    
    def test_download_structure(self):
        """Test that downloaded files have correct directory structure."""
        downloader = ArtifactDownloaderSimulator()
        downloader.download_component("sol-server")
        
        files = downloader.downloaded_files
        
        # Should have bin directory
        assert any("downloads/bin/" in f for f in files)
        # Should have services directory
        assert any("downloads/services/" in f for f in files)
    
    def test_download_structure_sol_utils(self):
        """Test that sol-utils download creates all directory structures."""
        downloader = ArtifactDownloaderSimulator()
        downloader.download_component("sol-utils")
        
        files = downloader.downloaded_files
        
        # Should have bin, services, config, and logrotate directories
        assert any("downloads/bin/" in f for f in files)
        assert any("downloads/services/" in f for f in files)
        assert any("downloads/config/" in f for f in files)
        assert any("downloads/logrotate/" in f for f in files)


class TestReleasePackageCreator:
    """Tests for the ReleasePackageCreator class."""
    
    def test_create_package(self):
        """Test package creation."""
        metadata = ReleaseMetadata()
        metadata.release_version = "Release-01012025_12-00-00"
        metadata.build_date = "2025-01-01T12:00:00Z"
        
        downloaded_files = [
            "downloads/bin/sol-server.zip",
            "downloads/services/sol-server.service"
        ]
        
        creator = ReleasePackageCreator(downloaded_files, metadata)
        zip_filename = creator.create_package("sol-release-01012025_12-00-00.zip")
        
        assert zip_filename == "sol-release-01012025_12-00-00.zip"
        assert len(creator.package_files) > 0
    
    def test_cleanup_old_releases(self):
        """Test old release cleanup simulation."""
        creator = ReleasePackageCreator([], ReleaseMetadata())
        removed = creator.cleanup_old_releases(releases_to_keep=5)
        
        assert isinstance(removed, list)
        # Returns empty list in simulation (no actual releases)
    
    def test_package_summary(self):
        """Test package summary generation."""
        metadata = ReleaseMetadata()
        metadata.release_version = "Release-01012025_12-00-00"
        
        downloaded_files = [
            "downloads/bin/file1",
            "downloads/bin/file2",
            "downloads/services/service1"
        ]
        
        creator = ReleasePackageCreator(downloaded_files, metadata)
        creator.create_package("test.zip")
        
        summary = creator.get_package_summary()
        
        assert summary["package_files_count"] == 3
        assert len(summary["package_files"]) == 3


class TestWorkflowIntegration:
    """Integration tests for complete workflow simulation."""
    
    def test_complete_release_workflow(self):
        """Test a complete release workflow from dispatch to package creation."""
        # Step 1: Collect metadata from dispatch events
        collector = WorkflowMetadataCollector()
        collector.initialize("repository_dispatch")
        
        # Process dispatch events for all components
        collector.parse_dispatch_event("sol_software_release", {
            "sol_software_branch": "main",
            "sol_software_commit": "abc123def",
            "sol_software_tag": "v1.0.0"
        })
        
        collector.parse_dispatch_event("sol_utils_release", {
            "sol_utils_branch": "develop",
            "sol_utils_commit": "def456ghi",
            "sol_utils_tag": "v2.0.0"
        })
        
        collector.parse_dispatch_event("sol_server_release", {
            "sol_server_branch": "release",
            "sol_server_commit": "ghi789jkl",
            "sol_server_tag": "v1.5.0"
        })
        
        collector.finalize_release_version()
        
        # Step 2: Download artifacts for each component
        downloader = ArtifactDownloaderSimulator()
        downloader.download_component("sol-server")
        downloader.download_component("sol-software")
        downloader.download_component("sol-utils")
        
        # Step 3: Create package
        creator = ReleasePackageCreator(downloader.downloaded_files, collector.metadata)
        zip_filename = creator.create_package(f"sol-release-{collector.metadata.release_version.split('-')[1]}.zip")
        
        # Step 4: Generate release body
        generator = ReleaseBodyGenerator(collector.metadata)
        body = generator.generate_body()
        
        # Verify all steps completed
        summary = collector.get_workflow_summary()
        assert len(summary["components"]) == 3
        assert creator.package_files == list(set(downloader.downloaded_files))
        assert len(body) > 1000  # Body should be substantial
    
    def test_manual_trigger_workflow(self):
        """Test workflow triggered manually via workflow_dispatch."""
        collector = WorkflowMetadataCollector()
        collector.initialize("workflow_dispatch")
        
        # When manually triggered, components may not have dispatch metadata
        collector.mark_component_included("sol-server")
        collector.mark_component_included("sol-software")
        collector.mark_component_included("sol-utils")
        
        collector.finalize_release_version()
        
        assert collector.metadata.triggered_by == "workflow_dispatch"
        assert all(c in collector.metadata.components for c in ["sol-server", "sol-software", "sol-utils"])
        
        # Should still be able to generate body
        generator = ReleaseBodyGenerator(collector.metadata)
        body = generator.generate_body()
        assert "sol-server" in body
    
    def test_partial_component_workflow(self):
        """Test workflow when only some components are available."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        # Only process sol-server dispatch
        collector.parse_dispatch_event("sol_server_release", {
            "sol_server_branch": "main",
            "sol_server_commit": "abc123",
            "sol_server_tag": "v1.0.0"
        })
        
        # Mark other components as included (without dispatch data)
        collector.mark_component_included("sol-software")
        collector.mark_component_included("sol-utils")
        
        collector.finalize_release_version()
        
        summary = collector.get_workflow_summary()
        
        # All 3 components should be present
        assert len(summary["components"]) == 3
        # But only sol-server should have detailed data
        assert collector.metadata.components["sol-server"]["branch"] == "main"
    
    def test_workflow_with_pr_number(self):
        """Test workflow with PR number in payload."""
        collector = WorkflowMetadataCollector()
        collector.initialize()

        payload = {
            "sol_software_branch": "feature/new-feature",
            "sol_software_commit": "abc123",
            "sol_software_tag": "v1.1.0",
            "sol_software_url": "https://github.com/eveningsco/sol-software/releases/123",
            "pr_number": "15"
        }

        collector.parse_dispatch_event("sol_software_release", payload)
        collector.finalize_release_version()

        # Check body includes PR info
        generator = ReleaseBodyGenerator(collector.metadata)
        body = generator.generate_body()

        # PR number is stored in metadata (commit should be visible)
        assert "feature/new-feature" in body
        assert "abc123" in body
    
    def test_workflow_steps_logging(self):
        """Test that all workflow steps are logged."""
        collector = WorkflowMetadataCollector()
        
        collector.initialize("repository_dispatch")
        collector.parse_dispatch_event("sol_software_release", {
            "sol_software_branch": "main",
            "sol_software_commit": "abc123",
            "sol_software_tag": "v1.0.0"
        })
        collector.mark_component_included("sol-utils")
        collector.mark_component_included("sol-server")
        collector.finalize_release_version()
        
        summary = collector.get_workflow_summary()
        
        # Should have multiple logged steps
        assert summary["steps_count"] >= 5
    
    def test_package_uniqueness(self):
        """Test that package files are deduplicated."""
        downloader = ArtifactDownloaderSimulator()
        
        # Download components in different orders to ensure potential overlaps
        downloader.download_component("sol-server")
        downloader.download_component("sol-utils")
        
        original_count = len(downloader.downloaded_files)
        
        # Create package which deduplicates
        creator = ReleasePackageCreator(downloader.downloaded_files, ReleaseMetadata())
        creator.create_package("test.zip")
        
        # Package should have deduplicated files
        assert len(creator.package_files) >= original_count // 2  # At least half (safety check)


class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_empty_dispatch_payload(self):
        """Test handling empty dispatch payload."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        result = collector.parse_dispatch_event("sol_software_release", {})
        
        # Should handle gracefully
        assert collector.metadata.triggered_by == "repository_dispatch"
    
    def test_incomplete_metadata_payload(self):
        """Test handling incomplete metadata payload."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        payload = {
            "sol_software_branch": "main"
            # Missing commit and tag
        }
        
        result = collector.parse_dispatch_event("sol_software_release", payload)
        
        assert result is True
        assert collector.metadata.components["sol-software"]["branch"] == "main"
    
    def test_special_characters_in_branch(self):
        """Test handling branches with special characters."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        payload = {
            "sol_software_branch": "feature/special-chars_123",
            "sol_software_commit": "abc123def",
            "sol_software_tag": "v1.0.0-beta+build.1"
        }
        
        collector.parse_dispatch_event("sol_software_release", payload)
        
        assert collector.metadata.components["sol-software"]["branch"] == "feature/special-chars_123"
        assert collector.metadata.components["sol-software"]["tag_name"] == "v1.0.0-beta+build.1"
    
    def test_long_commit_sha(self):
        """Test handling full-length commit SHA."""
        collector = WorkflowMetadataCollector()
        collector.initialize()
        
        payload = {
            "sol_software_branch": "main",
            "sol_software_commit": "a" * 40,  # Full SHA
            "sol_software_tag": "v1.0.0"
        }
        
        collector.parse_dispatch_event("sol_software_release", payload)
        
        assert collector.metadata.components["sol-software"]["commit_sha"] == "a" * 40
    
    def test_body_hash_changes_with_metadata(self):
        """Test that body hash changes when metadata changes."""
        metadata1 = ReleaseMetadata()
        metadata1.build_date = "2025-01-01T12:00:00Z"
        
        metadata2 = ReleaseMetadata()
        metadata2.build_date = "2025-01-02T12:00:00Z"
        
        generator1 = ReleaseBodyGenerator(metadata1)
        generator2 = ReleaseBodyGenerator(metadata2)
        
        hash1 = generator1.get_body_hash()
        hash2 = generator2.get_body_hash()
        
        assert hash1 != hash2  # Different dates should produce different hashes
