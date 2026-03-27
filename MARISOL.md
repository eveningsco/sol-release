# MARISOL.md — Pipeline Context for sol-release

## Pipeline History
- *2026-03-27* — Implement: Completed comprehensive unit tests for the eveningsco/sol-release GitHub Actions workflow orchestration and metadata generation logic. All 24 tests pass successfully.
- *2026-03-27* — Implement: Created test_workflow_simulation.py module (884 lines, 13 tests) simulating repository dispatch events, workflow step execution, artifact downloads, and combined release package creation.
- *2026-03-27* — Implement: Created test_metadata_generation.py module (584 lines, 11 tests) implementing ComponentMetadata, CombinedMetadata, MetadataMerger, and MetadataBuilder classes for handling component metadata serialization and merging.
- *2026-03-27* — Test Execution: All 24 tests pass using pytest framework on Ubuntu 24.04 container.
- *2026-03-27* — Architecture: Created architecture.svg visualization depicting SOL Release orchestration workflow from component repositories through GitHub Actions to hardware deployment.

## Test Summary
**Total Tests**: 24
**Status**: All passing
**Framework**: pytest 7.4.4
**Python**: 3.12.3

### test_metadata_generation.py (11 tests)
- test_metadata_builder_fluent_interface
- test_component_metadata_serialization
- test_combined_metadata_json_roundtrip
- test_metadata_merger_with_missing_files
- test_metadata_merger_with_partial_files
- test_component_metadata_with_none_values
- test_invalid_component_rejected
- test_release_version_format
- test_component_with_pr_commits
- test_combined_metadata_empty_components
- test_metadata_builder_chaining

### test_workflow_simulation.py (13 tests)
- test_workflow_simulation
- test_workflow_event_simulator_create_dispatch_event
- test_workflow_event_simulator_event_types
- test_repository_dispatch_event_serialization
- test_workflow_run_step_management
- test_workflow_run_complete_step
- test_workflow_step_simulator_directory_structure
- test_workflow_step_simulator_metadata_capture
- test_combined_release_simulator_reset
- test_dispatch_event_without_optional_fields
- test_workflow_run_to_dict
- test_simulate_download_artifact_with_chmod
- test_create_metadata_file_with_components

## Workflow Configuration
**File**: .github/workflows/create-combined-release.yml
**Triggers**: repository_dispatch (sol_software_release, sol_server_release, sol_utils_release), workflow_dispatch
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

## Notes
- Pre-releases only, auto-cleanup maintains 5 most recent
- RELEASE_TOKEN required for cross-repo asset downloads
- GITHUB_TOKEN automatically provided for release creation
- Component releases trigger dispatch events via peter-evans/repository-dispatch@v2
