'''Launcher for the MusicCast gateway.'''

import os.path

# import the function that initiates and starts the gateway
#from mqtt_gateways.gateway.start_gateway import startgateway
from mqtt_gateways.gateway.start_gateway_test import startgateway # TEST!!!!!

# import the class representing the interface *** add your import here ***
from mqtt_gateways.musiccast.musiccast_interface import musiccastInterface

if __name__ == '__main__':
    # launch the gateway *** add your class here ***
    startgateway(musiccastInterface, os.path.realpath(__file__))
