import time
from azure.iot.device import IoTHubDeviceClient
import os
from pathlib import Path
import uuid
import time
import sqlite3

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
    
    # Get message data and decode it
    message_data = message.data.decode('utf-8')
    print("Message Data: {}".format(message_data))

    # Check if message data contains "New Element ID: "
    if "NEW_ELEMENT_ID" in message_data:
        # Extract the sensor box ID and element ID
        sensor_box_id = message_data.split("SENSOR_BOX_ID:")[1].split("#")[0].strip()
        print("SENSOR_BOX_ID: {}".format(sensor_box_id))
        
        element_id = message_data.split("NEW_ELEMENT_ID:")[1].strip()
        print("NEW_ELEMENT_ID: {}".format(element_id))
        
        if(sensor_box_id and element_id):
            print("Writing new element_id to the database")
            # Paths and configuration
            source_path = Path(__file__).resolve()
            source_dir = source_path.parent    
            filePath = str(source_dir)
            
            # Check if the database exists
            if os.path.exists(filePath + '/lhp_db.db'):
                # Connect to the SQLite database
                dbConnection = sqlite3.connect(filePath + '/lhp_db.db')
                cursor = dbConnection.cursor()
                
                # Create table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sensor_box_table (
                        source_address_64 TEXT,
                        sensor_element_id TEXT,
                        isInitialized BOOLEAN DEFAULT FALSE
                    )
                ''')

                # Check if a row with the matching source_address_64 exists
                cursor.execute("SELECT * FROM sensor_box_table WHERE source_address_64 = ?", (sensor_box_id,))
                row = cursor.fetchone()
                
                if row is not None:
                    # If the row exists, check if the sensor_element_id is filled in
                    if row[0] is not None:
                        # If it is, overwrite the value
                        cursor.execute("UPDATE sensor_box_table SET sensor_element_id = ? WHERE source_address_64 = ?", (element_id, sensor_box_id))
                    else:
                        # If it's not, assign its value
                        cursor.execute("INSERT INTO sensor_box_table (sensor_element_id) VALUES (?) WHERE source_address_64 = ?", (element_id, sensor_box_id))

                    # Commit the changes and close the connection
                    dbConnection.commit()
                    dbConnection.close()

                    print(f"The sensor_element_id for the source_address_64 {sensor_box_id} has been updated to {element_id} in the database.")
                    
                else:
                    print(f"No row with the source_address_64 {sensor_box_id} exists in the database.")

    if "DELETE_ELEMENT_ID" in message_data:
        
        print("Deleting element_id from the database")
        
        # Extract the sensor box ID and element ID
        sensor_box_id = message_data.split("SENSOR_BOX_ID:")[1].split("#")[0].strip()
        print("SENSOR_BOX_ID: {}".format(sensor_box_id))
        
        if(sensor_box_id):
            # Paths and configuration
            source_path = Path(__file__).resolve()
            source_dir = source_path.parent    
            filePath = str(source_dir)
            
            # Check if the database exists
            if os.path.exists(filePath + '/lhp_db.db'):
                # Connect to the SQLite database
                dbConnection = sqlite3.connect(filePath + '/lhp_db.db')
                cursor = dbConnection.cursor()
                
                # Create table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sensor_box_table (
                        source_address_64 TEXT,
                        sensor_element_id TEXT,
                        isInitialized BOOLEAN DEFAULT FALSE
                    )
                ''')

                # Check if a row with the matching source_address_64 exists
                cursor.execute("SELECT * FROM sensor_box_table WHERE source_address_64 = ?", (sensor_box_id,))
                row = cursor.fetchone()
                
                if row is not None:
                    print("Found the row!")
                    # If the row exists, check if the sensor_element_id is filled in
                    if row[0] is not None:
                        # If it is, overwrite the value
                        cursor.execute("UPDATE sensor_box_table SET sensor_element_id = NULL WHERE source_address_64 = ?", (sensor_box_id,))
                    else:
                        # If it's not, assign its value
                        cursor.execute("INSERT INTO sensor_box_table (sensor_element_id) VALUES (NULL) WHERE source_address_64 = ?", (sensor_box_id,))

                    # Commit the changes and close the connection
                    dbConnection.commit()
                    dbConnection.close()

                    print(f"The sensor_element_id for the source_address_64 {sensor_box_id} has been updated to NULL in the database.")
                                
                else:
                    print(f"No row with the source_address_64 {sensor_box_id} exists in the database.")

    print("Total calls received: {}".format(RECEIVED_MESSAGES))

if __name__ == "__main__":
    print("Starting the sample...")
    iothub_cloudtodevice_method_sample_run()
