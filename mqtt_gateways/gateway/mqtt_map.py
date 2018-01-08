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
'''

import logging
import paho.mqtt.client as mqtt
import os.path

''' Indices for the list of dictionaries '''
_MQTT2INTERNAL = 0
_INTERNAL2MQTT = 1

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
        action (string): internal representation of action, optional
        arguments (dictionary of strings): all values should be assumed to be strings, even if numeric, optional
    
    '''

    def __init__(self, iscmd = False, function='', gateway = '',
                 location='', device = '', action='', arguments= {}):

        self.iscmd = iscmd
        self.function = function
        self.gateway = gateway
        self.location = location
        self.device = device
        self.action = action
        self.arguments = arguments
        
    def str(self):
        '''Helper function to stringify the class attributes.
        '''
        return ''.join(('cmd=',str(self.iscmd),
                        ';function=',self.function,
                        ';gateway=',self.gateway,
                        ';location=',self.location,
                        ';device=',self.device,
                        ';action=',self.action
                        ))

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
        fullpath (string): the full path of the application root

    .. TODO: all attributes are actually private, change their name

    '''

    def __init__(self, mapdata, fullpath = None):
        if fullpath is None: # create NullHandler as the root name is not known
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())
        else: # hook up to the 'root' logger
            rootname = os.path.splitext(os.path.basename(fullpath))[0] # first part of the filename, without extension
            self._logger = logging.getLogger(''.join((rootname,".",__name__)))
        
        self.logger.debug(''.join(('Module <',__name__,'> started.')))
        
        self.topics = []
        '''list of strings: the list of topics to subscribe to'''
        self.msglist_in=[]
        '''list of internalMsg objects: list of incoming messages '''
        self.msglist_out = []
        '''list of internalMsg objects: list of outgoing messages '''
        # The maps are pairs of dictionaries: [0] = MQTT -> Internal, [1] = Internal -> MQTT.
        self._functionMap = [{},{}]
        '''pair of dictionaries as in [{},{}]: contains the mapping data for the **function** characteristic
                the first dictionary relate MQTT keywords to internal keywords;
                the second one is the inverse.'''
        self._gatewayMap = [{},{}] # unused for now
        '''same for the **gateway** characteristic'''
        self._locationMap = [{},{}]
        '''same for the **location** characteristic'''
        self._deviceMap = [{},{}]
        '''same for the **device** characteristic'''
        self._actionMap = [{},{}]
        '''same for the **action** characteristic'''
               
        for line in mapdata.splitlines():
            try:
                tokens = line.rstrip().split(':')
                items = tokens[1].rstrip().split(',')
                if  tokens[0] == 'topic':
                    self.topics.append(items[0])
                elif tokens[0] == 'function':
                    self._functionMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self._functionMap[_INTERNAL2MQTT][items[1]]=items[0]
                elif tokens[0] == 'gateway':
                    self._gatewayMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self._gatewayMap[_INTERNAL2MQTT][items[1]]=items[0]
                elif tokens[0] == 'location':
                    self._locationMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self._locationMap[_INTERNAL2MQTT][items[1]]=items[0]
                elif tokens[0] == 'device':
                    self._deviceMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self._deviceMap[_INTERNAL2MQTT][items[1]]=items[0]
                elif tokens[0] == 'action':
                    self._actionMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self._actionMap[_INTERNAL2MQTT][items[1]]=items[0]
                else:
                    self.logger.info(''.join(('Unrecognised token in line <',line,'> in map data, skip the line.')))
            except IndexError:
                self.logger.info(''.join(('Incorrect line <',line,'> in map data, skip the line.')))
        
    def MQTT2Internal(self, mqttMsg):
        '''
        Converts the MQTT message into an internal one.

        Args:
            mqttMsg (string): a fully formed MQTT message, valid for this gateway,
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
        tokens = mqttMsg.topic.split('/')
        if len(tokens) != 7:
            raise ValueError(''.join(('Topic <', mqttMsg.topic,'> has not the right number of tokens.')))
        
        # Check here function or gateway, but they are probably filtered by the topic subscription
        
        if tokens[6] == 'S': iscmd = False
        elif tokens[6] == 'C': iscmd = True
        else:
            raise ValueError(''.join(('Type in topic <', mqttMsg.topic,'> not recognised.')))

        try: location = self._locationMap[_MQTT2INTERNAL][tokens[3]]
        except KeyError: location = ''
        try: device = self._deviceMap[_MQTT2INTERNAL][tokens[4]]
        except KeyError: device = ''
        if (location == '') and (device == ''):
            raise ValueError(''.join(('MQTT location <', tokens[3],'> and device <', tokens[4],'> unrecognised.')))

        try: function = self._functionMap[_MQTT2INTERNAL][tokens[1]]
        except KeyError: function = ''

        try: gateway = self._gatewayMap[_MQTT2INTERNAL][tokens[2]]
        except KeyError: gateway = ''
        
        args = {}
        # the payload syntax is a query string 'key1=value1&key2=value2&...' if there is more than one argument
        if '&' in mqttMsg.payload: # there is more than one argument in this payload
            mqtt_action = '' # just in case there is no 'action' in the list of arguments
            for token in mqttMsg.payload.split('&'):
                argument = token.split('=')
                if len(argument) != 2:
                    raise ValueError(''.join(('Bad format for payload <', mqttMsg.payload,'>')))
                if argument[0]=='action':
                    mqtt_action = str(argument[1])
                else:
                    args[argument[0]] = str(argument[1])
        else: # this is a straightforward action 
            mqtt_action = str(mqttMsg.payload)
        try:
            action = self._actionMap[_MQTT2INTERNAL][mqtt_action]
        except KeyError:
            raise ValueError(''.join(('MQTT action <',mqtt_action,'> unrecognised.')))
        
        return internalMsg(iscmd= iscmd,
                           function= function,
                           gateway = gateway,
                           location= location,
                           action= action,
                           device= device,
                           arguments= args)

    def Internal2MQTT(self, iMsg):
        '''
        Converts an internal message into a MQTT one.
        
        In cases where a characteristic is *empty* (i.e. it is ``''`` or
        equal to an ``_UNDEFINED`` constant) then ``_UNDEFINED``
        is used in the MQTT message.
        In all cases of unsuccesful conversion of an optional characteristic
        (i.e. there is a string in the field not equal to ``_UNDEFINED``),
        then ``_UNDEFINED`` is also used in the MQTT message, but the 
        conversion failure is logged just in case there is a
        typo in one of the maps.
        
        Args:
            iMsg (an :class:internalMsg object): the message to convert
        
        Returns:
            a MQTTMessage object: syntax is ``root/function/gateway/location/device/source/{C or S}``
            
        Raises:
            ValueError: in case both location and device are not found, or
                the action can not be converted.
        '''
        if iMsg.location == '' or iMsg.location == _UNDEFINED:
            mqtt_location = _UNDEFINED
            locfound = False
        else:
            try:
                mqtt_location = self._locationMap[_INTERNAL2MQTT][iMsg.location]
                locfound = True
            except KeyError:
                mqtt_location = _UNDEFINED
                locfound = False
                self.logger.info(''.join(('Location <',iMsg.location,'> unrecognised.')))

        if iMsg.device == '' or iMsg.device == _UNDEFINED:
            mqtt_device = _UNDEFINED
            devfound = False
        else:
            try:
                mqtt_device = self._deviceMap[_INTERNAL2MQTT][iMsg.device]
                devfound = True
            except KeyError:
                mqtt_device = _UNDEFINED
                devfound = False
                self.logger.info(''.join(('Device <',iMsg.device,'> unrecognised.')))

        if (not locfound) and (not devfound):
            raise ValueError(''.join(('Both location <',str(iMsg.location),'> and device <',str(iMsg.device),'> are unusable.')))
        
        if iMsg.function == '' or iMsg.function == _UNDEFINED:
            mqtt_function = _UNDEFINED
        else:
            try:
                mqtt_function = self._functionMap[_INTERNAL2MQTT][iMsg.function]
            except KeyError:
                mqtt_function = _UNDEFINED
                self.logger.info(''.join(('Function <',iMsg.function,'> not recognised.')))

        if iMsg.gateway == '' or iMsg.gateway == _UNDEFINED:
            mqtt_gateway = _UNDEFINED
        else:
            try:
                mqtt_gateway = self._gatewayMap[_INTERNAL2MQTT][iMsg.gateway]
            except KeyError:
                mqtt_gateway = _UNDEFINED
                self.logger.info(''.join(('Gateway <',iMsg.gateway,'> not recognised.')))
                
        # Include here treatment to generate topic
        topic = ''.join(('oer/',
                         mqtt_function,'/',
                         mqtt_gateway,'/',
                         mqtt_location,'/',
                         mqtt_device,'/',
                         'cbus/',
                         'C' if iMsg.iscmd else 'S'))

        try:
            mqtt_action = self._actionMap[_INTERNAL2MQTT][iMsg.action]
        except KeyError:
            raise ValueError(''.join(('Action <',iMsg.action,'> not recognised.')))
        
        # Generate payload
        if len(iMsg.arguments) == 0: # no arguments, just publish the action text on its own
            payload = mqtt_action
        else: # there are arguments, publish a query string
            stringlist = ['action=',mqtt_action]
            for arg in iMsg.arguments:
                stringlist.extend(['&',arg,'=',iMsg.arguments[arg]])
            payload = ''.join(stringlist)

        mqttMsg = mqtt.MQTTMessage()
        mqttMsg.topic = topic; mqttMsg.payload = payload; mqttMsg.qos = 0; mqttMsg.retain = False;
        return mqttMsg
