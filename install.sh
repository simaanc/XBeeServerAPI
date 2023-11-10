#!/bin/bash

# Define colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Define a logfile
# LOGFILE="/var/log/xbeeserver_install.log"

# Redirect stdout and stderr to logfile
# exec 1>>$LOGFILE 2>&1

# Function to print error messages in red
error_message() {
    echo -e "${RED}$1${NC}"
}

# Function to print success messages in green
success_message() {
    echo -e "${GREEN}$1${NC}"
}

# Function to print info messages in yellow
info_message() {
    echo -e "${YELLOW}$1${NC}"
}

# Ensure the script is being run from the Software directory
# if [ ! -f "app.py" ]; then
#     error_message "Error: Please run this script from the Software directory where app.py is located."
#     exit 1
# fi

# Step 1: Update the system
info_message "Updating the system..."
sudo apt-get update -y || { error_message "Updating failed, exiting."; exit 1; }

# Step 2: Install libusb-1.0 and Python3 virtual environment utilities
info_message "Installing libusb-1.0 and Python3 virtualenv..."
sudo apt-get install libusb-1.0-0 python3-venv -y || { error_message "Installation failed, exiting."; exit 1; }

# Step 3: Create udev rule for FTDI devices
info_message "Configuring udev rules for FTDI devices..."
UDEV_RULES_PATH="/etc/udev/rules.d/11-ftdi.rules"
sudo bash -c "cat <<EOF > $UDEV_RULES_PATH
# FTDI devices
SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6001', GROUP='plugdev', MODE='0664'
SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6010', GROUP='plugdev', MODE='0664'
SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6011', GROUP='plugdev', MODE='0664'
SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6014', GROUP='plugdev', MODE='0664'
SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6015', GROUP='plugdev', MODE='0664'
SUBSYSTEM=='usb', ATTR{idVendor}=='0403', ATTR{idProduct}=='6048', GROUP='plugdev', MODE='0664'
EOF" || { error_message "Failed to create udev rules, exiting."; exit 1; }

# Reload udev rules and trigger
sudo udevadm control --reload-rules
sudo udevadm trigger

# Add the current user to the plugdev group
info_message "Adding the current user to the plugdev group..."
sudo usermod -a -G plugdev $USER || { error_message "Failed to add user to plugdev group, exiting."; exit 1; }

# Step 4: Create and activate a virtual environment
info_message "Creating a virtual environment for the XBee Server API..."
python3 -m venv Software/env || { error_message "Virtual environment creation failed, exiting."; exit 1; }
source Software/env/bin/activate

# Step 5: Install the required Python packages including Flask
info_message "Installing required Python packages including Flask..."
pip install requests pyftdi flask || { error_message "Package installation failed, exiting."; exit 1; }

# Step 6: Create a non-login user and group for the service (if not already existing)
# info_message "Creating a non-login user and group for the XBee Server API service..."
# sudo getent group xbeeserver_group >/dev/null || sudo groupadd xbeeserver_group
# sudo getent passwd xbeeserver_user >/dev/null || sudo useradd -r -s /bin/false -g xbeeserver_group xbeeserver_user

# Step 7: Create a systemd service file for the XBee Server API
info_message "Creating a systemd service file for the XBee Server API..."
SERVICE_FILE="/etc/systemd/system/xbeeserver.service"
cat <<EOF | sudo tee $SERVICE_FILE
[Unit]
Description=XBee Server API Service
After=network.target

[Service]
ExecStart=$(pwd)/Software/env/bin/python $(pwd)/Software/app.py
Restart=on-failure
RestartSec=2
StartLimitIntervalSec=0
User=$USER
WorkingDirectory=$(pwd)/Software/
Environment=PATH=$(pwd)/Software/env/bin

[Install]
WantedBy=multi-user.target
EOF

# Step 8: Reload the systemd manager configuration
info_message "Reloading the systemd manager configuration..."
sudo systemctl daemon-reload || { error_message "Failed to reload systemd, exiting."; exit 1; }

# Step 9: Enable the XBee Server API service to start on boot
info_message "Enabling the XBee Server API service to start on boot..."
sudo systemctl enable xbeeserver.service || { error_message "Failed to enable service, exiting."; exit 1; }

# Step 10: Check if UFW (Uncomplicated Firewall) is installed, install it if it's not
info_message "Checking for UFW installation..."
if ! command -v ufw &> /dev/null; then
    info_message "UFW is not installed. Installing UFW..."
    sudo apt-get install ufw -y || { error_message "Failed to install UFW, exiting."; exit 1; }
fi

# Step 11: Add firewall rule to allow traffic on port 5001
info_message "Adding firewall rule for port 5001..."
sudo ufw allow 5001/tcp || { error_message "Failed to update firewall, exiting."; exit 1; }
sudo ufw enable || { error_message "Failed to enable UFW, exiting."; exit 1; }

# Step 12: Start the XBee Server API service
info_message "Starting the XBee Server API service..."
sudo systemctl start xbeeserver.service || { error_message "Failed to start service, check status."; sudo systemctl status xbeeserver.service; exit 1; }

# Step 13: Display the configuration URL to the user
IP_ADDRESS=$(hostname -I | awk '{print $1}')
success_message "The XBee Server API service is now running."
info_message "You can configure the application by visiting the following URL: http://${IP_ADDRESS}:5001"

# Provide the user with control instructions
info_message "To stop the XBee Server API service, run: sudo systemctl stop xbeeserver.service"
info_message "To start the XBee Server API service, run: sudo systemctl start xbeeserver.service"
info_message "To restart the XBee Server API service, run: sudo systemctl restart xbeeserver.service"
info_message "If you need to check the service status, run: sudo systemctl status xbeeserver.service"

success_message "Installation and service creation for the XBee Server API is complete!"
