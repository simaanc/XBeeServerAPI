# XBeeServerAPI Install Guide for Raspberry Pi 4

## Requirements
- Raspberry Pi 4
- MicroSD Card and Reader (either USB or native to your computer)
- Raspberry Pi Imager (download at https://www.raspberrypi.com/software/)

## Installation

1. Open the Raspberry Pi Imager and select the OS you want to install. For this guide, we will be using Raspberry Pi OS.

2. Select the SD card you want to install the OS on.

3. Click Next and configure the Raspberry Pi installation. Be sure to fill out the information for the device name, network SSID and password, country, keyboard, and SSH. *Ensure that the SSID you use is the same one your machine is connected to.*

4. Continue with these settings and install the OS on the SD card.

5. Insert the SD Card into the Raspberry Pi and turn the device on. Attach the XBee USB to the USB on your Pi. Wait about 2 minutes.

6. Open a terminal on your computer and SCP the XBeeServerAPI into the Raspberry Pi. The command will look something like this
```
scp -r /path/to/XBeeServerAPI/ DEVICE_USER@DEVICE_NAME.local:/home/DEVICE_USER
```

7. SSH into the Raspberry Pi
```
ssh DEVICE_USER@DEVICE_NAME.local
```

8. Allow script to run:
```
chmod +x ~/XBeeServerAPI/install.sh
```

9. Run the following command
```
sudo bash ~/XBeeServerAPI/install.sh
```

## This completes the installation of the XBeeServerAPI on the Raspberry Pi 4


## Installing XBeeServerAPI with Optional Flags

The `install.sh` script provides several optional flags to customize the installation process. Here are the available flags:

- `-d DIRECTORY`: Use this flag to specify an installation directory other than the default.

- `-n`: This flag allows you to skip root checks during installation. If you encounter issues related to root checks and want to bypass them.

- `-s`: Enable silent mode by using this flag. Silent mode suppresses most of the installation prompts and messages, making the installation process less interactive.

- `-f`: If you wish to skip enabling the UFW (Uncomplicated Firewall) for SSH during installation, you can use the `-f` flag. This can be useful if you have a different firewall setup or prefer to manage SSH access manually.