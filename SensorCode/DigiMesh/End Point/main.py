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

def get_sensor_value():
    # Read the potentiometer value
    apin = machine.ADC('D3')
    raw_val = apin.read()
    val_mv = (raw_val * 3300) / 4095

    # Convert the millivolts value to a string and add newline character
    val_str = "{:04.0f}".format(val_mv)  # Format the value to 4 digits with leading zeros
    return val_str

def sleep_time():
    # get the sleep time from the SP parameter
    sleep_time = xbee.atcmd('SP')
    return sleep_time * 10 # convert to milliseconds

def check_network():
    nodes = list(xbee.discover())
    if len(nodes) > 0:
        print('Network found')
        return sorted(nodes, key=lambda k: k['sender_eui64'])[0]['sender_eui64']
    else:
        print('No nodes found. Trying again...')
        check_network()

# __main__ excecution -------
print("Starting Send & Sleep Cycle...")

xb = xbee.XBee()

xbee.atcmd('SM', 6)
xbee.atcmd('AV', 2)
xbee.atcmd('AC')

# ensure that other nodes exist in the network
print("Checking for other nodes...")
addr = check_network()

# get the sleep time from the configuration
sleep_ms = sleep_time()

print("Sleep time is", sleep_ms, "ms")

while True:
    # force the device to stay awake for data send
    start_time = time.ticks_ms()
    with xb.wake_lock:
        # get value from the sensor
        val = get_sensor_value()

        # Combine EUI64 and potentiometer value into a single message with newline delimiter
        print("\tSending", val, "\n")
        try:
            xbee.transmit(addr, val)  # Encode as bytes before transmission
        except OSError as error:
            print("Connection Error! Waiting and trying again...")
            time.sleep(5)
            continue
    end_time = time.ticks_ms()

    # calculate the time taken to send the data
    time_taken = end_time - start_time

    # Shhhh... go to sleep little Zigbee
    sleep_s = sleep_ms / 1000
    print("Sleeping for", sleep_s, "seconds...\n")
    xb.sleep_now(sleep_ms - time_taken - 100) # 100 ms for safety
    print("Awake!\n")
    time.sleep(0.1)