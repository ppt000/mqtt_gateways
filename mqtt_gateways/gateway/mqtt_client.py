'''
This is a child class of the mqtt client in the paho library.

It includes the management of reconnection when using only the loop() method
(which is not included natively in the paho library) as well as overrides the
reconnect method to be able to reconnect in case the broker has gone down and does
not allow for 'persistent' connection (in which case the original reconnect()
method does not work because it assumes that the connect method has been called before).
'''

import mqtt_gateways.utils.app_properties as app
import mqtt_gateways.utils.throttled_exception as thrx
import paho.mqtt.client as mqtt

_logger = app.Properties.getLogger(__name__)

_mqtt_rc = {
    0: 'Connection successful',
    1: 'Connection refused - incorrect protocol version',
    2: 'Connection refused - invalid client identifier',
    3: 'Connection refused - server unavailable',
    4: 'Connection refused - bad username or password',
    5: 'Connection refused - not authorised'
    # 6-255: Currently unused.
    }

_THROTTLELAG = 600  #int: lag in seconds to throttle the error logs.
#_IN = 0; _OUT = 1 # indices for the message lists

# pylint: disable=too-few-public-methods
class ConnectionError(thrx.ThrottledException):
    ''' Base Exception class for this module, inherits from ThrottledException'''
    def __init__(self, msg=None):
        super(ConnectionError, self).__init__(msg, throttlelag=_THROTTLELAG, module_name=__name__)
# pylint: enable=too-few-public-methods

class Client(mqtt.Client):
    ''' docstring '''
    def __init__(self, host='localhost', port=1883, keepalive=60, client_id='', userdata=None):
        self._host = host
        self._port = port
        self._keepalive = keepalive
        self._client_id = client_id
        super(Client, self).__init__(client_id=client_id, clean_session=True,
                                         userdata=userdata, protocol=mqtt.MQTTv311, transport='tcp')
        super(Client, self).on_connect = self.on_connect
        super(Client, self).on_disconnect = self.on_disconnect
        super(Client, self).on_message = self.on_message
        try:
            self.connect(host=self._host,port=self._port,keepalive=self._keepalive)
        except (OSError, IOError) as err:
            # the loop will try to reconnect anyway so just log an info that might help diagnostics
            _logger.info('Client can''t connect to broker with error ', repr(err))

    def reconnect(self):
        ''' '''
        try: super(Client, self).reconnect()
        except (OSError, IOError): # still no connection
            try: # the broker might have gone down and the connections are not persistent
                super(Client, self).connect(self._host, self._port, self._keepalive)
            except (OSError, IOError): raise

    #===============================================================================
    # The MQTT callbacks.
    # In all the MQTT callbacks, the userdata is expected to be a dictionary of the
    # following elements:
    #   - the root logger
    #   - mqttparams, the dict of MQTT parameters, including the msg_map and the msg_list
    #   - the gateway interface instance
    #===============================================================================

    # pylint: disable=unused-argument

    def on_connect(self, client, userdata, flags, return_code):
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
        #logger = userdata['logger']
        _logger.info(''.join(('Connected with result code <',
                             str(return_code), '>: ', _mqtt_rc[return_code])))
        userdata['connected'] = True
        msg_map = userdata['msgmap']
        for topic in msg_map.topics:
            try: client.subscribe(topic)
            except ValueError:
                _logger.info(''.join(('Topic <', topic, '> cannot be subscribed to.')))
                continue
            _logger.debug(''.join(('Subscribing to topic <', topic, '>.')))
    
    def on_disconnect(self, client, userdata, return_code):
        '''
        The MQTT callback when a disconnection occurs.

        It sets to False the key ``connected`` of the :data:`mqttparams`
        dictionary and initiates the relevant variables to start the active monitoring
        of the reconnection attempts.
        '''
        #logger = userdata['logger']
        _logger.info(''.join(('Client has disconnected with code <', str(return_code), '>.')))
        userdata['connected'] = False

    def on_message(self, client, userdata, mqtt_msg):
        '''
        The MQTT callback when a message is received from the MQTT broker.

        The message (topic and payload) is mapped into its internal representation and
        then appended to the incoming message list for the gateway interface to
        execute it later.
        '''
        #logger = userdata['logger']
        _logger.debug(''.join(('MsgRcvd-Topic:<', mqtt_msg.topic, '>-Payload:<', str(mqtt_msg.payload), '>.')))
        msg_map = userdata['msgmap']
        try: internal_msg = msg_map.mqtt2internal(mqtt_msg)
        except ValueError as err:
            _logger.info(str(err))
            return
        userdata['msglist_in'].append(internal_msg)

    # pylint: enable=unused-argument
