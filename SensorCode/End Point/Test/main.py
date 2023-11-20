import time
import xbee
# import machine

def format_eui64(addr):
    return ':'.join('%02x' % b for b in addr)


def format_packet(p):
    type = 'Broadcast' if p['broadcast'] else 'Unicast'
    print("%s message from EUI-64 %s (network 0x%04X)" %
          (type, format_eui64(p['sender_eui64']), p['sender_nwk']))
    print("from EP 0x%02X to EP 0x%02X, Cluster 0x%04X, Profile 0x%04X:" %
          (p['source_ep'], p['dest_ep'], p['cluster'], p['profile']))
    print(p['payload'], "\n")


def network_status():
    # If the value of AI is non zero, the module is not connected to a network
    return xbee.atcmd("AI")

def get_sensor_value():
    # Read the potentiometer value
    # apin = machine.ADC('D3')
    # raw_val = apin.read()
    # val_mv = (raw_val * 3300) / 4095

    # Convert the celcius value to a string and add newline character
    val_str = "{:04.0f}".format(xbee.atcmd('TP'))  # Format the value to 4 digits with leading zeros
    return val_str

def check_network_connection():
    print("Checking network connection...\n")
    while network_status() != 0: 
        time.sleep(0.1)
    print("Connected to Network!\n")

def connect_to_network_as_end_point():
    print("Joining network as an end point...\n")
    network_settings = {"ID": 0x2917, "EE": 0, "SM": 6}
    for command, value in network_settings.items():
        xbee.atcmd(command, value)
    xbee.atcmd("AC")  # Apply changes
    time.sleep(1)
    check_network_connection()

# __main__ excecution -------

xb = xbee.XBee()

with xb.wake_lock:
    connect_to_network_as_end_point()

xbee.atcmd('AV', 2)

while True:
    # force the device to stay awake for data send
    with xb.wake_lock:
        # get value from the sensor
        val = get_sensor_value()

        # Combine EUI64 and potentiometer value into a single message with newline delimiter
        print("\tSending", val, "\n")
        try:
            xbee.transmit(xbee.ADDR_COORDINATOR, val)  # Encode as bytes before transmission
        except OSError as error:
            print("Connection Error! Sleeping and trying again...")

    # Shhhh... go to sleep little Zigbee
    print("Sleeping for 15 seconds...\n")
    xb.sleep_now(15000)
    print("Awake! Checking Network...\n")
    check_network_connection()
    time.sleep(0.1)

        
