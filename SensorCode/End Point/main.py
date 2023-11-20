import time
import xbee
import machine

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
    apin = machine.ADC('D3')
    raw_val = apin.read()
    val_mv = (raw_val * 3300) / 4095

    # Convert the millivolt value to a string and add newline character
    val_str = "{:04.0f}".format(val_mv)  # Format the value to 4 digits with leading zeros
    return val_str

def connect_to_network_as_end_point(pan_id):
    print("Joining network as an end point...\n")
    xbee.atcmd("NI", "Router2")
    network_settings = {"CE": 0, "ID": pan_id, "EE": 0, "SM": 6}
    for command, value in network_settings.items():
        xbee.atcmd(command, value)
    xbee.atcmd("AC")  # Apply changes
    time.sleep(1)

    while network_status() != 0:
        time.sleep(0.1)
    print("Connected to Network\n")

def get_sleep_time():
    sp_value = xbee.atcmd("SP")
    return sp_value

connect_to_network_as_end_point(0x2917)

# Start the transmit/receive loop
print("Sending pot data every {} second".format(interval / 1000))

xbee.atcmd('AV', 2)

while True:
    p = xbee.receive()
    if p:
        format_packet(p)
    else:
        # get value from the sensor
        val = get_sensor_value()

        # Combine EUI64 and potentiometer value into a single message with newline delimiter
        print("\tSending", val)
        try:
            xbee.transmit(xbee.ADDR_COORDINATOR, val)  # Encode as bytes before transmission
        except Exception as err:
            print(err)

        last_sent = time.ticks_ms()
        time.sleep(1)
