import requests
import pyftdi.serialext
import datetime
import configparser
import threading
import os
import queue
import time
from pathlib import Path

from flask import Flask, request, render_template, jsonify

# Paths and configuration
source_path = Path(__file__).resolve()
source_dir = source_path.parent
config = configparser.ConfigParser()
configLocation = str(source_dir) + "/configfile.ini"

app = Flask(__name__)

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
    # Standard byte offset for Zigbee/DigiMesh packet
    standard_offset = 3
    #Standard byte offset for Zigbee/DigiMesh Checksum
    checksum_offset = 1
    #minimum packet size with one byte of data (for 0x90 packet)
    min_packet_size = 17
    #byte of start delimiter
    delimiter = b"\x7E"

    buffer = b""  # Buffer to hold incoming data

    while True:
        try:
            # Read incoming data one byte at a time
            new_data = port.read(1)
            if not new_data:
                time.sleep(0.5) #wait half a second for new data
                continue
            buffer += new_data

            while buffer:
                # Find the index of the next start delimiter
                start_idx = buffer.find(delimiter)

                if start_idx == -1:
                    buffer = b""  # Discard incomplete packets
                    break
                if start_idx > 0:
                    buffer = buffer[start_idx:]

                # Check and see if this packet meets its minimum size with one byte of data
                if len(buffer) < min_packet_size: 
                    break

                # Extract MSB and LSB to calculate packet length
                msb = int(buffer[1:2].hex(), 16)
                lsb = int(buffer[2:3].hex(), 16)
                packet_length = (msb << 8) | lsb
                total_packet_length = packet_length + standard_offset + checksum_offset

                # Check if there's enough data for the complete packet
                if (
                    len(buffer) < total_packet_length
                ):
                    break

                print("New Packet Received")

                # Extract and process the complete packet
                end_packet_idx = total_packet_length + 1
                complete_packet = buffer[:end_packet_idx]
                buffer = buffer[end_packet_idx:] # buffer will be cleared if this is the only packet

                # Extract the frame type (4th byte)
                frame_type = complete_packet[3]

                if frame_type == 0x90:
                    parse_receive_data_packet(complete_packet[3:], packet_length)
                elif frame_type == 0x92:
                    parse_io_sample_packet(complete_packet[3:], packet_length)

        except Exception as e:
            print("Exception in serial_reader:", e)
            time.sleep(1)
                # # Extract the 64-bit source address (next 8 bytes)
                # source_address_64 = complete_packet[4:12]

                # # Extract the 16-bit source network address (next 2 bytes)
                # source_address_16 = complete_packet[12:14]

                # # Extract the receive options (next 1 byte)
                # receive_options = complete_packet[14]

                # # Calculate the number of bytes for the received data
                # received_data_length = (
                #     packet_length - 12
                # )
                
                # # Extract the received data
                # received_data = complete_packet[15 : 15 + received_data_length]

                # # Convert received data from hex to ASCII
                # received_data_ascii = bytes.fromhex(received_data.hex()).decode(
                #     "utf-8", errors="replace"
                # )
                # received_data_ascii = "".join(
                #     char for char in received_data_ascii if char.isascii()
                # )

                # # Validate the checksum
                # received_packet = complete_packet[3:]  # Exclude the start delimiter
                # is_checksum_valid = validate_checksum(received_packet)
                # if is_checksum_valid:
                #     print("Checksum is valid.")
                # else:
                #     print("Checksum is invalid. Ignoring the data.")
                #     continue

                # # Process the packet based on the identified frame type
                # if frame_type == 0x90:  # Receive packet
                #     print("Received Packet 90:", complete_packet.hex())

                #     current_time = datetime.datetime.now(datetime.timezone.utc)
                #     epoch_time = round(current_time.timestamp(), 3) * 1000
                #     # epoch_time = current_time.isoformat()
                    
                #     # Construct JSON payload
                #     payload = {
                #         "source_address_64": str(source_address_64.hex()).upper(),
                #         "date_time": epoch_time,
                #         "data": float(received_data_ascii),
                #     }
                    
                #     print(payload)
                #     # Put the JSON payload in a queue to be processed outside this loop
                #     json_payload_queue.put(payload)
                # elif frame_type == 0x95:  # Node identification indicator
                #     print("Received Packet 95:", complete_packet.hex())
                # else:
                #     print("Unknown frame type:", hex(frame_type))

# Parse an 0x90 packet, past the delimiter, length, and frame type bytes
def parse_receive_data_packet(packet, length):
    print("Received Packet 0x90:", packet.hex())
    # Extract the 64-bit source address (next 8 bytes)
    source_address_64 = packet[1:9]

    # Extract the 16-bit source network address (next 2 bytes)
    source_address_16 = packet[9:11]

    # Extract the receive options (next 1 byte)
    receive_options = packet[11]

    # Calculate the number of bytes for the received data
    received_data_length = (
        length - 12
    )

    # Extract the received data
    received_data = packet[12 : 12 + received_data_length]

    # Convert received data from hex to ASCII
    received_data_ascii = bytes.fromhex(received_data.hex()).decode(
        "utf-8", errors="replace"
    )
    received_data_ascii = "".join(
        char for char in received_data_ascii if char.isascii()
    )

    # Validate the checksum
    checksum_valid = validate_checksum(packet)
    if checksum_valid:
        print("Checksum is valid.")
        add_json_payload(str(source_address_64.hex()).upper(), float(received_data_ascii))
    else:
        print("Checksum is invalid. Ignoring the data.")

# Parse an 0x92 packet, past the delimiter, length, and frame type bytes
def parse_io_sample_packet(packet, length):
    print("Received Packet 0x92:", packet.hex())
    # reference voltage of 2.5 volts
    voltage_ref = 2.5
    c_factor = 1023

    # extract the 64 bit source address
    source_address_64 = packet[1:9]

    # Extract the 8 bit receive options
    receive_options = packet[11]

    # Extrack the number of sample, and check that it is 1
    num_samples = packet[12]
    if num_samples != 0x01:
        print("Packet contains more than one sample! Aborting")
        return;

    #Extract the 16 bit digital sample mask, and check that it is 0
    digital_sample_mask = packet[13:15]
    if int(digital_sample_mask.hex(), 16) > 0:
        print("Unsupported Digital Sample Provided! Aborting")
        return

    #Extract the 8 bit analog sample mask
    analog_sample_mask = packet[15]

    #Extract the 16 bit sample value
    sample_value = packet[16:18]
    act_sample_value = (int(sample_value.hex(), 16) / c_factor) * voltage_ref

    # Validate the checksum
    checksum_valid = validate_checksum(packet)
    if checksum_valid:
        print("Checksum is valid.")
        add_json_payload(str(source_address_64.hex()).upper(), act_sample_value)
    else:
        print("Checksum is invalid. Ignoring the data.")


# add json payload to the queue
def add_json_payload(source_address_64, data):
    current_time = datetime.datetime.now(datetime.timezone.utc)
    epoch_time = round(current_time.timestamp(), 3) * 1000
    
    # Construct JSON payload
    payload = {
        "source_address_64": source_address_64,
        "date_time": epoch_time,
        "data": data,
    }

    print(payload)

    json_payload_queue.put(payload)



# Create a thread-safe queue for JSON payloads
json_payload_queue = queue.Queue()

# Create a separate thread for serial reading
serial_thread = threading.Thread(target=serial_reader)
serial_thread.daemon = True
serial_thread.start()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Update the configuration with values from the form
        config["ServerConf"]["server_url"] = request.form["server_url"]
        config["ServerConf"]["api_key"] = request.form["api_key"]
        write_file()  # Save the updated configuration to the file
        return "Configuration updated successfully."

    # Render the configuration form
    return render_template(
        "index.html",
        server_url=config["ServerConf"]["server_url"],
        api_key=config["ServerConf"]["api_key"],
    )


@app.route("/check_auth_connection", methods=["POST"])
def check_auth_connection():
    try:
        # Get the JSON data from the request
        data = request.get_json()

        # Extract the server URL and API key
        server_url = data.get("server_url")
        api_key = data.get("api_key")

        payload = {}  # Include the API key in the payload

        headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
        }

        # Check if both server URL and API key are provided
        if server_url and api_key:
            try:
                # Make a POST request to the receive server's auth_check route
                auth_check_url = server_url + "/api/v1/sensor-hubs/test-connection"
                response = requests.post(auth_check_url, json=payload, headers=headers)

                print("POST Status Code:", response.status_code)

                if response.status_code == 200:
                    result = {"message": "Authorization and Connection are OK!"}
                else:
                    result = {"message": "Authorization or Connection failed."}
            except requests.exceptions.RequestException as e:
                # Handle exceptions raised by requests.post
                result = {"message": "Authorization or Connection failed"}
        else:
            result = {"message": "Missing server URL or API key."}

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == '__main__':

    # Need to run this from a shell script >>> os.system("pkill python")

    # Create a thread for the Flask app
    flask_thread = threading.Thread(target=app.run, kwargs={'host': '0.0.0.0', 'port': 5001})
    flask_thread.daemon = True
    flask_thread.start()
    
    #track the number of times a request bounces back
    bounce_count = 0

    # Main loop to process JSON payloads and make POST requests
    while True:
        try:
            
            payload = json_payload_queue.get(timeout=1)
            json_payload_queue.task_done()

            server_url = config["ServerConf"]["server_url"] + "/api/v1/sensors"
            api_key = config["ServerConf"]["api_key"]

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            # send the request with a timeout of 5 seconds
            post_response = requests.post(server_url, json=payload, headers=headers, timeout=5)
            
            bounce_count = 0 #reset the bounce counter

            # Check status code for response received (success code - 200)
            print("POST Status Code:", post_response.status_code)
            print("POST Response Content:", post_response.content, "\n")
            
        except requests.exceptions.Timeout:
            bounce_count += 1
            print("POST request timed out. Number of Tries:", bounce_count)
            print('Trying again...')
            while bounce_count < 6:
                try:
                    post_response = requests.post(server_url, json=payload, headers=headers, timeout=5)
                    post_response.raise_for_status()
                    print("POST Status Code:", post_response.status_code)
                    print("POST Response Content:", post_response.content, "\n")
                    bounce_count = 0
                    break
                except requests.exceptions.Timeout:
                    bounce_count += 1
                    print("POST request timed out. Number of Tries:", bounce_count)
                    print('Trying again...')
                except Exception as e:
                    print("Exception in main loop:", e)
            else:
                bounce_count = 0
                print('POST request failed after 5 tries. Trying Next Packet...')
                continue

        except queue.Empty:
            pass  # No new payloads to process

        except Exception as e:
            print("Exception in main loop:", e)