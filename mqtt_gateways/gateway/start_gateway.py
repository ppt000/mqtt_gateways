'''
Defines the function that starts the gateway and the 3 MQTT callbacks.

This module exposes the main entry points for the framework: the gateway
interface class, which is received as an argument by the main function
:func:`startgateway`, and is instantiated after all the initialisations are
done. Note that at the moment of instantiation, the configuration file should be
loaded, so anything that is written inside the ``[INTERFACE]`` section will be passed
on to the class constructor.  This way custom configuration settings can be passed
on to the gateway interface.

.. TODO
    Move the mqtt callbacks in a different module inside a class?
    Remove definitively all commented lines relating to reconnection attempts
'''

import logging
#import time
import os.path
import sys

import paho.mqtt.client as mqtt

from mqtt_gateways.utils.load_config import loadconfig
from mqtt_gateways.utils.init_logger import initlogger
from mqtt_gateways.utils.generate_filepath import generatefilepath
from mqtt_gateways.utils.exception_throttled import ThrottledException

from mqtt_gateways.gateway.mqtt_map import MsgMap
from mqtt_gateways.gateway.configuration import CONFIG

_THROTTLELAG = 600  #int: lag in seconds to throttle the error logs.
_IN = 0; _OUT = 1 # indices for the message lists

# pylint: disable=too-few-public-methods
class MQTTConnectionError(ThrottledException):
    ''' Base Exception class for this module, inherits from ThrottledException'''
    def __init__(self, msg=None):
        super(MQTTConnectionError, self).__init__(msg, throttlelag=_THROTTLELAG, module_name=__name__)
# pylint: enable=too-few-public-methods

#===============================================================================
# The MQTT callbacks.
# In all the MQTT callbacks, the userdata is expected to be a dictionary of the
# following elements:
#   - the root logger
#   - mqttparams, the dict of MQTT parameters, including the msg_map and the msg_list
#   - the gateway interface instance
#===============================================================================

def on_connect(client, userdata, flags, return_code):
    # pylint: disable=unused-argument
    '''
    The MQTT callback when a connection is established.

    It sets to True the key ``connected`` of the :data:`localdata`
    dictionary and subscribes to the topics available in the message map.
    '''
    logger = userdata['logger']
    logger.info(''.join(('Connected with result code <', str(return_code), '>.')))
    userdata['connected'] = True
    msg_map = userdata['msgmap']
    for topic in msg_map.topics:
        try: client.subscribe(topic)
        except ValueError:
            logger.info(''.join(('Topic <', topic, '> cannot be subscribed to.')))
            continue
        logger.debug(''.join(('Subscribing to topic <', topic, '>.')))

def on_disconnect(client, userdata, return_code):
    # pylint: disable=unused-argument
    '''
    The MQTT callback when a disconnection occurs.

    It sets to False the key ``connected`` of the :data:`mqttparams`
    dictionary and initiates the relevant variables to start the active monitoring
    of the reconnection attempts.
    '''
    logger = userdata['logger']
    logger.info(''.join(('Client has disconnected with code <', str(return_code), '>.')))
    userdata['connected'] = False

def on_message(client, userdata, mqtt_msg):
    # pylint: disable=unused-argument
    '''
    The MQTT callback when a message is received from the MQTT broker.

    The message (topic and payload) is mapped into its internal representation and
    then appended to the incoming message list for the gateway interface to
    execute it later.
    '''
    logger = userdata['logger']
    logger.debug(''.join(('MsgRcvd-Topic:<', mqtt_msg.topic, '>-Payload:<', str(mqtt_msg.payload), '>.')))
    msg_map = userdata['msgmap']
    try: internal_msg = msg_map.mqtt2internal(mqtt_msg)
    except ValueError as err:
        logger.info(str(err))
        return
    msgl = userdata['msglists']
    msgl[_IN].append(internal_msg)

def startgateway(gateway_interface, fullpath=None):
    '''
    Initialisation and main loop.

    Initialises the configuration and the logger, starts the interface,
    starts the MQTT communication then starts the main loop.
    The loop calls the MQTT loop method to process any message from the broker,
    then calls the gateway interface loop, and finally publishes all MQTT
    messages queued.

    Notes on MQTT behaviour:

    - if not connected, the `loop` and `publish` methods will not do anything,
      but raise no errors either.
    - it seems that the `loop` method handles always only one message per call.

    Notes on the loading of data:
    the configuration file is the only file that needs to be either
    passed as argument through the command line, or the default settings will
    be used (and probably fail as one needs at least a valid MQTT broker for
    the application to start).  All other filenames will be in the configuration
    file itself. The configuration file name can be passed as the first argument
    in the command line.  If the argument is a directory (i.err. ends with a slash)
    then it is appended with the default file name. If it is a path it is checked
    to see if it is absolute, and if it is not it will be prepended with the path
    of the calling script.  The default file name is the name of the calling script
    with the ``.conf`` extension.  The default directory is the directory of
    the calling script.

    Args:
        gateway_interface (class (not an instance of it!)): the interface
            The only requirement is that it should have an appropriate constructor
            and a ``loop`` method.
        fullpath (string): the absolute path of the application
            It will be useful to find the various files that are defined by a
            relative path. If not available the current directory will be used,
            but what 'current' means might be subject to interpretation depending
            on how the script is launched.

    Raises:
        OSError: if any of the necessary files are not found.

            The necessary files are the configuration file (which is necessary to define
            the mqtt broker, at the very least) and the map (for which there can not be
            any default).
            It tries to catch most other 'possible' exceptions.
            KeyboardInterrupt should work as there are a few pauses around. Finally,
            only errors thrown by the provided interface class will not be caught and
            could terminate the application.
    '''

    # Process fullpath
    if fullpath is None: fullpath = sys.argv[0] # not ideal but should work most of the time
    app_name = os.path.splitext(os.path.basename(fullpath))[0] # first part of the filename, without extension
    app_path = os.path.realpath(os.path.dirname(fullpath)) # full path of the launching script
    # Load the configuration. Check the first command line argument for the filename.
    if len(sys.argv) >= 2: pathgiven = sys.argv[1].strip()
    else: pathgiven = '' # default location in case no file name or path is given
    conffilepath = generatefilepath(app_name, '.conf', app_path, pathgiven)
    cfg = loadconfig(CONFIG, conffilepath)

    # Initialise the root logger.
    logger = logging.getLogger(app_name)
    logfilepath = generatefilepath(app_name, '.log', app_path, cfg.get('LOG', 'logfilename'))
    emailhost = (cfg.get('LOG', 'host'), cfg.getint('LOG', 'port'))
    initlogger(logger, app_name, logfilepath, cfg.getboolean('LOG', 'debug'),
               emailhost, cfg.get('LOG', 'address'))
    # Log the configuration used.
    logger.info('=== APPLICATION STARTED ===')
    logger.info('Configuration:')
    for section in cfg.sections():
        for option in cfg.options(section):
            logger.info(''.join(('   [', section, '].', option, ' : <',
                                 str(cfg.get(section, option)), '>.')))
    # Warn in case of error processing the configuration file.
    if cfg.has_section('CONFIG') and cfg.has_option('CONFIG', 'error'):
        raise OSError(''.join(('Error <', cfg.get('CONFIG', 'error'), '> while processing the configuration file.')))
    # Instantiate the gateway interface.
    interfaceparams = {} # the parameters for the interface from the configuration file
    for option in cfg.options('INTERFACE'): # read the configuration parameters in a dictionary
        interfaceparams[option] = str(cfg.get('INTERFACE', option))
    msglists = [[], []] # pair of message lists
    gatewayinterface = gateway_interface(interfaceparams,
                                         msglists,
                                         fullpath)
    # Load the map data.
    mapfilepath = generatefilepath(app_name, '.map', app_path, cfg.get('MQTT', 'mapfilename'))
    try:
        with open(mapfilepath, 'r') as mapfile:
            map_data = mapfile.read()
    except (OSError, IOError) as err:
        raise OSError(''.join(('Error <', str(err), '> with map file <', mapfilepath, '>.')))
    messagemap = MsgMap(map_data)
    # Initialise the dictionary to store parameters and to pass to the callbacks
    localdata = {}
    localdata['connected'] = False #  boolean to indicate connection, to be set in the callbacks
    localdata['timeout'] = cfg.getfloat('MQTT', 'timeout') # for the mqtt loop() method
    localdata['msgmap'] = messagemap
    localdata['msglists'] = msglists
    localdata['logger'] = logger
    localdata['interface'] = gatewayinterface
    # Initialise the MQTT client and connect.
    mqttclient = mqtt.Client(client_id=app_name,
                             clean_session=True,
                             userdata=localdata,
                             protocol=mqtt.MQTTv311,
                             transport='tcp')
    mqttclient.on_connect = on_connect
    mqttclient.on_disconnect = on_disconnect
    mqttclient.on_message = on_message
    try:
        mqttclient.connect(host=cfg.get('MQTT', 'host'),
                           port=cfg.getint('MQTT', 'port'),
                           keepalive=cfg.getint('MQTT', 'keepalive'))
    except (OSError, IOError):
        # the loop will try to reconnect anyway so just log an info that might help diagnostics
        logger.info('Client can''t connect to broker, socket error returned.')

    # Main loop
    while True:
        # Deal with the situation where mqtt is not connected as the loop() method does not automatically reconnect.
        if not localdata['connected']:
            try: raise MQTTConnectionError('Client can''t reconnect to broker.')
            except MQTTConnectionError as err: # not very elegant but works
                if err.trigger: logger.critical(err.report)
        # Call the mqtt loop.
        mqttclient.loop(localdata['timeout'])
        # Call the interface loop.
        gatewayinterface.loop()
        # Publish the messages returned, if any.
        while True:
            try: internal_msg = msglists[_OUT].pop(0) # send messages on a FIFO basis
            except IndexError: break
            try: mqtt_msg = messagemap.internal2mqtt(internal_msg)
            except ValueError as err:
                logger.info(str(err))
                continue
            mqttclient.publish(mqtt_msg.topic, mqtt_msg.payload, qos=0, retain=False)
