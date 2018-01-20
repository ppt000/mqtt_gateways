'''
Launcher script for the **dummy** gateway.

Use this as a template.
If the name conventions have been respected, just change all occurrences of
``dummy`` into the name of your gateway.
'''

import os.path

# import the function that initiates and starts the gateway
from mqtt_gateways.gateway.start_gateway import startgateway

# import the class representing the interface *** change to your import here ***
from mqtt_gateways.dummy.dummy_interface import DummyInterface

if __name__ == '__main__':
    # launch the gateway *** change to your class here ***
    startgateway(DummyInterface, os.path.realpath(__file__))
