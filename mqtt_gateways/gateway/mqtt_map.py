'''
This module represents the bridge between the internal
representation of messages and the MQTT representation.

It defines 2 classes:

- :class:`internalMsg` is the internal representation of a message
- :class:`msgMap` is the conversion engine between the internal
  representation and the MQTT one.

As a reminder, we define the MQTT syntax as follows:

- topic: ``root/function/gateway/location/device/source/type-{C or S}``
- payload: action or status, in plain text or in query string,
  e.g. ``key1=value1&key2=value2&...``
'''

from collections import namedtuple
import paho.mqtt.client as mqtt
import mqtt_gateways.utils.app_properties as app
_logger = app.Properties.getLogger(__name__)

class internalMsg(object):
    '''
    Defines all the characteristics of an internal message.

    Args:
        iscmd (bool): Indicates if the message is a command (True) or a status (False), optional
        function (string): internal representation of function, optional
        gateway (string): internal representation of gateway, optional
        location (string): internal representation of location, optional
        device (string): internal representation of device, optional
        source (string): internal representation of source, optional
        action (string): internal representation of action, optional
        arguments (dictionary of strings): all values should be assumed to be strings, optional

    '''

    def __init__(self, iscmd=False, function=None, gateway=None,
                 location=None, device=None, source=None, action=None, arguments=None):
        _logger = app.Properties.getLogger(__name__)
        self.iscmd = iscmd
        self.function = function
        self.gateway = gateway
        self.location = location
        self.device = device
        self.source = source
        self.action = action
        if arguments is None: self.arguments = {}
        else: self.arguments = arguments

    def copy(self):
        return internalMsg(iscmd=self.iscmd,
                           function=self.function,
                           gateway=self.gateway,
                           location=self.location,
                           device=self.device,
                           source=self.source,
                           action=self.action,
                           arguments=self.arguments.copy())

    def str(self):
        '''Helper function to stringify the class attributes.
        '''
        return ''.join(('cmd=', str(self.iscmd),
                        ';function=', str(self.function),
                        ';gateway=', str(self.gateway),
                        ';location=', str(self.location),
                        ';device=', str(self.device),
                        ';source=', str(self.source),
                        ';action=', str(self.action),
                        ';arguments', str(self.arguments)
                       ))

    def reply(self, response, reason):
        ''' Formats the message to be sent as a reply to an existing command
        
        This method is supposed to be used with an existing message that has been received
        by the interface
        '''
        self.iscmd = False
        self.arguments['response'] = response
        self.arguments['reason'] = reason
        return self

msglist_in = []
msglist_out = []

MappedFields = namedtuple('MappedFields', ('function', 'gateway', 'location',
                                           'device', 'source', 'action',
                                           'argkey', 'argvalue'))

class msgMap(object):
    '''
    Contains the mapping data and the conversion methods.

    Initialises the 5 maps from the argument ``mapdata``,
    which is an object that must be readable line by line with a simple iterator.
    The syntax for ``mapdata`` is that each line has to start with
    one of 6 possible labels (``topic``, ``function``, ``gateway``,
    ``location``, ``device``, ``action``) followed by ``:`` and then the actual data.
    If the label is ``topic`` then the data should be a valid MQTT topic
    string, otherwise the data should be a pair of keywords separated by a
    ``,``, the first being the MQTT representation of the element and the
    second being its internal equivalent.

    Args:
        jsondata (dictionary): contains the map data in the agreed format

    '''

    class tokenMap(object):
        ''' Represents the mapping for a given token or characteristic.
        
        Each instantiation of this class represent the mapping for a given
        token, and contains the type of mapping, the mapping dictionary if
        available, and the methods to convert the keywords back and forth between
        MQTT and internal representation.
        '''
        def __init__(self, maptype, mapdict=None):
            if not mapdict or maptype == 'none':
                self.m2i_dict = None
                self.i2m_dict = None
                self.mapfunc = self._mapnone # by default with no maps
                self.maptype = 'none'
            else:
                self.m2i_dict = mapdict 
                self.i2m_dict = {v: k for k, v in mapdict.iteritems()} # inverse dictionary
                if maptype == 'loose':
                    self.mapfunc = self._maploose
                    self.maptype = maptype
                elif maptype == 'strict':
                    self.mapfunc = self._mapstrict
                    self.maptype = maptype
                else:
                    self.mapfunc = self._mapnone # by default if unknown maptype
                    self.maptype = 'none'

        def _m2i(self, mqtt_token):
            return self.mapfunc(mqtt_token, self.m2i_dict)

        def _i2m(self, internal_token):
            mqtt_token = self.mapfunc(internal_token, self.i2m_dict)
            if mqtt_token is None: return ''
            return mqtt_token

        @staticmethod
        def _mapnone(token, dico):
            return token

        @staticmethod
        def _maploose(token, dico):
            if token is None: return None
            try: return dico[token]
            except KeyError: return token

        @staticmethod
        def _mapstrict(token, dico):
            if token is None: return None
            try: return dico[token]
            except KeyError: raise ValueError(''.join(('not found')))

    def __init__(self, jsondict):
        self._source = app.Properties.name
        try: self._root = jsondict['root']
        except KeyError: raise ValueError('JSON file has no object <root>.')
        try: self.topics = jsondict['topics']
        except KeyError: raise ValueError('JSON file has no object <topics>.')

        maplist = []
        for field in MappedFields._fields:
            try: field_data = jsondict[field]
            except KeyError: raise ValueError(''.join(('JSON file has no object <', field, '>.')))
            try: field_maptype = field_data['maptype']
            except KeyError: raise ValueError(''.join(('<', field, '> object has no child <maptype>.')))
            if field_maptype == 'none':
                field_map = None
            else:
                try: field_map = field_data['map']
                except KeyError: raise ValueError(''.join(('<', field, '> object has no child <map>.')))
            maplist.append(self.tokenMap(field_maptype, field_map))
        self.maps = MappedFields._make(maplist)

        # to access the maps use:
        #    mqtt_token = maps.*field*._m2i(internal_token)
        #    example: mqtt_token = maps.gateway._m2i(internal_token)

    def mqtt2internal(self, mqtt_msg):
        '''
        Converts the MQTT message into an internal one.

        Args:
            mqtt_msg (mqtt.MQTTMessage): a MQTT message.

        Returns:
            internalMsg object: the conversion of the MQTT message

        Raises:
            ValueError: in case of bad MQTT syntax or unrecognised map elements

        '''

        # unpack the topic
        tokens = mqtt_msg.topic.split('/')
        if len(tokens) != 7:
            raise ValueError(''.join(('Topic <', mqtt_msg.topic,
                                      '> has not the right number of tokens.')))
        # unpack the arguments
        # one of them should be 'action' and goes into mqtt_action
        # the other arguments form a dictionary: m_args
        m_args = {}
        if '&' in mqtt_msg.payload: # there is more than one argument in this payload
            mqtt_action = None # just in case there is no 'action' in the list of arguments
            # the payload syntax is a query string 'key1=value1&key2=value2&...'
            for token in mqtt_msg.payload.split('&'):
                argument = token.split('=')
                if len(argument) != 2:
                    raise ValueError(''.join(('Bad format for payload <', mqtt_msg.payload, '>')))
                if argument[0] == 'action':
                    mqtt_action = argument[1]
                else:
                    m_args[argument[0]] = argument[1]
            if not mqtt_action: raise ValueError(''.join(('No action found in payload <', mqtt_msg.payload, '>')))
        else: # this is a straightforward action
            mqtt_action = mqtt_msg.payload

        function = self.maps.function._m2i(tokens[1])
        gateway = self.maps.gateway._m2i(tokens[2])
        location = self.maps.location._m2i(tokens[3])
        device = self.maps.device._m2i(tokens[4])
        source = self.maps.source._m2i(tokens[5])
        action = self.maps.action._m2i(mqtt_action)
        i_args = {}
        for key, value in m_args.iteritems():
            i_args[self.maps.argkey._m2i(key)] = self.maps.argvalue._m2i(value)

        if tokens[6] == 'S': iscmd = False
        elif tokens[6] == 'C': iscmd = True
        else:
            raise ValueError(''.join(('Type in topic <', mqtt_msg.topic, '> not recognised.')))

        return internalMsg(iscmd=iscmd,
                           function=function,
                           gateway=gateway,
                           location=location,
                           device=device,
                           source=source,
                           action=action,
                           arguments=i_args)

    def internal2mqtt(self, internal_msg):
        '''
        Converts an internal message into a MQTT one.

        Args:
            internal_msg (an internalMsg object): the message to convert

        Returns:
            a MQTTMessage object: a full MQTT message where topic syntax is
            ``root/function/gateway/location/device/source/{C or S}`` and
            payload syntax is either a plain action or a query string.

        Raises:
            ValueError: in case a token conversion fails
        '''


        mqtt_function = self.maps.function._i2m(internal_msg.function)
        mqtt_gateway = self.maps.gateway._i2m(internal_msg.gateway)
        mqtt_location = self.maps.location._i2m(internal_msg.location)
        mqtt_device = self.maps.device._i2m(internal_msg.device)
        #mqtt_source = self.maps.source._i2m(internal_msg.source)
        mqtt_action = self.maps.action._i2m(internal_msg.action)
        mqtt_args = {}
        if internal_msg.arguments is not None:
            for key, value in internal_msg.arguments.iteritems():
                mqtt_args[self.maps.argkey._i2m(key)] = self.maps.argvalue._i2m(value)

        # TODO: decide what source to send:
        #        the official source represented by self._source
        # or
        #        whatever comes from the internal message, represented by mqtt_source?

        # Generate topic
        topic = '/'.join((self._root, mqtt_function, mqtt_gateway, mqtt_location,
                          mqtt_device, self._source, 'C' if internal_msg.iscmd else 'S'))

        # Generate payload
        if not mqtt_args: # no arguments, just publish the action text on its own
            payload = mqtt_action
        else: # there are arguments, publish a query string
            stringlist = ['action=', mqtt_action]
            for arg in internal_msg.arguments:
                stringlist.extend(['&', arg, '=', internal_msg.arguments[arg]])
            payload = ''.join(stringlist)

        mqtt_msg = mqtt.MQTTMessage()
        mqtt_msg.topic = topic; mqtt_msg.payload = payload; mqtt_msg.qos = 0; mqtt_msg.retain = False
        return mqtt_msg

import json # TESTING
def test():
    # load a valid map in JSON format
    jsonfilepath = '..\data\cbus_map.json'
    with open(jsonfilepath, 'r') as json_file:
        json_data = json.load(json_file)
    # instantiate a class
    msgmap = msgMap(json_data)
    # printout some members
    function = msgmap.maps.function._m2i('lighting'); print function
    gateway = msgmap.maps.gateway._m2i('whatever'); print gateway
    location = msgmap.maps.location._m2i('office'); print location
    device = msgmap.maps.device._m2i('kitchen_track'); print device
    source = msgmap.maps.source._m2i('me'); print source
    action = msgmap.maps.action._m2i('light_on'); print action
    m_args = {'key1': 'value1'}
    i_args = {}
    for key, value in m_args.iteritems():
        i_args[msgmap.maps.argkey._m2i(key)] = msgmap.maps.argvalue._m2i(value)
    print i_args

if __name__ == '__main__':
    test()
