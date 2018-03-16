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

..
    TODO: change empty strings assignment with None
    TODO: review mapping strategy in case of item not found in map
'''


import paho.mqtt.client as mqtt

from mqtt_gateways.utils.app_helper import appHelper

_logger = appHelper.getLogger(__name__)

_MQTT2INTERNAL = 0; _INTERNAL2MQTT = 1
''' Indices for the list of dictionaries'''

_UNDEFINED = 'undefined'
'''string: default name for an empty characteristic'''

class internalMsg(object):
    '''
    Defines all the characteristics of an internal message.

    Despite all the defaults, for the message to make sense:

    - the action parameter should be provided,
    - the location or the device should be provided as well.

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
    # TODO: decide if None members are accepted (instead of an empty string)
    def __init__(self, iscmd=False, function='', gateway='',
                 location='', device='', source='', action='', arguments=None):
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
                           arguments=self.arguments.copy()) # TODO: is a copy enough?

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
        mapdata (a StringIO object or similar): contains the map data in the agreed format
        root (string): the word to be used as first token in all message topics

    '''

    def __init__(self, mapdata, root):
        self._root = root
        self._source = appHelper.app_name

        _logger.debug(''.join(('Module <', __name__, '> started.')))

        self.topics = []
        '''list of strings: the list of topics to subscribe to'''
        # The maps are pairs of dictionaries: [0] = MQTT -> Internal, [1] = Internal -> MQTT.
        self._function_map = [{}, {}]
        '''pair of dictionaries: contains the mapping data for the **function** characteristic.
                the first dictionary relate MQTT keywords to internal keywords;
                the second one is the inverse.'''
        self._gateway_map = [{}, {}]
        '''same for the **gateway** characteristic'''
        self._location_map = [{}, {}]
        '''same for the **location** characteristic'''
        self._device_map = [{}, {}]
        '''same for the **device** characteristic'''
        self._action_map = [{}, {}]
        '''same for the **action** characteristic'''

        for line in mapdata.splitlines():
            try:
                tokens = [item.strip() for item in line.split(':')]
                items = [item.strip() for item in tokens[1].split(',')]
                if  tokens[0] == 'topic':
                    self.topics.append(items[0])
                    _logger.debug(''.join(('Added topic ',items[0],'.')))
                elif tokens[0] == 'function':
                    self._function_map[_MQTT2INTERNAL][items[0]] = items[1]
                    self._function_map[_INTERNAL2MQTT][items[1]] = items[0]
                    _logger.debug(''.join(('Added function: ',items[0],'=',items[1],'.')))
                elif tokens[0] == 'gateway':
                    self._gateway_map[_MQTT2INTERNAL][items[0]] = items[1]
                    self._gateway_map[_INTERNAL2MQTT][items[1]] = items[0]
                    _logger.debug(''.join(('Added gateway: ',items[0],'=',items[1],'.')))
                elif tokens[0] == 'location':
                    self._location_map[_MQTT2INTERNAL][items[0]] = items[1]
                    self._location_map[_INTERNAL2MQTT][items[1]] = items[0]
                    _logger.debug(''.join(('Added location: ',items[0],'=',items[1],'.')))
                elif tokens[0] == 'device':
                    self._device_map[_MQTT2INTERNAL][items[0]] = items[1]
                    self._device_map[_INTERNAL2MQTT][items[1]] = items[0]
                    _logger.debug(''.join(('Added device: ',items[0],'=',items[1],'.')))
                elif tokens[0] == 'action':
                    self._action_map[_MQTT2INTERNAL][items[0]] = items[1]
                    self._action_map[_INTERNAL2MQTT][items[1]] = items[0]
                    _logger.debug(''.join(('Added action: ',items[0],'=',items[1],'.')))
                else:
                    _logger.info(''.join(('Unrecognised token in line <', line,
                                              '> in map data, skip the line.')))
            except IndexError:
                _logger.info(''.join(('Incorrect line <', line,
                                          '> in map data, skip the line.')))


    def mqtt2internal(self, mqtt_msg):
        '''
        Converts the MQTT message into an internal one.

        Args:
            mqtt_msg (string): a fully formed MQTT message, valid for this gateway,
                i.e. in the form ``root/function/gateway/location/device/source/type{C or S}``

        Returns:
            internalMsg object: the conversion of the MQTT message

        Raises:
            ValueError: in case of bad MQTT syntax or unrecognised map elements

        ..
            TODO: the assignments relating to the payload all go through an str()
            function call just in case they are considered numbers, but I am not
            sure if it is really necessary.

        '''
        tokens = mqtt_msg.topic.split('/')
        if len(tokens) != 7:
            raise ValueError(''.join(('Topic <', mqtt_msg.topic,
                                      '> has not the right number of tokens.')))

        # One can check here the function or gateway, or filter them through the topic subscription

        if tokens[6] == 'S': iscmd = False
        elif tokens[6] == 'C': iscmd = True
        else:
            raise ValueError(''.join(('Type in topic <', mqtt_msg.topic, '> not recognised.')))

        try: location = self._location_map[_MQTT2INTERNAL][tokens[3]]
        except KeyError: location = ''
        try: device = self._device_map[_MQTT2INTERNAL][tokens[4]]
        except KeyError: device = ''
        if (location == '') and (device == ''):
            raise ValueError(''.join(('MQTT location <', tokens[3], '> and device <',
                                      tokens[4], '> unrecognised.')))

        try: function = self._function_map[_MQTT2INTERNAL][tokens[1]]
        except KeyError: function = ''

        # here we use the actual incoming string if it is not found in the map
        try: gateway = self._gateway_map[_MQTT2INTERNAL][tokens[2]]
        except KeyError: gateway = tokens[2]

        args = {}
        # the payload syntax is a query string 'key1=value1&key2=value2&...' if...
        # ...there is more than one argument
        if '&' in mqtt_msg.payload: # there is more than one argument in this payload
            mqtt_action = '' # just in case there is no 'action' in the list of arguments
            for token in mqtt_msg.payload.split('&'):
                argument = token.split('=')
                if len(argument) != 2:
                    raise ValueError(''.join(('Bad format for payload <', mqtt_msg.payload, '>')))
                if argument[0] == 'action':
                    mqtt_action = str(argument[1])
                else:
                    args[argument[0]] = str(argument[1])
        else: # this is a straightforward action
            mqtt_action = str(mqtt_msg.payload)
        try:
            action = self._action_map[_MQTT2INTERNAL][mqtt_action]
        except KeyError:
            raise ValueError(''.join(('MQTT action <', mqtt_action, '> unrecognised.')))

        return internalMsg(iscmd=iscmd,
                           function=function,
                           gateway=gateway,
                           location=location,
                           action=action,
                           device=device,
                           arguments=args)

    def internal2mqtt(self, internal_msg):
        '''
        Converts an internal message into a MQTT one.

        In cases where a characteristic is *empty* (i.e. it is ``''`` or
        equal to an ``_UNDEFINED`` constant) then ``_UNDEFINED``
        is used in the MQTT message.
        In all cases of unsuccessful conversion of an optional characteristic
        (i.e. there is a string in the field not equal to ``_UNDEFINED``),
        then ``_UNDEFINED`` is also used in the MQTT message, but the
        conversion failure is logged just in case there is a
        typo in one of the maps.

        Args:
            internal_msg (an internalMsg object): the message to convert

        Returns:
            a MQTTMessage object: a full MQTT message where topic syntax is
            ``root/function/gateway/location/device/source/{C or S}`` and
            payload syntax is either a plain action or a query string.

        Raises:
            ValueError: in case both location and device are not found, or
                the action can not be converted.
        '''
        if internal_msg.location == '' or internal_msg.location == _UNDEFINED:
            mqtt_location = _UNDEFINED
            locfound = False
        else:
            try:
                mqtt_location = self._location_map[_INTERNAL2MQTT][internal_msg.location]
                locfound = True
            except KeyError:
                mqtt_location = _UNDEFINED
                locfound = False
                _logger.info(''.join(('Location <', internal_msg.location, '> unrecognised.')))

        if internal_msg.device == '' or internal_msg.device == _UNDEFINED:
            mqtt_device = _UNDEFINED
            devfound = False
        else:
            try:
                mqtt_device = self._device_map[_INTERNAL2MQTT][internal_msg.device]
                devfound = True
            except KeyError:
                mqtt_device = _UNDEFINED
                devfound = False
                _logger.info(''.join(('Device <', internal_msg.device, '> unrecognised.')))

        if (not locfound) and (not devfound):
            raise ValueError(''.join(('Both location <', str(internal_msg.location), '> and device <',
                                      str(internal_msg.device), '> are unusable.')))

        if internal_msg.function == '' or internal_msg.function == _UNDEFINED:
            mqtt_function = _UNDEFINED
        else:
            try:
                mqtt_function = self._function_map[_INTERNAL2MQTT][internal_msg.function]
            except KeyError:
                mqtt_function = _UNDEFINED
                _logger.info(''.join(('Function <', internal_msg.function, '> not recognised.')))

        # for the gateway, we use the internal string as the mqtt token if it is not found in the map
        if internal_msg.gateway == '' or internal_msg.gateway == _UNDEFINED:
            mqtt_gateway = _UNDEFINED
        else:
            try:
                mqtt_gateway = self._gateway_map[_INTERNAL2MQTT][internal_msg.gateway]
            except KeyError:
                mqtt_gateway = internal_msg.gateway
                _logger.info(''.join(('Gateway <', internal_msg.gateway, '> not recognised.')))

        # Include here treatment to generate topic
        topic = '/'.join((self._root, mqtt_function, mqtt_gateway, mqtt_location,
                          mqtt_device, self._source, 'C' if internal_msg.iscmd else 'S'))
        try:
            mqtt_action = self._action_map[_INTERNAL2MQTT][internal_msg.action]
        except KeyError:
            raise ValueError(''.join(('Action <', internal_msg.action, '> not recognised.')))

        # Generate payload
        if not internal_msg.arguments: # no arguments, just publish the action text on its own
            payload = mqtt_action
        else: # there are arguments, publish a query string
            stringlist = ['action=', mqtt_action]
            for arg in internal_msg.arguments:
                stringlist.extend(['&', arg, '=', internal_msg.arguments[arg]])
            payload = ''.join(stringlist)

        mqtt_msg = mqtt.MQTTMessage()
        mqtt_msg.topic = topic; mqtt_msg.payload = payload; mqtt_msg.qos = 0; mqtt_msg.retain = False
        return mqtt_msg
