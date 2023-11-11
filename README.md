# XBeeServerAPI

For a guide on how to install this system onto a Raspberry PI, please refer to the [Installation Guide](/install.md)

## Overview

Hub for all Zigbee Sensor Projects and Dev 

## Project Structure

This project is organized into four main folders:

### 1. Hardware

The `Hardware` folder contains all the sensor hardware schematics and related information.

### 2. Sensor Code

The `SensorCode` folder houses all the code flashed onto the Zigbee sensors.

Currently only includes HXBee3 Test Router - Test Router configured for Hydrogen sensor input.

### 3. Software

The `Software` folder is dedicated to the actual API and is what is run on a dedicated Linux machine with Zigbee capabilities.

Able to be configured using a web interface

### 4. Testing Environment

The `TestingEnv` folder is dedicated to the testing environment set up to verify if post requests are being sent correctly.

It creates a local web server to which the API can connect and store a test InfluxDB setup.

It should eventually not be needed and be replaced with an XPTrack instance. 

### Todo List

1. Do the hardware portion.
2. Figure out how to configure the network connection on Raspberry Pi to prepare for deployment.
