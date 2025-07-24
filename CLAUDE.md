# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

SOL is a hardware/software project for an audio recording device based on Raspberry Pi CM4. The codebase consists of:
- Python software for device operation (`/sol-software/`)
- Bun/Node.js web server (`/sol-server/`)
- System utilities and provisioning scripts (`/sol-utils/`)
- KiCad PCB design files (`/sol-pcb/`)
- Release orchestration (`/sol-release/`)

## Common Commands

### SOL Software (Python)
```bash
# Install dependencies
pip install -r sol-software/requirements.txt

# Run tests
cd sol-software
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov

# Run a single test
python -m pytest tests/test_sol.py::TestSOLClass::test_initial_state -v

# Install on device
cd sol-software
sudo bash INSTALL.sh

# Build executable
pyinstaller SOL.spec

# Check linting (if configured)
python -m flake8 . --exclude=build,dist
```

### SOL Server (Bun/Node.js)
```bash
# Install dependencies
cd sol-server
bun install

# Development (with hot reload)
bun dev

# Production
bun start

# Build
bun build

# Compile for Raspberry Pi
bun compile:pi
bun compile:ap:pi

# Run tests
bun test

# Check for outdated packages
bun outdated
```

### SOL Utils
```bash
# Install dependencies
cd sol-utils
pip install -r requirements.txt

# Run provisioning
cd sol-utils
sudo bash provision.sh

# Run tests
python -m pytest tests/

# Build executables
pyinstaller sol_update_gui.spec
pyinstaller sol_update_backend.spec
pyinstaller sol_update_manager.spec
pyinstaller sol_update_manager_gui.spec
pyinstaller mass_gadget_watchdog.spec
pyinstaller update_version_info.spec
pyinstaller gpio_shutdown_trigger.spec
```

### SOL Release
```bash
# Combined release workflow is triggered automatically via repository dispatch
# or manually through GitHub Actions UI
```

## Architecture

### SOL Software
- `SOL.py` - Main application handling audio recording and device control
  - Manages recording state machine (idle, recording, streaming)
  - Handles hardware button inputs and LED indicators
  - Integrates with WiFi management for connectivity
- `SOLUI.py` - UI application for the device display
  - Shows battery status, recording state, and system info
  - Uses tkinter with Pillow for graphics rendering
- `mcp3021.py` - ADC interface for battery monitoring (I2C address 0x48)
  - Reads battery voltage through voltage divider
  - Calculates battery percentage based on LiPo voltage ranges
- `mp2624.py` - Battery charger interface (I2C address 0x4B)
  - Manages input current limits
  - Controls watchdog timer for safety
- Hardware interfaces via RPi.GPIO, smbus2 for I2C communication
- Audio handling with pyaudio (HiFiBerry DAC+ ADC)
- Display management with Pillow and tkinter (Adafruit miniTFT)

### SOL Server
- MVC architecture with:
  - `/src/controllers/` - Request handlers
  - `/src/routes/` - Route definitions
  - `/src/services/` - Business logic
  - `/src/middlewares/` - Express-style middleware
  - `/views/` - EJS templates
  - `/public/` - Static assets
- Environment-based configuration via `.env` files
- Device configuration in `.device.json`
- Real-time updates via WebSockets
- Recording management and file serving
- WiFi auto-connect with secure password storage
  - AES-256-GCM encryption with device-specific keys
  - Automatic reconnection to known networks on startup
  - Password management through web UI and API
  - Stored in `config/known-connections.json`

### SOL Utils
Key executables and their purposes:
- `sol_update_gui` - Graphical interface for system updates
- `sol_update_backend` - Backend service handling update downloads and installations
- `sol_update_manager` - Service that periodically checks for updates
- `sol_update_manager_gui` - GUI for managing update settings
- `mass_gadget_watchdog` - Monitors USB mass storage gadget functionality
- `update_version_info` - Updates version information files
- `gpio_shutdown_trigger` - Handles GPIO-based shutdown requests
- `off_mass_gadget` / `on_mass_gadget` - Toggle USB mass storage mode
- `expand_exfat` - Expands ExFAT partition on first boot

### Key Services
System services managed by systemd:
- `sol-server.service` - Main web server
- `sol-connectivity.service` - Network connectivity monitoring
- `sol-software.service` - Main device software
- `sol-ui.service` - Device UI service
- `sol_update_manager.service` - Automatic update checking
- `update_version_info.service` & `.timer` - Periodic version updates
- `mass_gadget_watchdog.service` - USB gadget monitoring
- `mp2624_watchdog.service` - Battery charger safety monitoring
- `fbcp.service` - Display framebuffer copy service

### Hardware Components
- Raspberry Pi CM4
- HiFiBerry DAC+ ADC (uses custom DTS overlay)
- Adafruit miniTFT display (320x240, fbcp-ili9341 driver)
- Custom PCB with battery management (MP2624), ADC (MCP3021)
- PiSugar power management
- GPIO pins for buttons (PIN_BTN_0: 27) and LEDs
- PCB design files in `/sol-pcb/`:
  - KiCad project files
  - Gerber files for manufacturing
  - 3D enclosure models (STL/3MF)
  - STEP files for mechanical integration

### CI/CD Pipeline
The project uses GitHub Actions for automated builds:
- **Individual Component Builds**: Each repository has its own workflow
- **Combined Releases**: sol-release orchestrates multi-component builds
- **Repository Dispatch**: Automated triggering between repositories
- **ARM Runner**: Native compilation for Raspberry Pi
- **Build Process**:
  - Uses `uv` for fast Python package management
  - Runs tests with coverage before building
  - Creates GitHub releases with built artifacts
  - Automatically cleans up old releases (keeps newest 5)
- **Release Artifacts**:
  - Executables built with PyInstaller
  - Compiled Bun server applications
  - Service files and configurations
  - Installation scripts

### USB Gadget Functionality
- **Mass Storage Mode**: Exposes recording storage as USB drive
- **Ethernet Gadget**: Network access over USB
- **Toggle Mechanism**: Scripts to switch between modes
- **Watchdog Service**: Ensures gadget reliability
- **Auto-mount**: Handled by systemd mount units

## Environment Configuration

### SOL Server
Create `.env` file:
```
DEVICE_CONFIG_PATH=.device.json
DISPLAY_PROGRAM=../sol-software/SOL.py
NODE_ENV=development
API_URL=https://api.evenings.co
DEVICE_RECORDING_PATH=/mnt/SOL/Recordings
PORT=3000
```

### SOL Software
Uses `.device` file with environment variables:
```
LOG_PATH=/home/pi/.config/sol/logs
RTMP_SERVER=rtmp://your-server/live
DEVICE_ID=your-device-id
OFFLINE_RECORDING=1
```

## Testing

The project includes comprehensive test suites with hardware mocking:
- Mock classes for GPIO, PyAudio, smbus2, and other hardware interfaces
- Test fixtures for creating isolated test environments
- Categories: basic functionality, audio, recording, WiFi management
- Run with coverage to ensure code quality

## Version Management

Versions are automatically generated in `SOL.spec`:
- Format: `major.minor.patch-YYYYMMDD.HHMMSS`
- Version info embedded in built executables
- Accessible via `--version` flag

## Logging

- Centralized logging in `/home/pi/.config/sol/logs/`
- Filebeat integration for log shipping
- Structured logging with timestamps and levels
- Separate logs for each service component
- Logrotate configurations for:
  - `mp2624-logrotate`
  - `sol-server-logrotate`
  - `sol_software-logrotate`
  - `mass_gadget_watchdog-logrotate`
  - `sol_update_manager-logrotate`

## Update Management

The SOL device uses `sol-update` to check for and install updates from GitHub releases.

### Development/Bleeding Edge Updates
To pull development (prerelease) updates instead of only stable releases:

1. Set `DEV_MODE` to `true` in `/home/pi/.config/sol/.device.json`:
   ```json
   {
     "DEV_MODE": true,
     // ... other configuration
   }
   ```

2. How it works:
   - **DEV_MODE false (default)**: Only downloads stable releases
   - **DEV_MODE true**: Checks both prereleases and stable releases, downloading whichever has the most recent `published_at` date
   - If dates are identical, prefers stable release

3. The update manager (`sol-utils/sol_update_manager.py`) will automatically check for updates based on this setting

### Update System Architecture
- **Version Checking**: Periodic checks against GitHub releases API
- **Download Management**: Validates checksums and verifies signatures
- **Installation Process**: Atomic updates with rollback capability
- **GUI Interface**: Visual feedback during update process
- **Service Coordination**: Graceful service restarts post-update

## Inter-Service Communication
- **WebSocket Connections**: Real-time updates between server and UI
- **File-based IPC**: Shared configuration and state files
- **System Signals**: systemd service dependencies and triggers
- **D-Bus Integration**: Hardware event propagation
- **Shared Memory**: Audio buffer management

## Security Features
- **Device-specific Encryption**: Unique keys per device
- **Secure Password Storage**: AES-256-GCM for WiFi credentials
- **Service Isolation**: systemd security features
- **Update Verification**: Signed releases and checksums
- **Access Control**: Sudoers configuration for privileged operations