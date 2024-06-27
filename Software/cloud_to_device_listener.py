import time
from azure.iot.device import IoTHubDeviceClient
import os
from pathlib import Path
import uuid
import time

RECEIVED_MESSAGES = 0

def iothub_cloudtodevice_method_sample_run():
    # Paths and configuration
    source_path = Path(__file__).resolve()
    source_dir = source_path.parent    
    filePath = str(source_dir)
    
    alreadyInitialized = False
    
    try:
        time.sleep(30)
        
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
                    elif line.startswith(('CUSTOMER_ID')):
                        customerId = line.strip().split('=', 1)[1]

                    elif line.startswith(('DERIVED_DEVICE_KEY')):
                        derivedDeviceKey = line.strip().split('=', 1)[1]
                        alreadyInitialized = True
                    elif line.startswith(('IOT_HUB_NAME')):
                        IOTHubName = line.strip().split('=', 1)[1]
                        alreadyInitialized = True                    
                    elif line.startswith(('SAS_TOKEN')):
                        sas_token = line.strip().split('=', 1)[1]
                        alreadyInitialized = True
            
                #If the device has already been registered, just send messages
                if(alreadyInitialized):
                    print("Already initialized!")
                    
                    # Get the MAC address for the DEVICE_ID
                    DEVICE_ID = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])
                    print("DEVICE_ID: ", DEVICE_ID)
                    
                    CONNECTION_STRING = "HostName=" + IOTHubName + ";DeviceId=" + DEVICE_ID + ";SharedAccessKey=" + derivedDeviceKey
                    print(CONNECTION_STRING)
                    
                    # Instantiate the client
                    client = IoTHubDeviceClient.create_from_connection_string(CONNECTION_STRING)
                    
                    time.sleep(1)

                    print ("Waiting for C2D messages, press Ctrl-C to exit")
                    try:
                        # Attach the handler to the client
                        client.on_message_received = message_handler

                        while True:
                            time.sleep(60)
                    except Exception as ex:
                        print("Unexpected error {0}".format(ex))
                    except KeyboardInterrupt:
                        print("IoT Hub C2D Messaging device sample stopped")
                    finally:
                        # Graceful exit
                        print("Shutting down IoT Hub Client")
                        client.shutdown()                    
                
                else:
                    print("Not initialized!")

    except Exception as ex:
        print("Unexpected error {0}".format(ex))
    except KeyboardInterrupt:
        print("iothub_cloudtodevice_method_sample stopped")

def message_handler(message):
    global RECEIVED_MESSAGES
    RECEIVED_MESSAGES += 1
    print("")
    print("Message received:")

    # print data from both system and application (custom) properties
    #for property in vars(message).items():
        #print ("    {}".format(property))        
    
    # Get message data and decode it
    message_data = message.data.decode('utf-8')
    print("Message Data: {}".format(message_data))

    # Check if message data contains "New Element ID: "
    if "NEW_ELEMENT_ID" in message_data:
        # Extract the element ID
        element_id = message_data.split("NEW_ELEMENT_ID:")[1]
        print("NEW_ELEMENT_ID: {}".format(element_id))
        
        if(element_id):
            print("Writing new Element_Id to the config file")
            # Paths and configuration
            source_path = Path(__file__).resolve()
            source_dir = source_path.parent    
            filePath = str(source_dir)
                            
            # Read the file
            with open(filePath + '/config.txt', 'r') as file:
                lines = file.readlines()

            #Flag to check whether the element id was overwritten
            fileContainsElementId = False

            # Replace the "ELEMENT_ID" line if it exists
            for i, line in enumerate(lines):
                if line.startswith("ELEMENT_ID"):
                    fileContainsElementId = True
                    lines[i] = 'ELEMENT_ID=' + str(element_id) + '\n'
            
            #If the ELEMENT_ID line wasn't there, add it to the end of the file
            if(fileContainsElementId == False):
                lines.append('\nELEMENT_ID=' + str(element_id) + '\n')                
                
            # Write the file
            with open(filePath + '/config.txt', 'w') as file:
                file.writelines(lines)

    print("Total calls received: {}".format(RECEIVED_MESSAGES))

if __name__ == "__main__":
    print("Starting the sample...")
    iothub_cloudtodevice_method_sample_run()
