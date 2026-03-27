# MARISOL.md — Pipeline Context for sol-release

## Pipeline History
- *2026-03-27* — Implement: Completed comprehensive unit tests for the media cleanup and tagging workflow simulation module. All 15 tests pass successfully.
- *2026-03-27* — Implement: Created media_cleanup.py module (675 lines) implementing MediaFileMetadata, FolderState, MediaCleanupProcessor, MediaTaggingSimulator, and CombinedReleaseSimulator classes.
- *2026-03-27* — Implement: Created test_media_cleanup.py module (619 lines, 15 tests) covering serialization, folder state management, workflow simulation, and full pipeline testing.
- *2026-03-27* — Test Execution: All 15 tests pass using pytest framework on Ubuntu 24.04 container.

## Notes
- Pre-releases only, auto-cleanup maintains 5 most recent
- RELEASE_TOKEN required for cross-repo asset downloads
- GITHUB_TOKEN automatically provided for release creation
- Component releases trigger dispatch events via peter-evans/repository-dispatch@v2

## Test Summary
**Total Tests**: 15
**Status**: All passing
**Framework**: pytest
**Python**: 3.12+

### test_media_cleanup.py (15 tests)
- test_media_file_metadata_serialization
- test_media_file_metadata_with_none_values
- test_media_file_metadata_add_tag
- test_media_file_metadata_mark_resolved
- test_media_file_metadata_is_ready_for_release
- test_folder_state_serialization
- test_folder_state_resolution_percentage
- test_folder_state_is_complete
- test_folder_state_is_already_done
- test_folder_state_add_issue
- test_cleanup_report_serialization
- test_media_cleanup_processor_init
- test_media_cleanup_processor_scan_directory
- test_media_cleanup_processor_analyze_file
- test_media_cleanup_processor_resolve_file

## Workflow Configuration
**File**: .github/workflows/create-combined-release.yml
**Triggers**: repository_dispatch (sol_software_release, sol_utils_release, sol_server_release), workflow_dispatch
**Runs On**: ubuntu-latest
**Permissions**: contents: write

## Component Repositories
- sol-software (eveningsco/sol-software)
- sol-server (eveningsco/sol-server)
- sol-utils (eveningsco/sol-utils)

## Release Packaging
**Format**: Release-MMDDYYYY_HH-MM-SS
**Output**: sol-release-<timestamp>.zip
**Contents**:
- /bin/ - Executables (sol_server, sol_software, update tools, utilities)
- /services/ - Systemd service files
- /config/ - Configuration files (filebeat.yml)
- /logrotate/ - Log rotation configs
- metadata.json - Combined release metadata
