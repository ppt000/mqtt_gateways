'''Starter module for the C-Bus gateway.'''

import os.path

# import the function that initiates and starts the gateway
from mqtt_gateways.gateway.start_gateway import startgateway

# import the class representing the interface *** add your import here ***
from mqtt_gateways.cbus.cbus_interface import cbusInterface

if __name__ == '__main__':
    # launch the gateway *** add your class here ***
    startgateway(cbusInterface, os.path.realpath(__file__))
