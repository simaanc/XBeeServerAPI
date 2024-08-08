import asyncio
from azure.iot.device.aio import ProvisioningDeviceClient
import os
from azure.iot.device.aio import IoTHubDeviceClient
from azure.iot.device import Message
import uuid
import base64
import hashlib
import hmac
import json

import time
import urllib
from pathlib import Path

def generate_sas_token(uri, key, expiry=999999999999999):
    ttl = time.time() + expiry
    sign_key = "%s\n%d" % ((urllib.parse.quote_plus(uri)), int(ttl))
    signature = base64.b64encode(hmac.HMAC(base64.b64decode(key), sign_key.encode('utf-8'), hashlib.sha256).digest())

    rawtoken = {
        'sr' :  uri,
        'sig': signature,
        'se' : str(int(ttl))
    }    

    return 'SharedAccessSignature ' + urllib.parse.urlencode(rawtoken)

async def main():
    alreadyInitialized = False
    messages_to_send = 1
    
    provisioning_host = None
    id_scope = None
    symmetric_key = None
    derivedDeviceKey = None
    IOTHubName = None
    customerId = None
    
    # Paths and configuration
    source_path = Path(__file__).resolve()
    source_dir = source_path.parent    
    filePath = str(source_dir)
    
    # Check if the file exists
    if not os.path.isfile(filePath + '/config.txt'):
        print("Error: The file 'config.txt' does not exist.")
        
        # Check if the error file exists
        if not os.path.isfile(filePath + '/error.txt'):
            # Open the error file in append mode
            with open(filePath +  '/error.txt', 'a') as file:
                file.write('Created new config file because it did not exist')
    else:
        #Read contents of config file
        with open(filePath + '/config.txt', 'r') as file:
            lines = file.readlines()

        #Check if the config file was empty
        if(len(lines) == 0):
            print("Error: The file 'config.txt' did not have data.")
            # Check if the error file exists
            if not os.path.isfile(filePath + '/error.txt'):
                # Open the error file in append mode
                with open(filePath +  '/error.txt', 'a') as file:
                    file.write('config.txt was empty')
        
        #If there was data in the file, read the lines
        else:
            # Print the lines
            for line in lines:
                if line.startswith(('PROVISIONING_HOST')):
                    provisioning_host = line.strip().split('=', 1)[1]
                elif line.startswith(('PROVISIONING_IDSCOPE')):
                    id_scope = line.strip().split('=', 1)[1]
                elif line.startswith(('PROVISIONING_SYMMETRIC_KEY')):
                    symmetric_key = line.strip().split('=', 1)[1]

                elif line.startswith(('DERIVED_DEVICE_KEY')):
                    derivedDeviceKey = line.strip().split('=', 1)[1]
                    alreadyInitialized = True
                elif line.startswith(('IOT_HUB_NAME')):
                    IOTHubName = line.strip().split('=', 1)[1]
                    alreadyInitialized = True
                    
                elif line.startswith(('CUSTOMER_ID')):
                    customerId = line.strip().split('=', 1)[1]

            #If the device has already been registered, just send messages
            if(alreadyInitialized):
                print("Already initialized!")

            # If the device has not been initialized, register with Azure IoT Hub
            else:
                print("Initializing!")

                if(provisioning_host and id_scope and symmetric_key and customerId):
                    #######################################################################################################
                    #Generate Registration ID!
                    
                    # Get the MAC address
                    mac_address = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])
                    print("MAC Address: ", mac_address)

                    KEY = symmetric_key

                    key_bytes = base64.b64decode(KEY)
                    hmacsha256 = hmac.new(key_bytes, digestmod=hashlib.sha256)
                    hmacsha256.update(mac_address.encode('utf-8'))

                    sig = hmacsha256.digest()
                    derivedDeviceKey = base64.b64encode(sig).decode('utf-8')

                    print("\nDERIVED_DEVICE_KEY: " + str(derivedDeviceKey) + "\n")
                    #######################################################################################################

                    #Need to check what happens if the device is already registered
                    provisioning_device_client = ProvisioningDeviceClient.create_from_symmetric_key(
                        provisioning_host=provisioning_host,
                        # registration_id=registration_id,
                        registration_id=mac_address,
                        id_scope=id_scope,
                        # symmetric_key=symmetric_key,
                        symmetric_key=derivedDeviceKey
                    )
                                       
                    # Values can be "unassigned", "assigning", "assigned", "failed", "disabled"
                    registration_result = await provisioning_device_client.register()

                    print("The complete registration result is")
                    print(registration_result.registration_state)

                    if registration_result.status == "assigned":
                        #Write to the config file
                        # Open the file in append mode
                        with open(filePath +  '/config.txt', 'a') as file:
                            file.write('\nDERIVED_DEVICE_KEY=' + str(derivedDeviceKey) + '\n')
                            file.write('IOT_HUB_NAME=' + str(registration_result.registration_state.assigned_hub) + '\n')

                        print("Will send telemetry from the provisioned device")
                        device_client = IoTHubDeviceClient.create_from_symmetric_key(
                            symmetric_key=derivedDeviceKey,
                            hostname=registration_result.registration_state.assigned_hub,
                            device_id=registration_result.registration_state.device_id,
                        )
                        # Connect the client.
                        await device_client.connect()

                        async def send_test_message(i):
                            print("sending message #" + str(i))
                            msg = Message(json.dumps( { "message" : "Device: " + mac_address + " Initialized" } ))
                            msg.custom_properties["$.ct"] = "application/json;charset=utf-8"
                            msg.custom_properties["customer_id"] = customerId
                            msg.message_id = uuid.uuid4()
                            await device_client.send_message(msg)
                            print("done sending message #" + str(i))

                        # send `messages_to_send` messages in parallel
                        await asyncio.gather(*[send_test_message(i) for i in range(1, messages_to_send + 1)])

                        # finally, disconnect
                        await device_client.disconnect()
                        
                        resource_uri = "https://{}/devices/{}".format(str(registration_result.registration_state.assigned_hub), str(registration_result.registration_state.device_id))
                        sas_token = generate_sas_token(resource_uri, derivedDeviceKey)
                        
                        #The URL needs to be generated
                        azureServerUrl = "https://{}/devices/{}/messages/events?api-version=2020-03-13".format(str(registration_result.registration_state.assigned_hub), str(registration_result.registration_state.device_id))
                        
                        with open(filePath +  '/config.txt', 'a') as file:
                            file.write('\nAZURE_SERVER_URL=' + azureServerUrl + '\n')
                            file.write('SAS_TOKEN=' + sas_token + '\n')
                            
                        
                    else:
                        print("Can not send telemetry from the provisioned device")
                else:
                    print("Not all values present.")

if __name__ == "__main__":
    asyncio.run(main())
