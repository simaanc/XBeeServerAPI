#!/bin/bash

# Default values for command-line arguments
install_dir="/home/$USER/XBeeServerAPI"
no_root_check=0  # Flag for bypassing root check
silent_mode=0    # Flag for silent mode
skip_ufw_ssh=0   # Flag for skipping UFW SSH rule
service_name="xbeeserver.service"  # Service name

# Determine the destination path for app.py based on install_dir
app_destination="$install_dir/Software/app.py"  # Adjust this path as needed

# Define colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Enhanced logging function
log_message() {
    if [ "$silent_mode" -eq 0 ]; then
        local type="$1"
        local message="$2"
        echo -e "[$(date)] $type: $message"
    fi
}

# Function to print error messages in red
error_message() {
    log_message "${RED}ERROR${NC}" "$1"
}

# Function to print success messages in green
success_message() {
    log_message "${GREEN}SUCCESS${NC}" "$1"
}

# Function to print info messages in yellow
info_message() {
    log_message "${YELLOW}INFO${NC}" "$1"
}

# Function to update app.py and restart the service
update_app_and_restart_service() {
    info_message "Stopping the service: $service_name..."
    sudo systemctl stop "$service_name" || { error_message "Failed to stop $service_name"; exit 1; }

    info_message "Updating app.py..."
    if [ -f "$install_dir/Software/app.py" ]; then
        sudo cp "$install_dir/Software/app.py" "$app_destination" || { error_message "Failed to update app.py."; exit 1; }
    else
        error_message "Updated app.py not found."
        exit 1
    fi

    info_message "Restarting the service: $service_name..."
    sudo systemctl start "$service_name" || { error_message "Failed to start $service_name"; exit 1; }

    success_message "app.py updated and service restarted successfully."
    exit 0
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -d <dir>       Set the installation directory"
    echo "  -s             Silent mode"
    echo "  -f             Skip UFW SSH rule"
    echo "  -uninstall     Uninstall the software"
    echo "Example:"
    echo "  $0 -d /custom/dir -n -s"
}

# Function to check for required commands and install UFW if not found
check_dependencies() {
    local dependencies=("python3" "pip" "systemctl" "cp" "mkdir")
    for cmd in "${dependencies[@]}"; do
        if ! command -v "$cmd" &> /dev/null; then
            error_message "Required command '$cmd' not found. Please install it."
            exit 1
        fi
    done

    # Improved package checking
    local packages=("libusb-1.0-0" "python3-venv")
    for pkg in "${packages[@]}"; do
        if ! dpkg-query -W -f='${Status}' $pkg 2>/dev/null | grep -q "install ok installed"; then
            error_message "Required package '$pkg' not installed. Please install it."
            exit 1
        fi
    done

    # Special handling for UFW
    if ! command -v ufw &> /dev/null; then
        info_message "UFW is not installed. Installing UFW..."
        sudo apt-get install ufw -y || { error_message "Failed to install UFW, exiting."; exit 1; }
    fi
}

# Function to configure udev rules
configure_udev_rules() {
    local UDEV_RULES_PATH="/etc/udev/rules.d/11-ftdi.rules"
    sudo bash -c "cat <<EOF > $UDEV_RULES_PATH
    # FTDI devices
    SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6001', GROUP='plugdev', MODE='0664'
    SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6010', GROUP='plugdev', MODE='0664'
    SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6011', GROUP='plugdev', MODE='0664'
    SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6014', GROUP='plugdev', MODE='0664'
    SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6015', GROUP='plugdev', MODE='0664'
    SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6048', GROUP='plugdev', MODE='0664'
EOF" || { error_message "Failed to create udev rules, exiting."; exit 1; }
}

uninstall() {
    # Confirmation before uninstalling
    echo "You are about to uninstall the software. This action cannot be undone."
    read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error_message "Uninstallation aborted by the user."
        exit 1
    fi

    echo "Starting uninstallation process..."

    # Stop the service
    echo "Stopping the service: $service_name..."
    sudo systemctl stop "$service_name" 2>/dev/null

    # Disable the service
    echo "Disabling the service: $service_name..."
    sudo systemctl disable "$service_name" 2>/dev/null

    # Remove the systemd service file
    local SERVICE_FILE="/etc/systemd/system/$service_name"
    if [ -f "$SERVICE_FILE" ]; then
        echo "Removing the systemd service file..."
        sudo rm "$SERVICE_FILE"
    fi

    # Reload systemd daemon
    sudo systemctl daemon-reload

    # Remove the specific UFW rule for port 5001 added by this script
    echo "Reverting UFW rule for port 5001 added by the script..."
    sudo ufw delete allow 5001/tcp || { error_message "Failed to remove UFW rule for port 5001, please check manually."; }

    # Check if UFW is active and reload it
    if sudo ufw status | grep -qw "active"; then
        sudo ufw reload || { error_message "Failed to reload UFW, please check manually."; }
    fi

    # Remove installation directory
    if [ -d "$install_dir/Software" ]; then
        echo "Removing installed software directory..."
        sudo rm -rf "$install_dir/Software"
    fi

    # Remove log files
    if [ -f "$LOGFILE" ]; then
        echo "Removing installation log file..."
        sudo rm "$LOGFILE"
    fi

    if [ -f "/var/log/XBeeServerAPI.log" ]; then
        echo "Removing application log file..."
        sudo rm "/var/log/XBeeServerAPI.log"
    fi

    # Add here any other cleanup tasks (e.g., UFW rule removal, udev rules cleanup)

    echo "Uninstallation complete."
}

# Function to validate the installation path
validate_install_path() {
    if [[ ! -d "$install_dir" || ! -w "$install_dir" ]]; then
        error_message "Invalid installation path: '$install_dir' is not a directory or not writable."
        exit 1
    fi
}

# Function for signal handling and cleanup
cleanup() {
    echo -e "${RED}Caught signal, script interrupted. Cleanup initiated.${NC}"
    
    # Notify about partial installation
    echo "The script was interrupted. The system may be in a partially installed state."
    echo "Please check the following:"
    echo "1. The 'Software' directory in '$install_dir' may need to be manually removed if partially copied."
    echo "2. Systemd service might not be fully configured. Check '/etc/systemd/system/xbeeserver.service'."
    echo "3. Firewall settings and udev rules might have been partially applied."

    exit 1
}

# Function for user confirmation prompt
confirm_action() {
    if [ "$silent_mode" -eq 0 ]; then
        read -p "Are you sure you want to proceed? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error_message "Operation aborted by the user."
            exit 1
        fi
    fi
}

# Main execution starts here

# Trap signals
trap cleanup SIGINT SIGTERM

# Check for required dependencies
check_dependencies

while [ $# -gt 0 ]; do
    case "$1" in
        -h|--help)
            show_usage
            exit 0
            ;;
        -d)
            install_dir="$2"
            if [ -z "$install_dir" ]; then
                echo "Error: -d requires an argument."
                show_usage
                exit 1
            fi
            shift 2
            ;;
        -n)
            no_root_check=1
            shift
            ;;
        -s)
            silent_mode=1
            shift
            ;;
        -f)
            skip_ufw_ssh=1
            shift
            ;;
        -uninstall)
            uninstall  # Call the uninstall function
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate installation path
validate_install_path

# User confirmation
confirm_action

# Check if the Software directory exists in the current directory
if [ ! -d "Software" ]; then
    error_message "Error: Software directory not found in the current directory."
    exit 1
fi

# Installation directory check
sudo mkdir -p "$install_dir"

# Copy the Software directory
if [ -d "$install_dir/Software" ]; then
    info_message "Software directory already exists in $install_dir. Skipping copy."
else
    info_message "Copying Software directory to $install_dir..."
    sudo cp -r Software "$install_dir/"
fi

# System update
info_message "Updating the system..."
sudo apt-get update -y || { error_message "Updating failed, exiting."; exit 1; }

# Udev rules configuration
info_message "Configuring udev rules for FTDI devices..."
configure_udev_rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Adding user to the plugdev group
info_message "Adding the current user to the plugdev group..."
sudo usermod -a -G plugdev $USER || { error_message "Failed to add user to plugdev group, exiting."; exit 1; }

# Virtual environment creation
info_message "Creating a virtual environment for the XBee Server API..."
python3 -m venv "$install_dir/Software/env" || { error_message "Virtual environment creation failed, exiting."; exit 1; }
source "$install_dir/Software/env/bin/activate"

# Python packages installation
info_message "Installing required Python packages including Flask..."
pip install requests pyftdi flask || { error_message "Package installation failed, exiting."; exit 1; }

# Modify the systemd service file creation section
cat <<EOF | sudo tee $SERVICE_FILE
[Unit]
Description=XBee Server API Service
After=network.target

[Service]
ExecStart=$install_dir/Software/env/bin/python $install_dir/Software/app.py
Restart=on-failure
RestartSec=2
StartLimitIntervalSec=0
User=$USER
WorkingDirectory=$install_dir/Software/
Environment=PATH=$install_dir/Software/env/bin

[Install]
WantedBy=multi-user.target
EOF

# Systemd manager configuration reload
info_message "Reloading the systemd manager configuration..."
sudo systemctl daemon-reload || { error_message "Failed to reload systemd, exiting."; exit 1; }

# Enabling the service to start on boot
info_message "Enabling the XBee Server API service to start on boot..."
sudo systemctl enable xbeeserver.service || { error_message "Failed to enable service, exiting."; exit 1; }

# Configure UFW
if [ "$skip_ufw_ssh" -eq 0 ]; then
    info_message "Configuring UFW - allowing SSH..."
    sudo ufw allow ssh || { error_message "Failed to configure UFW for SSH, exiting."; exit 1; }
fi

info_message "Adding firewall rule for port 5001..."
sudo ufw allow 5001/tcp || { error_message "Failed to update firewall, exiting."; exit 1; }

info_message "Enabling UFW..."
sudo ufw enable || { error_message "Failed to enable UFW, exiting."; exit 1; }

# Starting the XBee Server API service
info_message "Starting the XBee Server API service..."
sudo systemctl start xbeeserver.service || { error_message "Failed to start service, check status."; sudo systemctl status xbeeserver.service; exit 1; }

# Displaying configuration URL
IP_ADDRESS=$(hostname -I | awk '{print $1}')
success_message "The XBee Server API service is now running."
info_message "You can configure the application by visiting the following URL: http://${IP_ADDRESS}:5001"

# Control instructions
info_message "To stop the XBee Server API service, run: sudo systemctl stop xbeeserver.service"
info_message "To start the XBee Server API service, run: sudo systemctl start xbeeserver.service"
info_message "To restart the XBee Server API service, run: sudo systemctl restart xbeeserver.service"
info_message "If you need to check the service status, run: sudo systemctl status xbeeserver.service"

success_message "Installation and service creation for the XBee Server API is complete!"
