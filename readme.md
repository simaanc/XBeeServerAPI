# Serial Data Processor

This code is designed to read and process serial data from a specific device and send the processed data as JSON payloads to a server using POST requests.

## Prerequisites

- Python 3.x
- Required Python packages: `requests`, `pyftdi`

## Usage

1. Clone the Repository:

    To get started, you can clone this repository using the following command:
    ```bash
    git clone https://github.com/simaanc/XBeeServerAPI.git
    ```
## Installation

1. Create a Virtual Environment (Recommended):

    It's recommended to create a virtual environment to manage dependencies for this project. Navigate into the project directory and execute the following command:

    ```bash
    python -m venv .
    ```
    Activate the virtual environment
    
    On macOS and Linux
    ```bash
    source bin/activate
    ```
2. Install the required packages using the following command:

    ```bash
    pip install -r requirements.txt
    ```
3. Configure the configfile.ini:

    Modify the configuration in the configfile.ini file to provide the necessary information:

    `server_url`: The URL of the server to which JSON payloads will be sent.
    
    `api_key`: Your API key for authorization on the server.
    
    `serial_port_url`: The URL of the serial port to read data from (FTDI interface).
    
    `baud_rate`: The baud rate for the serial communication.

    Default Config:

    ```ini
    [ServerConf]
    server_url = https://example.com
    api_key = your_api_key_here
    serial_port_url = ftdi://ftdi:232:/1
    baud_rate = 115200
    ```
4. Run the code:

    Execute the script using the following command:
    ```bash
    python app.py
    ```

## Description

1. The script reads data from the specified serial port using the pyftdi library.
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

## Internal Box Information

1. XBee Sensor code stored in "SensorCode" directory
2. Linux Box at Randolph office available at: 10.10.6.66 (sensorhub1.telaeris.com)
    a. Running both testing server and sensor hub code
3. Credentials (found in Dave's skype with Christopher)    