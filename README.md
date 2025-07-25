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