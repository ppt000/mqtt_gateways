'''Starter module for the C-Bus gateway.'''

import os.path
import mqtt_gateways.utils.app_properties as app
app.Properties(os.path.realpath(__file__))

# import the module that initiates and starts the gateway
import mqtt_gateways.gateway.start_gateway as start_g

# import the module representing the interface *** add your import here ***
import mqtt_gateways.cbus.cbus_interface as cbus_i

if __name__ == '__main__':
    # launch the gateway *** add your class here ***
    start_g.startgateway(cbus_i.cbusInterface)
