'''
Launcher script for the **entry** gateway.
'''

import os.path

# import the function that initiates and starts the gateway
from mqtt_gateways.gateway.start_gateway import startgateway

# import the class representing the interface *** change to your import here ***
from mqtt_gateways.entry.entry_interface import entryInterface

if __name__ == '__main__':
    # launch the gateway *** change to your class here ***
    startgateway(entryInterface, os.path.realpath(__file__))
