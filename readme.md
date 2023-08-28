# Serial Data Processor

This code is designed to read and process serial data from a specific device and send the processed data as JSON payloads to a server using POST requests.

## Prerequisites

- Python 3.x
- Required Python packages: `requests`, `pyftdi`

## Usage

1. Install the required packages using the following command:

    ```bash
    pip install -r requirements.txt
    ```
2. Configure the configfile.ini:

    Modify the configuration in the configfile.ini file to provide the necessary information:

    server_url: The URL of the server to which JSON payloads will be sent.
    api_key: Your API key for authorization on the server.
    serial_port_url: The URL of the serial port to read data from (FTDI interface).
    baud_rate: The baud rate for the serial communication.

3. Run the code:

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
`date_time`: The timestamp when the data was received in ISO 8601 format (UTC).
`data`: The processed data from the received packet, converted to ASCII.

```json
{
  "source_address_64": "0013A20040A12345",
  "date_time": "2023-08-28T12:34:56.789012Z",
  "data": "Hello, World!"
}
```