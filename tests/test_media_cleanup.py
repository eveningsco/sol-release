"""Tests for media cleanup and tagging workflow simulation.

These tests validate the folder state detection, tagging logic,
and sidecar generation workflow for media cleanup operations.
"""

import pytest
from tests.media_cleanup import (
    MediaFileMetadata,
    FolderState,
    MediaCleanupProcessor,
    TaggingValidator
)


class TestMediaFileMetadata:
    """Tests for the MediaFileMetadata class."""

    def test_initialization(self):
        """Test that metadata initializes with empty values."""
        metadata = MediaFileMetadata("/SharedPhotos/test.jpg")

        assert metadata.file_path == "/SharedPhotos/test.jpg"
        assert metadata.folder == ""
        assert metadata.file_name == ""
        assert metadata.shot_type == ""
        assert metadata.category == ""
        assert metadata.description == ""
        assert metadata.rotation_fixed is False
        assert metadata.date_fixed is False
        assert metadata.tagged is False
        assert metadata.sidecar_created is False

    def test_to_dict_returns_correct_structure(self):
        """Test that to_dict returns properly structured dictionary."""
        metadata = MediaFileMetadata("/test/photo.jpg")
        metadata.folder = "Test Folder"
        metadata.file_name = "photo.jpg"
        metadata.shot_type = "wide"
        metadata.category = "landscape"
        metadata.tagged = True
        metadata.rotation_fixed = True

        result = metadata.to_dict()

        assert result["folder"] == "Test Folder"
        assert result["shot_type"] == "wide"
        assert result["category"] == "landscape"
        assert result["tagged"] is True
        assert result["rotation_fixed"] is True

    def test_to_json_serializes_correctly(self):
        """Test that to_json produces valid JSON."""
        import json
        metadata = MediaFileMetadata("/test/photo.jpg")
        metadata.tagged = True

        json_str = metadata.to_json()
        parsed = json.loads(json_str)

        assert parsed["file_path"] == "/test/photo.jpg"
        assert parsed["tagged"] is True

    def test_from_json_deserializes_correctly(self):
        """Test that from_dict correctly parses metadata."""
        data = {
            "file_path": "/test/photo.jpg",
            "folder": "Test",
            "file_name": "photo.jpg",
            "shot_type": "portrait",
            "category": "people",
            "description": "Test description",
            "rotation_fixed": True,
            "date_fixed": False,
            "tagged": True,
            "sidecar_created": True
        }

        metadata = MediaFileMetadata.from_dict(data)

        assert metadata.file_path == "/test/photo.jpg"
        assert metadata.shot_type == "portrait"
        assert metadata.category == "people"
        assert metadata.description == "Test description"
        assert metadata.rotation_fixed is True
        assert metadata.date_fixed is False


class TestFolderState:
    """Tests for the FolderState class."""

    def test_initialization(self):
        """Test folder state initialization."""
        folder = FolderState("Oaxaca 2026", "/SharedPhotos/Albums/Oaxaca 2026")

        assert folder.folder_name == "Oaxaca 2026"
        assert folder.folder_path == "/SharedPhotos/Albums/Oaxaca 2026"
        assert folder.total_files == 0
        assert folder.tagged_count == 0
        assert folder.skipped_count == 0
        assert folder.fixed_rotations == 0
        assert folder.fixed_dates == 0
        assert folder.already_done is False
        assert len(folder.files) == 0

    def test_needs_processing_true(self):
        """Test that folder needs processing when not done."""
        folder = FolderState("Test Folder", "/path/to/test")
        folder.total_files = 10
        folder.tagged_count = 0
        folder.already_done = False

        assert folder.needs_processing is True

    def test_needs_processing_false_when_done_and_tagged(self):
        """Test that folder doesn't need processing when done and tagged."""
        folder = FolderState("Test Folder", "/path/to/test")
        folder.total_files = 10
        folder.tagged_count = 10
        folder.already_done = True

        assert folder.needs_processing is False

    def test_needs_processing_true_when_done_but_zero_tagged(self):
        """Test folder with already_done=True but 0 tagged files needs processing."""
        folder = FolderState("Problem Folder", "/path/to/problem")
        folder.total_files = 29
        folder.tagged_count = 0
        folder.already_done = True  # Bug: folder marked done but nothing tagged

        assert folder.needs_processing is True

    def test_to_dict_serialization(self):
        """Test folder state to_dict serialization."""
        folder = FolderState("Oaxaca 2026", "/SharedPhotos/Albums/Oaxaca 2026")
        folder.total_files = 116
        folder.tagged_count = 0
        folder.skipped_count = 116
        folder.fixed_rotations = 0
        folder.fixed_dates = 0
        folder.already_done = False

        result = folder.to_dict()

        assert result["folder"] == "Oaxaca 2026"
        assert result["total"] == 116
        assert result["tagged"] == 0
        assert result["skipped"] == 116
        assert result["folder_path"] == "/SharedPhotos/Albums/Oaxaca 2026"

    def test_from_dict_deserialization(self):
        """Test folder state from_dict deserialization."""
        data = {
            "folder": "Test Folder",
            "folder_path": "/path/to/test",
            "total": 50,
            "tagged": 25,
            "skipped": 25,
            "fixed_rotations": 5,
            "fixed_dates": 3
        }

        folder = FolderState.from_dict(data)

        assert folder.folder_name == "Test Folder"
        assert folder.total_files == 50
        assert folder.tagged_count == 25
        assert folder.skipped_count == 25


class TestMediaCleanupProcessor:
    """Tests for the MediaCleanupProcessor class."""

    def test_initialization(self):
        """Test processor initialization."""
        processor = MediaCleanupProcessor()

        assert processor.base_path == "/SharedPhotos/Albums"
        assert len(processor.processed_folders) == 0
        assert len(processor.workflow_steps) == 0

    def test_analyze_folder(self):
        """Test folder analysis."""
        processor = MediaCleanupProcessor()
        folder = processor.analyze_folder("Oaxaca 2026")

        assert folder.folder_name == "Oaxaca 2026"
        assert folder.total_files == 116
        assert folder.tagged_count == 0
        assert folder.already_done is False
        assert "Analyzing folder: Oaxaca 2026" in processor.workflow_steps

    def test_tag_folder(self):
        """Test folder tagging."""
        processor = MediaCleanupProcessor()
        folder = FolderState("Test Folder", "/path/to/test")
        folder.total_files = 29

        result = processor.tag_folder(folder)

        assert result["tagged"] == 29
        assert result["skipped"] == 0
        assert result["errors"] == 0
        assert folder.tagged_count == 29
        assert folder.already_done is True

    def test_process_folder_full_workflow(self):
        """Test complete folder processing workflow."""
        processor = MediaCleanupProcessor()
        result = processor.process_folder("Oaxaca 2026")

        assert result["folder"]["folder_name"] == "Oaxaca 2026"
        assert result["result"]["tagged"] == 116
        assert len(processor.processed_folders) == 1

    def test_process_folder_already_done_with_zero_tagged(self):
        """Test processing folder marked done but with 0 tagged (bug scenario)."""
        processor = MediaCleanupProcessor()
        
        # Manually create folder with bug state
        folder = FolderState("Oaxaca 2026", "/SharedPhotos/Albums/Oaxaca 2026")
        folder.total_files = 116
        folder.tagged_count = 0
        folder.already_done = True  # Bug: marked done but nothing tagged

        # Simulate the warning by checking the validation
        validator = TaggingValidator()
        validation = validator.validate_folder_state(folder)

        # Should detect the bug
        assert validation["valid"] is False
        assert any("already done" in error.lower() for error in validation["errors"])
        assert any("tagged" in error.lower() for error in validation["errors"])

    def test_get_processing_summary(self):
        """Test processing summary generation."""
        processor = MediaCleanupProcessor()

        # Process multiple folders
        processor.process_folder("Oaxaca 2026")
        processor.process_folder("Summer Trip 2025")

        summary = processor.get_processing_summary()

        assert summary["folders_processed"] == 2
        assert summary["total_files"] == 232
        assert summary["tagged"] == 232
        assert summary["skipped"] == 0


class TestTaggingValidator:
    """Tests for the TaggingValidator class."""

    def test_validate_folder_state_normal(self):
        """Test validation of normally processed folder."""
        validator = TaggingValidator()
        folder = FolderState("Normal Folder", "/path/normal")
        folder.total_files = 50
        folder.tagged_count = 50
        folder.already_done = True
        folder.sidecar_created = True

        result = validator.validate_folder_state(folder)

        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_folder_state_bug_detected(self):
        """Test validation detects the 'already done' bug."""
        validator = TaggingValidator()
        folder = FolderState("Oaxaca 2026", "/SharedPhotos/Albums/Oaxaca 2026")
        folder.total_files = 116
        folder.tagged_count = 0
        folder.already_done = True  # Bug: folder marked done but nothing tagged

        result = validator.validate_folder_state(folder)

        assert result["valid"] is False
        assert any("already done" in error.lower() for error in result["errors"])
        assert any("sidecar completeness" in error.lower() for error in result["errors"])

    def test_validate_folder_state_no_files(self):
        """Test validation with empty folder."""
        validator = TaggingValidator()
        folder = FolderState("Empty Folder", "/path/empty")
        folder.total_files = 0

        result = validator.validate_folder_state(folder)

        assert result["valid"] is True
        assert any("no files" in warning.lower() for warning in result["warnings"])

    def test_validate_sidecar_complete(self):
        """Test sidecar completeness validation."""
        validator = TaggingValidator()
        folder = FolderState("Complete Folder", "/path/complete")
        folder.total_files = 100
        folder.tagged_count = 100
        folder.sidecar_created = True
        folder.fixed_rotations = 5
        folder.fixed_dates = 3

        result = validator.validate_sidecar_complete(folder)

        assert result["valid"] is True
        assert result["sidecars_complete"] is True

    def test_validate_sidecar_incomplete(self):
        """Test detection of incomplete sidecars."""
        validator = TaggingValidator()
        folder = FolderState("Incomplete Folder", "/path/incomplete")
        folder.total_files = 50
        folder.tagged_count = 50
        folder.sidecar_created = False

        result = validator.validate_sidecar_complete(folder)

        assert result["valid"] is False
        assert any("sidecars missing" in error.lower() for error in result["errors"])

    def test_qa_validation_reprocessing_required(self):
        """Test that bug triggers QA reprocessing requirement."""
        validator = TaggingValidator()
        folder = FolderState("Oaxaca 2026", "/SharedPhotos/Albums/Oaxaca 2026")
        folder.total_files = 116
        folder.tagged_count = 0
        folder.skipped_count = 116
        folder.already_done = True

        result = validator.validate_folder_state(folder)

        assert result["valid"] is False
        assert any("re-run tagging pipeline" in warning.lower() for warning in result["warnings"])


class TestIntegration:
    """Integration tests for the complete media cleanup workflow."""

    def test_full_tagging_workflow(self):
        """Test complete tagging workflow from analysis to validation."""
        processor = MediaCleanupProcessor()
        validator = TaggingValidator()

        # Step 1: Analyze folder
        folder = processor.analyze_folder("Oaxaca 2026")

        # Step 2: Validate initial state
        validation = validator.validate_folder_state(folder)

        # Step 3: Process the folder
        result = processor.process_folder("Oaxaca 2026")

        # Get the actual folder from processor
        processed_folder = processor.processed_folders[-1]

        # Step 4: Validate final state
        final_validation = validator.validate_folder_state(processed_folder)

        # Verify workflow completed successfully
        assert validation["valid"] is True  # Initial state is valid
        assert final_validation["valid"] is True  # After processing, still valid
        assert processed_folder.tagged_count == 116
        assert processed_folder.already_done is True

    def test_bug_scenario_full_workflow(self):
        """Test the bug scenario where folder marked done but 0 tagged."""
        processor = MediaCleanupProcessor()
        validator = TaggingValidator()

        # Simulate bug: folder marked done but no files tagged
        folder = FolderState("Oaxaca 2026", "/SharedPhotos/Albums/Oaxaca 2026")
        folder.total_files = 116
        folder.tagged_count = 0
        folder.skipped_count = 116
        folder.already_done = True

        # Validation should detect the bug
        validation = validator.validate_folder_state(folder)

        assert validation["valid"] is False
        assert len(validation["errors"]) > 0

        # Now process the folder (should re-process all files)
        folder = processor.analyze_folder("Oaxaca 2026")
        processor.tag_folder(folder)

        # After processing, folder should be valid
        final_validation = validator.validate_folder_state(folder)
        assert final_validation["valid"] is True
        assert folder.tagged_count == 116

    def test_qa_requirement_enforcement(self):
        """Test that QA requirements enforce sidecar completeness."""
        validator = TaggingValidator()

        folder = FolderState("Test Folder", "/path/test")
        folder.total_files = 29
        folder.tagged_count = 29
        folder.already_done = True
        folder.sidecar_created = False

        # Sidecar completeness should be flagged
        sidecar_result = validator.validate_sidecar_complete(folder)
        assert sidecar_result["valid"] is False

        # Tagging should also be flagged as incomplete (sidecar not created)
        folder_result = validator.validate_folder_state(folder)
        # Should detect that sidecars are not created for tagged files
        assert folder_result["valid"] is False
        assert any("sidecars not created" in error.lower() for error in folder_result["errors"])


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
