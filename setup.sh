#!/bin/bash
set -euo pipefail

# Weather Daemon Setup Script
# Installs and configures the weather-daemon service on Linux systems

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="/opt/weather-daemon"
CONFIG_DIR="/etc/weather-daemon"
OUTPUT_DIR="/opt/weather-daemon/cache"
SERVICE_USER="weather-daemon"
SERVICE_FILE="weather-daemon.service"

# Helper functions
info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

check_system() {
    info "Checking system requirements..."

    # Check for systemd
    if ! command -v systemctl &> /dev/null; then
        error "systemd not found. This script requires systemd."
    fi

    # Check for Python 3.9+
    if ! command -v python3 &> /dev/null; then
        error "python3 not found. Please install Python 3.9 or higher."
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
    if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"; then
        error "Python 3.9+ required. Found: $PYTHON_VERSION"
    fi

    info "System requirements met (Python $PYTHON_VERSION)"
}

create_user() {
    if id "$SERVICE_USER" &>/dev/null; then
        warn "User '$SERVICE_USER' already exists, skipping creation"
    else
        info "Creating service user '$SERVICE_USER'..."
        useradd -r -s /bin/false "$SERVICE_USER"
        info "Service user created"
    fi
}

install_system_deps() {
    info "Installing system dependencies..."

    if command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y python3-pip python3-venv python3-dev gcc
    elif command -v yum &> /dev/null; then
        yum install -y python3-pip python3-devel gcc
    elif command -v dnf &> /dev/null; then
        dnf install -y python3-pip python3-devel gcc
    else
        warn "Unknown package manager. Please install: python3-pip python3-venv python3-dev gcc manually"
    fi
}

install_daemon() {
    info "Installing weather-daemon to $INSTALL_DIR..."

    # Create install directory
    mkdir -p "$INSTALL_DIR"

    # Copy files (excluding some development artifacts)
    rsync -av --exclude='venv' \
              --exclude='.venv' \
              --exclude='__pycache__' \
              --exclude='*.pyc' \
              --exclude='.git' \
              --exclude='.env' \
              --exclude='test_output' \
              ./ "$INSTALL_DIR/"

    # Create virtual environment
    info "Creating Python virtual environment..."
    cd "$INSTALL_DIR"
    python3 -m venv venv

    # Install package
    info "Installing Python package and dependencies..."
    venv/bin/pip install --upgrade pip
    venv/bin/pip install -e .

    # Set ownership
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$INSTALL_DIR"

    info "Daemon installed successfully"
}

setup_config() {
    info "Setting up configuration..."

    # Create config directory
    mkdir -p "$CONFIG_DIR"

    # Copy example config if it doesn't exist
    if [[ ! -f "$CONFIG_DIR/config.env" ]]; then
        cp "$INSTALL_DIR/.env.example" "$CONFIG_DIR/config.env"
        info "Configuration template copied to $CONFIG_DIR/config.env"
        warn "IMPORTANT: Edit $CONFIG_DIR/config.env with your API key and location"
    else
        warn "Configuration file already exists at $CONFIG_DIR/config.env, skipping"
    fi

    # Set ownership
    chown -R "$SERVICE_USER":"$SERVICE_USER" "$CONFIG_DIR"
    chmod 600 "$CONFIG_DIR/config.env"

    info "Configuration setup complete"
}

setup_output_dir() {
    info "Setting up output directory..."

    mkdir -p "$OUTPUT_DIR"
    chown "$SERVICE_USER":"$SERVICE_USER" "$OUTPUT_DIR"
    chmod 755 "$OUTPUT_DIR"

    info "Output directory created at $OUTPUT_DIR"
}

install_systemd_service() {
    info "Installing systemd service..."

    cp "$INSTALL_DIR/deploy/systemd/$SERVICE_FILE" /etc/systemd/system/
    systemctl daemon-reload

    info "Systemd service installed"
}

enable_service() {
    info "Enabling weather-daemon service..."

    systemctl enable "$SERVICE_FILE"

    info "Service enabled (will start on boot)"
}

start_service() {
    info "Starting weather-daemon service..."

    systemctl start "$SERVICE_FILE"
    sleep 2

    if systemctl is-active --quiet "$SERVICE_FILE"; then
        info "Service started successfully"
    else
        warn "Service failed to start. Check logs with: journalctl -u $SERVICE_FILE -n 50"
        return 1
    fi
}

test_installation() {
    info "Testing installation..."

    # Check if binary is accessible
    if [[ -x "$INSTALL_DIR/venv/bin/weather-daemon" ]]; then
        info "weather-daemon binary installed correctly"
    else
        warn "weather-daemon binary not found or not executable"
    fi

    # Check service status
    systemctl status "$SERVICE_FILE" --no-pager || true

    # Show recent logs
    info "Recent logs:"
    journalctl -u "$SERVICE_FILE" -n 10 --no-pager || true
}

show_next_steps() {
    echo ""
    echo "======================================================================"
    echo -e "${GREEN}Weather Daemon Installation Complete!${NC}"
    echo "======================================================================"
    echo ""
    echo "Next steps:"
    echo ""
    echo "1. Edit the configuration file:"
    echo "   sudo nano $CONFIG_DIR/config.env"
    echo ""
    echo "2. Add your Google Maps API key and location coordinates"
    echo ""
    echo "3. Restart the service:"
    echo "   sudo systemctl restart $SERVICE_FILE"
    echo ""
    echo "4. Check service status:"
    echo "   sudo systemctl status $SERVICE_FILE"
    echo ""
    echo "5. View logs:"
    echo "   sudo journalctl -u $SERVICE_FILE -f"
    echo ""
    echo "6. Configure nginx (if not already done):"
    echo "   sudo cp $INSTALL_DIR/deploy/nginx/weather-locations.conf /etc/nginx/sites-available/"
    echo "   # Add 'include /etc/nginx/sites-available/weather-locations.conf;' to your nginx config"
    echo "   sudo nginx -t"
    echo "   sudo systemctl reload nginx"
    echo ""
    echo "Weather data will be written to: $OUTPUT_DIR/weather_forecast.json"
    echo "======================================================================"
}

main() {
    echo "======================================================================"
    echo "Weather Daemon Setup Script"
    echo "======================================================================"
    echo ""

    check_root
    check_system

    info "Starting installation..."
    echo ""

    create_user
    install_system_deps
    install_daemon
    setup_config
    setup_output_dir
    install_systemd_service
    enable_service

    echo ""
    warn "Service not started yet. Configure $CONFIG_DIR/config.env first!"
    echo ""

    test_installation
    show_next_steps
}

# Run main function
main "$@"
