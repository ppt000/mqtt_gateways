'''
This is a child class of the MQTT client in the paho library.

It includes the management of reconnection when using only the loop() method
(which is not included natively in the paho library) as well as overrides the
reconnect method to be able to reconnect in case the broker has gone down and does
not allow for 'persistent' connection (in which case the original reconnect()
method does not work because it assumes that the connect method has been called before).
'''

import time
import paho.mqtt.client as mqtt
import mqtt_gateways.utils.app_properties as app
import mqtt_gateways.utils.throttled_exception as thrx

_logger = app.Properties.get_logger(__name__)

_MQTT_RC = {
    0: 'Connection successful',
    1: 'Connection refused - incorrect protocol version',
    2: 'Connection refused - invalid client identifier',
    3: 'Connection refused - server unavailable',
    4: 'Connection refused - bad username or password',
    5: 'Connection refused - not authorised'
       # 6-255: Currently unused.
    }

_THROTTLELAG = 600  # lag in seconds to throttle the error logs.
_RACELAG = 0.1 # lag in seconds to wait before testing the connection state

# pylint: disable=too-few-public-methods
class connectionError(thrx.ThrottledException):
    ''' Base Exception class for this module, inherits from ThrottledException'''
    def __init__(self, msg=None):
        super(connectionError, self).__init__(msg, throttlelag=_THROTTLELAG, module_name=__name__)
# pylint: enable=too-few-public-methods


#===============================================================================
# The MQTT callbacks.
# In all the MQTT callbacks, the userdata is expected to be a dictionary of the
# following elements:
#   - the root logger
#   - mqttparams, the dict of MQTT parameters, including the msg_map and the msg_list
#   - the gateway interface instance
#===============================================================================

# pylint: disable=unused-argument
def on_connect(client, userdata, flags, return_code):
    '''
    The MQTT callback when a connection is established.

    It sets to True the key ``connected`` of the :data:`localdata`
    dictionary and subscribes to the topics available in the message map.
    Note: the argument flags is a dictionary with at least the item
    'session present' (with a space!) in it which will be 1 if the session
    is indeed already present.  In our case it should never happen because
    the broker should have persistence turned off and the client should
    always connect asking for a clean session.
    '''
    _logger.info(''.join(('Connected with result code <',
                          str(return_code), '>: ', _MQTT_RC[return_code])))
    userdata['connected'] = True
    msg_map = userdata['msgmap']
    for topic in msg_map.topics:
        try: client.subscribe(topic)
        except ValueError:
            _logger.info(''.join(('Topic <', topic, '> cannot be subscribed to.')))
            continue
        _logger.debug(''.join(('Subscribing to topic <', topic, '>.')))

def on_disconnect(client, userdata, return_code):
    '''
    The MQTT callback when a disconnection occurs.

    It sets to False the key ``connected`` of the :data:`mqttparams`
    dictionary and initiates the relevant variables to start the active monitoring
    of the reconnection attempts.
    '''
    _logger.info(''.join(('Client has disconnected with code <', str(return_code), '>.')))
    userdata['connected'] = False

def on_message(client, userdata, mqtt_msg):
    '''
    The MQTT callback when a message is received from the MQTT broker.

    The message (topic and payload) is mapped into its internal representation and
    then appended to the incoming message list for the gateway interface to
    execute it later.
    '''
    _logger.debug(''.join(('MQTTMsgRcvd-Topic:<', mqtt_msg.topic,
                           '>-Payload:<', str(mqtt_msg.payload), '>.')))
    msg_map = userdata['msgmap']
    try: internal_msg = msg_map.mqtt2internal(mqtt_msg)
    except ValueError as err:
        _logger.info(str(err))
        return
    userdata['msglist_in'].push(internal_msg)

# pylint: enable=unused-argument

class mgClient(mqtt.Client):
    ''' docstring - mg as in mqtt_gateways

    The MQTT paho library sets quite a few attributes in the Client class.  They all start
    with an underscore.  Be careful not to overwrite them.
    '''
    def __init__(self, host='localhost', port=1883, keepalive=60, client_id='', userdata=None):
        self.host = host
        self.port = port
        self.keepalive = keepalive
        self.client_id = client_id
        self.userdata = userdata
        self.userdata['connected'] = False # connection state, to be set in the callbacks
        self.connect_time = 0 # time of connection request
        self.lag_test = self.lag_end # this is a 'function attribute', like a method.

        super(mgClient, self).__init__(client_id=client_id, clean_session=True,
                                       userdata=userdata, protocol=mqtt.MQTTv311, transport='tcp')
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_message = on_message
        self.connect()
        return

    def lag_end(self):
        ''' Used to inhibit the connection test during the lag.
        
        There is the possibility of a race condition when testing the connection state.  This
        happens if the **on_connect** call-back is not called fast enough and the main loop
        tests the connection state before that call-back has set the state to *connected*.  As a
        consequence the automatic reconnection feature gets triggered, and the connection process
        gets jammed with the broker.  That's why we need to leave a little lag before testing the
        connection.
        '''
        if time.time() - self.connect_time > _RACELAG:
            self.lag_test = lambda: True
            return True
        return False

    def connect(self):
        try:
            super(mgClient, self).connect(self.host, self.port, self.keepalive)
            self.connect_time = time.time()
            self.lag_test = self.lag_end
        except (OSError, IOError) as err:
            # the loop will try to reconnect anyway so just log an info
            _logger.info('Client can''t connect to broker with error ', repr(err))
        return

    def reconnect(self):
        super(mgClient, self).reconnect()
        self.connect_time = time.time()
        self.lag_test = self.lag_end

    def loop(self, timeout):
        ''' Implements automatic reconnection on top of the parent loop method.
        
        The use of the method/attribute **lag_test** is to avoid having to test the lag forever
        once the connection is established.  Once the lag is finished, this method gets replaced
        by a simple lambda, which hopefully is much faster than calling the time library and
        doing a comparison.  Probably a case of premature optimisation though...
        '''
        # Deal with the situation where MQTT is not connected as the loop() method does not automatically reconnect.
#        if now - self.connect_time > 0.1 and not self.userdata['connected']:
        if self.lag_test():
            if not self.userdata['connected']:
                # the MQTT broker is not connected
                try: self.reconnect() # try to reconnect
                except (OSError, IOError): # still no connection
                    try: raise connectionError('Client can''t reconnect to broker.') # throttled log
                    except connectionError as err: # not very elegant but works
                        if err.trigger: _logger.error(err.report)
            
        super(mgClient, self).loop(timeout)
