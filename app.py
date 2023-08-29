import requests
import pyftdi.serialext
import datetime
import configparser
import threading
import os
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


def calculate_checksum(data):
    checksum = 0xFF - (sum(data) & 0xFF)
    return checksum & 0xFF


def validate_checksum(data):
    calculated_checksum = calculate_checksum(
        data[:-1]
    )  # Exclude the last byte (received checksum)
    received_checksum = data[-1]
    return calculated_checksum == received_checksum


def serial_reader():
    buffer = b""  # Buffer to hold incoming data

    while True:
        try:
            # Read incoming data
            new_data = port.read(6)  # Adjust the read size as needed

            if not new_data:
                continue
            buffer += new_data

            while buffer:
                # Find the index of the next start delimiter
                start_idx = buffer.find(b"\x7E")

                if start_idx == -1:
                    buffer = b""  # Discard incomplete packets
                    break
                if start_idx > 0:
                    buffer = buffer[start_idx:]

                # Check if there's enough data for MSB, LSB, and checksum
                if len(buffer) < 5:  # Minimum length for MSB, LSB, and checksum
                    break

                # Extract MSB and LSB to calculate packet length
                msb = int(buffer[1:2].hex(), 16)
                lsb = int(buffer[2:3].hex(), 16)
                packet_length = (msb << 8) | lsb

                # Check if there's enough data for the complete packet
                if (
                    len(buffer) < packet_length + 4
                ):  # 4 bytes for MSB, LSB, and checksum
                    break

                # Extract and process the complete packet
                complete_packet = buffer[: packet_length + 4]
                buffer = buffer[packet_length + 4 :]

                # Extract the frame type (4th byte)
                frame_type = complete_packet[3]
                # print("Frame Type:", hex(frame_type))

                # Extract the 64-bit source address (next 8 bytes)
                source_address_64 = complete_packet[4:12]
                # print("Source Address (64-bit):", source_address_64.hex())

                # Extract the 16-bit source network address (next 2 bytes)
                source_address_16 = complete_packet[12:14]
                # print("Source Address (16-bit):", source_address_16.hex())

                # Extract the receive options (next 1 byte)
                receive_options = complete_packet[14]
                # print("Receive Options:", hex(receive_options))

                # Calculate the number of bytes for the received data
                received_data_length = (
                    packet_length - 12
                )  # Subtracting 8 bytes for address, 2 bytes for network address, and 1 byte for options

                # Extract the received data
                received_data = complete_packet[15 : 15 + received_data_length]
                # print("Received Data (Hex):", received_data.hex())

                # Convert received data from hex to ASCII
                received_data_ascii = bytes.fromhex(received_data.hex()).decode(
                    "utf-8", errors="replace"
                )
                received_data_ascii = "".join(
                    char for char in received_data_ascii if char.isascii()
                )
                # print("Received Data (ASCII):", received_data_ascii)

                # Validate the checksum
                received_packet = complete_packet[3:]  # Exclude the start delimiter
                is_checksum_valid = validate_checksum(received_packet)
                if is_checksum_valid:
                    print("Checksum is valid.")
                else:
                    print("Checksum is invalid. Ignoring the data.")
                    continue

                # Process the packet based on the identified frame type
                if frame_type == 0x90:  # Receive packet
                    print("Received Packet 90:", complete_packet.hex())

                    current_time = datetime.datetime.now(datetime.timezone.utc)
                    date_time_str = current_time.isoformat()

                    # Construct JSON payload
                    payload = {
                        "source_address_64": str(source_address_64.hex()).upper(),
                        "date_time": date_time_str,
                        "data": received_data_ascii,
                    }
                    print(payload)
                    # Put the JSON payload in a queue to be processed outside this loop
                    json_payload_queue.put(payload)
                elif frame_type == 0x95:  # Node identification indicator
                    print("Received Packet 95:", complete_packet.hex())
                else:
                    print("Unknown frame type:", hex(frame_type))

                print("\n\n")

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
            "Content-Type": "application/json",
        }

        post_response = requests.post(server_url, json=payload, headers=headers)

        # Check status code for response received (success code - 200)
        print("POST Status Code:", post_response.status_code)
        print("POST Response Content:", post_response.content)

    except queue.Empty:
        pass  # No new payloads to process

    except Exception as e:
        print("Exception in main loop:", e)
