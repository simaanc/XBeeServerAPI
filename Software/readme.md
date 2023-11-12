# Serial Data Processor - Linux Server Sensor Hub Code

This code is designed to read and process serial data from an XBee serial device receiving data from multiple Zigbee sensors and send the processed data as a JSON payload to XPTrack server using POST requests.

## Prerequisites

- Python 3.x
- Required Python packages: `requests`, `pyftdi`, `flask`

## Installation

1. Clone the Repository:

    To get started, you can clone this repository using the following command:
    ```bash
    git clone https://github.com/Telaeris/XBeeServerAPI.git
    ```

    For a guide on how to install this system onto a Raspberry PI, please refer to the [Installation Guide](/install.md)

## Installing XBeeServerAPI with Optional Flags

The `install.sh` script provides several optional flags to customize the installation process. Here are the available flags:

- `-d DIRECTORY`: Use this flag to specify an installation directory other than the default.

- `-n`: This flag allows you to skip root checks during installation. If you encounter issues related to root checks and want to bypass them.

- `-s`: Enable silent mode by using this flag. Silent mode suppresses most of the installation prompts and messages, making the installation process less interactive.

- `-f`: If you wish to skip enabling the UFW (Uncomplicated Firewall) for SSH during installation, you can use the `-f` flag. This can be useful if you have a different firewall setup or prefer to manage SSH access manually.

## Description

1. The app reads data from the specified serial port using the pyftdi library.
2. It maintains a buffer to collect incoming data until it forms complete packets.
3. Complete packets are processed according to a specific format and are converted to JSON payloads.
4. The JSON payloads are then added to a thread-safe queue for processing.
5. A separate thread continuously reads from the queue and sends the JSON payloads as POST requests to the specified server.

## JSON Payload

The JSON payload sent to the server consists of the following fields:

`source_address_64`: The 64-bit source address from the received data.

`date_time`: The timestamp when the data was received in EPOCH (MS Precision).

`data`: The processed data from the received packet, converted to ASCII.

```json
{
  "source_address_64": "0013A20040A12345",
  "date_time": "1694467656480",
  "data": "Hello, World!"
}
```
