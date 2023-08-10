import requests
import pyftdi.serialext
import datetime
import json
import configparser
import os
import threading
import queue
from pathlib import Path

# Paths and configuration
source_path = Path(__file__).resolve()
source_dir = source_path.parent
config = configparser.ConfigParser()
configLocation = str(source_dir) + "/configfile.ini"

# Open a serial port on the second FTDI device interface (IF/2) @ 115200 baud
port = pyftdi.serialext.serial_for_url("ftdi://ftdi:232:/1", baudrate=115200)

def write_file():
    with open(configLocation, "w") as configfile:
        config.write(configfile)


# Configuration setup
config = configparser.ConfigParser()
if not os.path.exists(configLocation):
    config["ServerConf"] = {
        "server_url": "https://example.com",
        "api_key": "your_api_key_here",
        "serial_port_url": "ftdi://ftdi:232:/1",
        "baud_rate": "115200",
    }
    write_file()
else:
    config.read(configLocation)
    print(config.sections())

def serial_reader():
    buffer = b""  # Buffer to hold incoming data

    while True:
        try:
            # Read incoming data
            new_data = port.read(25)  # Adjust the read size as needed

            if not new_data:
                continue
            buffer += new_data

            while buffer:
                # Find the index of the next start delimiter
                start_idx = buffer.find(b"\x7E")

                if start_idx == -1:
                    buffer = b""  # Discard incomplete packets
                    break            # If the start delimiter is not at the beginning, discard bytes before it
                if start_idx > 0:
                    buffer = buffer[start_idx:]
                # Check if there's enough data for a complete packet
                if len(buffer) < 20:  # Adjust based on packet structure
                    break
                # Extract and process the complete packet
                complete_packet = buffer[:20]  # Adjust based on packet structure
                buffer = buffer[20:]  # Remove the processed packet from the buffer

                # Process the packet as before
                hex_representation = complete_packet.hex()

                hex_representation = hex_representation.upper()

                # Interpret the API frame structure
                start_delimiter = hex_representation[0:2]
                length = hex_representation[2:6]
                frame_type = hex_representation[6:8]
                source_address_64 = hex_representation[8:24]
                source_address_16 = hex_representation[24:28]
                receive_options = hex_representation[28:30]
                data_hex = hex_representation[30:38]
                checksum_hex = hex_representation[38:40]

                # Convert data to ASCII
                data_ascii = bytes.fromhex(data_hex).decode("utf-8", errors="replace")

                current_time = datetime.datetime.now(datetime.timezone.utc)
                date_time_str = current_time.isoformat()

                # Filter out non-ASCII characters from data_ascii
                data_ascii = "".join(char for char in data_ascii if char.isascii())

                global current_value
                current_value = data_ascii

                # Construct JSON payload
                payload = {
                    "source_address_64": source_address_64,
                    "date_time": date_time_str,
                    "data": data_ascii
                }

                # Put the JSON payload in a queue to be processed outside this loop
                json_payload_queue.put(payload)

        except Exception as e:
            print("Exception in serial_reader:", e)


# Create a thread-safe queue for JSON payloads
json_payload_queue = queue.Queue()

# Create a separate thread for serial reading
serial_thread = threading.Thread(target=serial_reader)
serial_thread.daemon = True
serial_thread.start()

# Main loop to process JSON payloads and make POST requests
while True:
    try:
        payload = json_payload_queue.get(timeout=1)  # Adjust the timeout as needed
        json_payload_queue.task_done()

        server_url = config["ServerConf"]["server_url"]
        api_key = config["ServerConf"]["api_key"]

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        post_response = requests.post(server_url, json=payload, headers=headers)

        # Check status code for response received (success code - 200)
        print("POST Status Code:", post_response.status_code)
        print("POST Response Content:", post_response.content)

    except queue.Empty:
        pass  # No new payloads to process

    except Exception as e:
        print("Exception in main loop:", e)