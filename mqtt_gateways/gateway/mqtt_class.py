'''
Created on 3 Dec 2017

@author: PierPaolo
'''

import paho.mqtt.client as mqtt

class Client(mqtt.Client):
    
    def __init__(self, client_id="", clean_session=True, userdata=None, protocol=mqtt.MQTTv311, transport="tcp"):
        
        super(Client,self).__init__(self, client_id=client_id, clean_session=clean_session, userdata=userdata, protocol=protocol, transport=transport)
    
    
    def loop(self):
        
        super(Client, self).loop()
        pass
    