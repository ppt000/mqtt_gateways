'''
Created on 15 Nov 2017

@author: Paolo
'''

import os.path

# import the function that initiates and starts the gateway
from mqtt_gateways.gateway.start_gateway import startgateway

# import the class representing the interface *** add your import here ***
from mqtt_gateways.dummy.dummy_interface import dummyInterface

if __name__ == '__main__':
    # launch the gateway *** add your class here ***
    startgateway(dummyInterface, os.path.realpath(__file__))