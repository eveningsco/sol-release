# SOL Release Orchestration

This repository manages the automated release process for the SOL audio recording device ecosystem. It aggregates build artifacts from multiple component repositories into unified release packages for device deployment.

## Overview

The SOL Release repository serves as the central hub for creating combined releases that include:
- **sol-software**: Core device application and UI
- **sol-server**: Web server and API
- **sol-utils**: System utilities and management tools

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  sol-software   │     │   sol-server    │     │   sol-utils     │
│   Repository    │     │   Repository    │     │   Repository    │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                         │
         │ Repository           │ Repository              │ Repository
         │ Dispatch             │ Dispatch                │ Dispatch
         │                       │                         │
         └───────────────────────┴─────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   sol-release          │
                    │   GitHub Actions       │
                    │   Workflow             │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Download Latest       │
                    │  Releases from Each    │
                    │  Component             │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Aggregate Artifacts   │
                    │  Create metadata.json  │
                    │  Package into ZIP      │
                    └────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │  Create GitHub         │
                    │  Pre-Release with      │
                    │  Combined Package      │
                    └────────────────────────┘
```

## Release Process

### Automatic Triggering

When any component repository creates a new release, it automatically triggers the combined release workflow via repository dispatch:

```yaml
# Example from component repository
- name: Trigger combined release
  uses: peter-evans/repository-dispatch@v2
  with:
    token: ${{ secrets.RELEASE_TOKEN }}
    repository: eveningsco/sol-release
    event-type: sol_software_release
    client-payload: '{"branch": "${{ github.ref_name }}", "commit_sha": "${{ github.sha }}", "tag_name": "${{ steps.create_release.outputs.tag }}"}'
```

### Manual Triggering

The workflow can also be triggered manually through the GitHub Actions UI:
1. Navigate to the Actions tab
2. Select "Create Combined Release"
3. Click "Run workflow"

## Release Package Contents

Each combined release includes:

### Executables (`/bin/`)
- `sol-server.zip` - Bun compiled server application
- `sol_software` - Main device application
- `sol_update_gui` - Graphical update interface
- `sol_update_backend` - Update backend service
- `sol_update_manager` - Automatic update checker
- `sol_update_manager_gui` - Update manager GUI
- `mass_gadget_watchdog` - USB gadget monitor
- `update_version_info` - Version information updater
- `gpio_shutdown_trigger` - GPIO shutdown handler
- `off_mass_gadget` / `on_mass_gadget` - USB mass storage toggles
- `expand_exfat` - Partition expander
- `provision` - System provisioning script
- `mp2624` - Battery charger utility

### System Services (`/services/`)
- Core services: `sol-server.service`, `sol_software.service`
- Monitoring: `sol-connectivity.service`, `mass_gadget_watchdog.service`
- Updates: `sol_update_manager.service`, `update_version_info.service`
- Hardware: `fbcp.service`, `mp2624_watchdog.service`
- Logging: `filebeat.service`

### Configuration (`/config/`)
- `filebeat.yml` - Log shipping configuration

### Log Rotation (`/logrotate/`)
- Individual logrotate configs for each service

### Metadata
- `metadata.json` - Combined release information including:
  - Release version and build date
  - Component versions and commit SHAs
  - Branch and PR information
  - Build timestamps

## Setup Requirements

### GitHub Secrets

The following secrets must be configured:
- `RELEASE_TOKEN`: Personal access token with repo access to component repositories
- `GITHUB_TOKEN`: Automatically provided by GitHub Actions

### Permissions

The workflow requires:
- Write access to create releases
- Read access to component repositories
- API access for downloading release assets

## Development

### Testing Releases

1. **Fork Testing**: Fork the repository and update component repository URLs
2. **Local Testing**: Use `act` tool to test GitHub Actions locally
3. **Manual Trigger**: Use workflow_dispatch for testing

### Adding New Components

1. Update workflow triggers:
   ```yaml
   on:
     repository_dispatch:
       types: [...existing..., new_component_release]
   ```

2. Add download step following existing pattern
3. Update metadata merging logic
4. Add files to release body generation

### Debugging

Common issues and solutions:
- **Missing assets**: Check component release includes all required files
- **Permission errors**: Verify RELEASE_TOKEN has appropriate access
- **Workflow not triggering**: Ensure repository dispatch event types match
- **Download failures**: Check asset IDs in workflow logs

## Testing

### Unit Tests

This repository includes comprehensive unit tests that simulate the GitHub Actions workflow:

```bash
# Run all tests
pytest tests/ -v

# Run specific test module
pytest tests/test_workflow_simulation.py -v
pytest tests/test_metadata_generation.py -v
```

### Test Coverage

- **test_workflow_simulation.py**: Simulates repository dispatch events, workflow orchestration, artifact downloads, and release packaging (13 tests, 884 lines)
- **test_metadata_generation.py**: Implements metadata classes, merging logic, and serialization tests (11 tests, 584 lines)

All tests pass on Ubuntu 24.04 with Python 3.12.3 and pytest 7.4.4. See [MARISOL.md](MARISOL.md) for detailed pipeline history and test results.

### Testing Workflow Simulation

The workflow simulator provides:
- `WorkflowEventSimulator`: Creates repository dispatch events
- `WorkflowStepSimulator`: Simulates individual workflow steps
- `CombinedReleaseSimulator`: Orchestrates complete release workflow
- `RepositoryDispatchEvent`: Event structure with client payload
- `WorkflowRun`: Tracks workflow execution state
- `WorkflowStep`: Represents individual workflow steps

### Metadata Generation Testing

The metadata module provides:
- `ComponentMetadata`: Individual component release information
- `CombinedMetadata`: Aggregated metadata for combined releases
- `MetadataMerger`: Merges component metadata files
- `MetadataBuilder`: Fluent interface for constructing metadata

## Hardware Layer

The SOL devices deploy these combined releases and include:

### Components
- Raspberry Pi CM4 - Core computing platform
- HiFiBerry DAC+ ADC - Audio interface
- Adafruit miniTFT (320x240) - Display
- Custom PCB with MP2624 - Battery charging IC
- MCP3021 ADC - Battery voltage monitoring
- PiSugar Power Management - Power distribution
- GPIO Buttons & LEDs - User interface
- USB-C Connectivity - Charging and data
- SD Card Storage - System and application storage

### Update Process
- `sol_update_manager` checks for new releases
- `sol_update_manager_gui` provides user interface
- Device downloads and installs combined release
- Service management via systemd

## Contributing

When modifying the release process:
1. Test changes thoroughly in a fork
2. Ensure backward compatibility
3. Update documentation
4. Consider impact on deployed devices

### Test Updates

When updating workflow or metadata logic:
1. Update simulation tests in `tests/test_workflow_simulation.py`
2. Update metadata tests in `tests/test_metadata_generation.py`
3. Ensure all 24 tests continue to pass
4. Document changes in MARISOL.md

## Documentation Files

- **README.md**: User-facing documentation (this file)
- **MARISOL.md**: Pipeline context, test results, and build history
- **architecture.svg**: Visual architecture diagram
- **tests/test_workflow_simulation.py**: Workflow orchestration simulation tests
- **tests/test_metadata_generation.py**: Metadata generation and handling tests

## Release Naming

- Format: `Release-MMDDYYYY_HH-MM-SS`
- Example: `Release-01252025_14-30-45`
- All releases are created as pre-releases
- Automatic cleanup maintains only the 5 most recent releases

## Update Flow

1. Component repositories build and test their artifacts
2. On successful build, they create a GitHub release
3. Release creation triggers repository dispatch to sol-release
4. sol-release workflow downloads all latest component releases
5. Artifacts are organized and packaged into a single ZIP
6. Combined release is created with comprehensive metadata
7. SOL devices check for and download these combined releases

## Contributing

When modifying the release process:
1. Test changes thoroughly in a fork
2. Ensure backward compatibility
3. Update documentation
4. Consider impact on deployed devices

## License

This project is part of the SOL audio recording device ecosystem.