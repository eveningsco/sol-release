"""
Comprehensive tests for media cleanup and tagging workflow simulation.

Tests cover:
- MediaFileMetadata serialization and operations
- FolderState management and resolution tracking
- MediaCleanupProcessor workflow simulation
- MediaTaggingSimulator operations
- CombinedReleaseSimulator package creation
- Full workflow simulation
"""

import json
import os
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone

import pytest

from media_cleanup import (
    ShotType,
    MediaCategory,
    MediaFileMetadata,
    FolderState,
    CleanupReport,
    MediaCleanupProcessor,
    MediaTaggingSimulator,
    CombinedReleaseSimulator,
    simulate_full_workflow
)


# ============================================================================
# MediaFileMetadata Tests
# ============================================================================

def test_media_file_metadata_serialization():
    """Test that MediaFileMetadata can be serialized and deserialized."""
    metadata = MediaFileMetadata(
        file_path="/media/video1.mp4",
        file_name="video1.mp4",
        file_size_bytes=1048576,
        duration_seconds=120.5,
        shot_type=ShotType.WIDE,
        category=MediaCategory.ACTION,
        description="Test video",
        tags=["tag1", "tag2"],
        notes="Sample notes"
    )
    
    # Serialize
    data = metadata.to_dict()
    
    # Verify fields
    assert data["file_path"] == "/media/video1.mp4"
    assert data["file_name"] == "video1.mp4"
    assert data["file_size_bytes"] == 1048576
    assert data["duration_seconds"] == 120.5
    assert data["shot_type"] == "wide"
    assert data["category"] == "action"
    assert data["description"] == "Test video"
    assert data["tags"] == ["tag1", "tag2"]
    assert data["notes"] == "Sample notes"
    
    # Deserialize
    restored = MediaFileMetadata.from_dict(data)
    assert restored.file_path == metadata.file_path
    assert restored.file_name == metadata.file_name
    assert restored.file_size_bytes == metadata.file_size_bytes
    assert restored.shot_type == metadata.shot_type
    assert restored.category == metadata.category
    assert restored.tags == metadata.tags


def test_media_file_metadata_with_none_values():
    """Test that None values are excluded from serialization."""
    metadata = MediaFileMetadata(
        file_path="/media/video.mp4",
        file_name="video.mp4",
        file_size_bytes=1024
    )
    
    data = metadata.to_dict()
    
    # None values should be excluded
    assert "shot_type" not in data
    assert "category" not in data
    assert "description" not in data
    assert "tags" not in data or data["tags"] == []
    assert "notes" not in data


def test_media_file_metadata_add_tag():
    """Test adding tags to media file metadata."""
    metadata = MediaFileMetadata(
        file_path="/media/video.mp4",
        file_name="video.mp4",
        file_size_bytes=1024
    )
    
    metadata.add_tag("tag1")
    metadata.add_tag("tag2")
    
    assert "tag1" in metadata.tags
    assert "tag2" in metadata.tags
    
    # Adding same tag should not duplicate
    metadata.add_tag("tag1")
    assert metadata.tags.count("tag1") == 1
    assert len(metadata.tags) == 2


def test_media_file_metadata_mark_resolved():
    """Test marking a file as resolved."""
    metadata = MediaFileMetadata(
        file_path="/media/video.mp4",
        file_name="video.mp4",
        file_size_bytes=1024
    )
    
    assert not metadata.resolved
    
    metadata.mark_resolved(notes="Processed successfully")
    
    assert metadata.resolved is True
    assert metadata.notes == "Processed successfully"


def test_media_file_metadata_is_ready_for_release():
    """Test checking if file is ready for release."""
    # Not resolved
    metadata1 = MediaFileMetadata(
        file_path="/media/video.mp4",
        file_name="video.mp4",
        file_size_bytes=1024
    )
    assert not metadata1.is_ready_for_release()
    
    # Resolved but no category
    metadata1.mark_resolved()
    assert not metadata1.is_ready_for_release()
    
    # Resolved with category
    metadata1.category = MediaCategory.ACTION
    assert metadata1.is_ready_for_release()


# ============================================================================
# FolderState Tests
# ============================================================================

def test_folder_state_serialization():
    """Test that FolderState can be serialized and deserialized."""
    folder = FolderState(
        folder_path="/media/videos",
        folder_name="videos",
        total_files=10,
        resolved_files=5,
        total_size_bytes=10485760,
        status="in_progress",
        issues=["Issue 1", "Issue 2"],
        metadata={"key": "value"}
    )
    
    data = folder.to_dict()
    restored = FolderState.from_dict(data)
    
    assert restored.folder_path == folder.folder_path
    assert restored.total_files == folder.total_files
    assert restored.resolved_files == folder.resolved_files
    assert restored.status == folder.status
    assert restored.issues == folder.issues


def test_folder_state_resolution_percentage():
    """Test calculation of resolution percentage."""
    folder = FolderState(
        folder_path="/media",
        folder_name="media",
        total_files=10,
        resolved_files=5
    )
    
    assert folder.resolution_percentage == 50.0
    
    folder.total_files = 0
    assert folder.resolution_percentage == 0.0
    
    folder.total_files = 10
    folder.resolved_files = 10
    assert folder.resolution_percentage == 100.0


def test_folder_state_is_complete():
    """Test checking if folder is complete."""
    # No files
    folder1 = FolderState(folder_path="/media", folder_name="media")
    assert not folder1.is_complete()
    
    # Some files resolved, status not complete
    folder2 = FolderState(
        folder_path="/media",
        folder_name="media",
        total_files=10,
        resolved_files=5,
        status="in_progress"
    )
    assert not folder2.is_complete()
    
    # All files resolved, status complete
    folder3 = FolderState(
        folder_path="/media",
        folder_name="media",
        total_files=10,
        resolved_files=10,
        status="complete"
    )
    assert folder3.is_complete()


def test_folder_state_is_already_done():
    """Test checking if folder has already been processed."""
    # Incomplete resolution
    folder1 = FolderState(
        folder_path="/media",
        folder_name="media",
        total_files=10,
        resolved_files=5,
        status="complete"
    )
    assert not folder1.is_already_done()
    
    # All files resolved
    folder2 = FolderState(
        folder_path="/media",
        folder_name="media",
        total_files=10,
        resolved_files=10,
        status="complete"
    )
    assert folder2.is_already_done()


def test_folder_state_add_issue():
    """Test adding issues to folder state."""
    folder = FolderState(folder_path="/media", folder_name="media")
    
    folder.add_issue("Issue 1")
    folder.add_issue("Issue 2")
    folder.add_issue("Issue 1")  # Should not duplicate
    
    assert len(folder.issues) == 2
    assert "Issue 1" in folder.issues
    assert "Issue 2" in folder.issues


# ============================================================================
# CleanupReport Tests
# ============================================================================

def test_cleanup_report_serialization():
    """Test that CleanupReport can be serialized and deserialized."""
    report = CleanupReport(
        files_analyzed=100,
        files_resolved=80,
        files_rejected=10,
        files_deleted=5,
        folders_processed=5,
        total_size_freed_bytes=1048576,
        issues_found=3,
        success=True
    )
    
    # Test to_dict
    data = report.to_dict()
    assert data["files_analyzed"] == 100
    assert data["files_resolved"] == 80
    
    # Test to_json
    json_str = report.to_json()
    parsed = json.loads(json_str)
    assert parsed["files_analyzed"] == 100
    
    # Test from_dict
    restored = CleanupReport.from_dict(data)
    assert restored.files_analyzed == report.files_analyzed
    assert restored.files_resolved == report.files_resolved


# ============================================================================
# MediaCleanupProcessor Tests
# ============================================================================

def test_media_cleanup_processor_init():
    """Test initialization of MediaCleanupProcessor."""
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = MediaCleanupProcessor(temp_dir)
        
        assert processor.base_path == Path(temp_dir)
        assert processor.temp_folder.exists()
        assert len(processor.files) == 0
        assert len(processor.folders) == 0


def test_media_cleanup_processor_scan_directory():
    """Test scanning a directory for media files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create test files
        test_dir = Path(temp_dir)
        (test_dir / "video1.mp4").touch()
        (test_dir / "image1.jpg").touch()
        (test_dir / "audio1.wav").touch()
        (test_dir / "text.txt").touch()  # Not a media file
        
        processor = MediaCleanupProcessor(temp_dir)
        file_count = processor.scan_directory()
        
        assert file_count == 3
        assert "video1.mp4" in processor.files
        assert "image1.jpg" in processor.files
        assert "audio1.wav" in processor.files
        assert "text.txt" not in processor.files


def test_media_cleanup_processor_analyze_file():
    """Test analyzing a media file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "wide_shot.mp4").touch()
        (test_dir / "dialogue_scene.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        
        # Analyze wide shot
        metadata = processor.analyze_file("wide_shot.mp4")
        assert metadata is not None
        assert metadata.shot_type == ShotType.WIDE
        
        # Analyze dialogue scene
        metadata = processor.analyze_file("dialogue_scene.mp4")
        assert metadata is not None
        assert metadata.category == MediaCategory.DIALOGUE


def test_media_cleanup_processor_resolve_file():
    """Test resolving a media file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        
        # Resolve file
        success = processor.resolve_file(
            "video.mp4",
            category="action",
            shot_type="wide"
        )
        
        assert success is True
        assert processor.files["video.mp4"].resolved is True
        assert processor.files["video.mp4"].category == MediaCategory.ACTION
        assert processor.files["video.mp4"].shot_type == ShotType.WIDE


def test_media_cleanup_processor_resolve_invalid_file():
    """Test resolving a file that doesn't exist."""
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = MediaCleanupProcessor(temp_dir)
        
        success = processor.resolve_file("nonexistent.mp4")
        assert success is False


def test_media_cleanup_processor_reject_file():
    """Test rejecting a media file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        
        success = processor.reject_file("video.mp4", "Corrupted file")
        
        assert success is True
        assert processor.files["video.mp4"].resolved is True
        assert "Rejected" in processor.files["video.mp4"].notes
        assert any("video.mp4" in issue for issue in processor.folders[str(test_dir)].issues)


def test_media_cleanup_processor_generate_report():
    """Test generating a cleanup report."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video1.mp4").touch()
        (test_dir / "video2.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        
        # Resolve one file
        processor.resolve_file("video1.mp4", category="action")
        
        # Reject another
        processor.reject_file("video2.mp4", "Test")
        
        report = processor.generate_report()
        
        assert report.files_analyzed == 2
        assert report.files_resolved == 2
        assert report.folders_processed == 1


def test_media_cleanup_processor_cleanup_temp_files():
    """Test cleaning up temporary files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = MediaCleanupProcessor(temp_dir)
        
        # Create temp files
        temp_file1 = processor.temp_folder / "temp1.txt"
        temp_file2 = processor.temp_folder / "temp2.txt"
        temp_file1.write_text("test")
        temp_file2.write_text("test")
        
        deleted_count = processor.cleanup_temp_files()
        
        assert deleted_count == 2
        assert not temp_file1.exists()
        assert not temp_file2.exists()


def test_media_cleanup_processor_close():
    """Test closing the processor."""
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = MediaCleanupProcessor(temp_dir)
        processor.close()
        
        assert not processor.temp_folder.exists()


# ============================================================================
# MediaTaggingSimulator Tests
# ============================================================================

def test_media_tagging_simulator_init():
    """Test initialization of MediaTaggingSimulator."""
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = MediaCleanupProcessor(temp_dir)
        simulator = MediaTaggingSimulator(processor)
        
        assert simulator.processor == processor
        assert simulator.tag_operations == []


def test_media_tagging_simulator_add_release_tags():
    """Test adding release tags to a file."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        
        simulator = MediaTaggingSimulator(processor)
        
        success = simulator.add_release_tags("video.mp4", "v1.0.0")
        
        assert success is True
        assert "release-v1.0.0" in processor.files["video.mp4"].tags
        assert len(simulator.tag_operations) == 1


def test_media_tagging_simulator_categorize_media():
    """Test categorizing media."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        
        simulator = MediaTaggingSimulator(processor)
        
        success = simulator.categorize_media("video.mp4", "action", "wide")
        
        assert success is True
        assert processor.files["video.mp4"].category == MediaCategory.ACTION
        assert processor.files["video.mp4"].shot_type == ShotType.WIDE


def test_media_tagging_simulator_get_tag_summary():
    """Test getting tag operation summary."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        
        simulator = MediaTaggingSimulator(processor)
        
        simulator.add_release_tags("video.mp4", "v1.0.0")
        simulator.categorize_media("video.mp4", "action", "wide")
        
        summary = simulator.get_tag_summary()
        
        assert summary["total_operations"] == 2
        assert len(summary["operations"]) == 2


# ============================================================================
# CombinedReleaseSimulator Tests
# ============================================================================

def test_combined_release_simulator_init():
    """Test initialization of CombinedReleaseSimulator."""
    with tempfile.TemporaryDirectory() as temp_dir:
        processor = MediaCleanupProcessor(temp_dir)
        simulator = CombinedReleaseSimulator(processor)
        
        assert simulator.processor == processor
        assert simulator.package_path is None


def test_combined_release_simulator_create_release_package():
    """Test creating a release package."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        processor.resolve_file("video.mp4", category="action")
        
        simulator = CombinedReleaseSimulator(processor)
        
        package_path = simulator.create_release_package("v1.0.0")
        
        assert package_path is not None
        assert simulator.package_path == package_path
        assert "metadata.json" in os.listdir(package_path)


def test_combined_release_simulator_get_package_info():
    """Test getting package information."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        processor.scan_directory()
        
        simulator = CombinedReleaseSimulator(processor)
        
        simulator.create_release_package("v1.0.0")
        
        info = simulator.get_package_info()
        
        assert info is not None
        assert info["package_path"] == simulator.package_path
        assert info["exists"] is True


def test_combined_release_simulator_reset():
    """Test resetting the simulator."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video.mp4").touch()
        
        processor = MediaCleanupProcessor(temp_dir)
        
        simulator = CombinedReleaseSimulator(processor)
        
        simulator.reset()
        
        assert simulator.package_path is None
        assert simulator.package_metadata == {}


# ============================================================================
# Full Workflow Simulation Tests
# ============================================================================

def test_simulate_full_workflow():
    """Test complete workflow simulation."""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_dir = Path(temp_dir)
        (test_dir / "video1.mp4").touch()
        (test_dir / "video2.mp4").touch()
        (test_dir / "image1.jpg").touch()
        
        results = simulate_full_workflow(temp_dir, "v1.0.0")
        
        assert results["success"] is True
        assert len(results["steps"]) >= 4
        assert results["workflow_id"] is not None
        
        # Check steps
        steps = {step["step"]: step for step in results["steps"]}
        assert "scan" in steps
        assert "analyze" in steps
        assert "tag" in steps
        assert "package" in steps


def test_simulate_full_workflow_empty_directory():
    """Test workflow with empty directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        results = simulate_full_workflow(temp_dir, "v1.0.0")
        
        assert results["success"] is True
        assert len(results["steps"]) >= 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
