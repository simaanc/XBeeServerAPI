import time
import xbee
import machine

MODEM_STATUS_NETWORK_WOKE = 0x0B

def get_sensor_value():
    # Read the potentiometer value
    apin = machine.ADC('D3')
    raw_val = apin.read()
    val_mv = (raw_val * 3300) / 4095

    # Convert the millivolts value to a string and add newline character
    val_str = "{:04.0f}".format(val_mv)  # Format the value to 4 digits with leading zeros
    return val_str

def handle_modem_status(addr):
    def w(status):        
        if status == MODEM_STATUS_NETWORK_WOKE:
            print('Network woke up. Sending to', addr, 'with TP value', xbee.atcmd('TP'))
            xbee.transmit(addr, get_sensor_value())
    return w

def check_network():
    nodes = list(xbee.discover())
    if len(nodes) > 0:
        print('Network found')
        return sorted(nodes, key=lambda k: k['sender_eui64'])[0]['sender_eui64']
    else:
        return False

print('Waiting for network to wake up...')
while True:
    addr = check_network()
    if addr == False:
        print('No network found. Waiting 5 seconds...')
        continue        
    # Register the above function as the modem status callback so that it
    # will be called whenever a modem status is generated.
    print('Registering modem status callback')
    xbee.modem_status.callback(handle_modem_status(addr))
    break

print('Enable sync sleep modem status messages')
xbee.atcmd("SO", 4)

print('Enable sync sleep')
xbee.atcmd("SM", 8)

while True:
    p = xbee.receive()
    if p:
        print(p['payload'], "\n")
    else:
        time.sleep(0.2)

# Note that even after this code completes the modem status callback
# will still be registered and will continue to execute until
# MicroPython is rebooted or xbee.modem_status.callback(None) is called.