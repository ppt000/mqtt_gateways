'''
Created on 23 May 2017

This module defines a class that acts as a bridge between the internal
representation of messages and the MQTT representation.  The MQTT representation
(or naming convention) has obviously to be the same across all applications
interacting through MQTT.  The purpose of this bridge is to contain all the
processing of MQTT messages in the class and therefore make the application that
uses this module (the gateway) agnostic of any changes in the MQTT syntax or in
the vocabulary used to identify the various concepts (functions, locations,
actions, etc...).  This module should be used by all the gateways, so that any
change in this module will be reflected in all gateways.

This abstraction only works if some basic concepts are respected across the
applications. These are:

    There are 6 parameters that define all types of messages: the function, the
    gateway, the location, the device, the type (command or status) and the action
    (or status); out of these, 4 are related to the destination of the message
    (function, gateway, location, device) and 2 to the content of the message (type
    and action/status). Finally we can add the source parameter to identify the
    sender as it might be useful, making a total of 7 parameters.

    In theory only 3 parameters are absolutely necessary: the type (defines the
    purpose of the message), the location or the device (defines the destination),
    the action or status (defines the content). Those 3 elements constitute a full
    'command' or a full 'reply'. Adding the function and/or the gateway helps a lot
    in filtering the topic, and therefore simplifies the processing of the message
    downstream, but should not be considered compulsory.

We define the MQTT syntax as follows (19Oct2017):
    Topic: root/function/gateway/location/device/source/type-{'C' or 'S'}
    Payload: command or status, in plain text or in query string

TODO: change empty strings assignment with None

@author: PierPaolo
'''

import logging
import paho.mqtt.client as mqtt
import os.path

''' Indices for the list of dictionaries '''
_MQTT2INTERNAL = 0
_INTERNAL2MQTT = 1

''' MQTT default topic name '''
_UNDEFINED = 'undefined'

class internalMsg():
    '''
    Defines all the elements of an internal message.
    '''
    def __init__(self, iscmd = False, function='', gateway = '', location='', device = '', action='', arguments= {}):
        ''' internalMsg constructor
        
        All strings default to '', boolean to False and objects to empty object.
        
        Despite all the defaults, for the message to make sense:
        - the action parameter should be provided,
        - the location or the device should be provided as well.
        
        @param iscmd: boolean to indicate if the message is a command (True) or a status (False)
        @param function: internal representation of function, if any
        @param gateway: internal representation of gateway, if any
        @param location: internal representation of location, if any
        @param device: internal representation of device, if any
        @param action: internal representation of action
        @param arguments: dictionary of arguments, if any
        @errors: none
        '''
        self.iscmd = iscmd
        self.function = function
        self.gateway = gateway
        self.location = location
        self.device = device
        self.action = action
        self.arguments = arguments
        
    def str(self):
        return ''.join(('cmd=',str(self.iscmd),
                        ';function=',self.function,
                        ';gateway=',self.gateway,
                        ';location=',self.location,
                        ';device=',self.device,
                        ';action=',self.action
                        ))

class msgMap():
    '''
    This class is made of:
    
    1 list of topics to subscribe to,
    
    2 lists of internal messages, one for incoming ones and one for outgoing
    ones; these lists could be located in different places, but here is as good
    as any other, even if it does not pertain to the mapping process;
    
    5 maps corresponding to the 5 elements of an internal message that have to
    be translated in MQTT syntax, and back;
    
    2 methods to translate an internal message into an MQTT message and back.
    '''

    def __init__(self, mapdata, fullpath = None):
        '''
        Initialises the 5 maps, which are defined as dictionary pairs, one to
        translate from MQTT to internal representation, the other one for the
        other way around. The initialisation data comes from the argument
        mapdata. The syntax for mapdata is that each line has to start with
        one of 6 possible labels ('topic', 'function', 'gateway',
        'location', 'device', 'action') followed by ':' and then the actual data.
        If the label is 'topic' then the data should be a valid MQTT topic
        string, otherwise the data should be a pair of keywords separated by a
        ',', the first being the MQTT representation of the element and the
        second being its internal equivalent.

        @param mapdata: a StringIO object or similar that can be read line by
        line with a simple iterator and that contains the map data in the agreed
        format.
        
        @errors: none
        '''

        if fullpath is None: # create NullHandler as the root name is not known
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(logging.NullHandler())
        else: # hook up to the 'root' logger
            rootname = os.path.splitext(os.path.basename(fullpath))[0] # first part of the filename, without extension
            self._logger = logging.getLogger(''.join((rootname,".",__name__)))
        
        self.logger.debug(''.join(('Module <',__name__,'> started.')))
        
        self.topics = []
        self.msglist_in=[]
        self.msglist_out = []
        # The maps are pairs of dictionaries: [0] = MQTT -> Internal, [1] = Internal -> MQTT.
        self.functionMap = [{},{}]
        self.gatewayMap = [{},{}] # unused for now
        self.locationMap = [{},{}]
        self.deviceMap = [{},{}]
        self.actionMap = [{},{}]
               
        for line in mapdata.splitlines():
            try:
                tokens = line.rstrip().split(':')
                items = tokens[1].rstrip().split(',')
                if  tokens[0] == 'topic':
                    self.topics.append(items[0])
                elif tokens[0] == 'function':
                    self.functionMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self.functionMap[_INTERNAL2MQTT][items[1]]=items[0]
                elif tokens[0] == 'gateway':
                    self.gatewayMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self.gatewayMap[_INTERNAL2MQTT][items[1]]=items[0]
                elif tokens[0] == 'location':
                    self.locationMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self.locationMap[_INTERNAL2MQTT][items[1]]=items[0]
                elif tokens[0] == 'device':
                    self.deviceMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self.deviceMap[_INTERNAL2MQTT][items[1]]=items[0]
                elif tokens[0] == 'action':
                    self.actionMap[_MQTT2INTERNAL][items[0]]=items[1]
                    self.actionMap[_INTERNAL2MQTT][items[1]]=items[0]
                else:
                    self.logger.info(''.join(('Unrecognised token in line <',line,'> in map data, skip the line.')))
            except IndexError:
                self.logger.info(''.join(('Incorrect line <',line,'> in map data, skip the line.')))
        
    def MQTT2Internal(self, mqttMsg):
        '''
        Translates the MQTT message and returns an internal one. Raises
        ValueError in the various cases where the MQTT message is not a valid
        one because of bad syntax or unrecognised map elements.
        
        NOTE: the assignment relating to the payload all go through an str()
        function call just in case they are considered numbers, but I am not
        sure if it is really necessary.
        
        @param mqttMsg: a fully formed MQTT message, valid for this gateway,
        i.e. in the form root/function/gateway/location/device/source/'C'or'S'
        @return: a valid internalMsg message
        '''
        tokens = mqttMsg.topic.split('/')
        if len(tokens) != 7:
            raise ValueError(''.join(('Topic <', mqttMsg.topic,'> has not the right number of tokens.')))
        
        # Check here function or gateway, but they are probably filtered by the topic subscription
        
        if tokens[6] == 'S': iscmd = False
        elif tokens[6] == 'C': iscmd = True
        else:
            raise ValueError(''.join(('Type in topic <', mqttMsg.topic,'> not recognised.')))

        try: location = self.locationMap[_MQTT2INTERNAL][tokens[3]]
        except KeyError: location = ''
        try: device = self.deviceMap[_MQTT2INTERNAL][tokens[4]]
        except KeyError: device = ''
        if (location == '') and (device == ''):
            raise ValueError(''.join(('MQTT location <', tokens[3],'> and device <', tokens[4],'> unrecognised.')))

        try: function = self.functionMap[_MQTT2INTERNAL][tokens[1]]
        except KeyError: function = ''

        try: gateway = self.gatewayMap[_MQTT2INTERNAL][tokens[2]]
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
            action = self.actionMap[_MQTT2INTERNAL][mqtt_action]
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
        Translates an internal message msg and returns an MQTT one.
        
        Raises ValueError in those 2 'blocking' cases:
        - both location and device are not found,
        - the action can not be translated.
        
        In other cases of unfound translations, the constant _UNDEFINED is used
        in the topic.
        
        The tests on iMsg members are sequenced so that legitimate '' or
        _UNDEFINED values are tested first and do not generate log, then the
        try/except search in the dictionary uncovers the cases where a 'proper'
        string has not been found, which deserves a log just in case there is a
        typo in one of the maps. It is a bit convoluted, so be it.
        
        syntax reminder: root/function/gateway/location/device/source/'C'or'S'
        
        @param msg: an internalMsg object
        @return: an MQTTMessage object with syntax:
        root/function/gateway/location/device/source/'C'or'S'
        '''
        if iMsg.location == '' or iMsg.location == _UNDEFINED:
            mqtt_location = _UNDEFINED
            locfound = False
        else:
            try:
                mqtt_location = self.locationMap[_INTERNAL2MQTT][iMsg.location]
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
                mqtt_device = self.deviceMap[_INTERNAL2MQTT][iMsg.device]
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
                mqtt_function = self.functionMap[_INTERNAL2MQTT][iMsg.function]
            except KeyError:
                mqtt_function = _UNDEFINED
                self.logger.info(''.join(('Function <',iMsg.function,'> not recognised.')))

        if iMsg.gateway == '' or iMsg.gateway == _UNDEFINED:
            mqtt_gateway = _UNDEFINED
        else:
            try:
                mqtt_gateway = self.gatewayMap[_INTERNAL2MQTT][iMsg.gateway]
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
            mqtt_action = self.actionMap[_INTERNAL2MQTT][iMsg.action]
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
