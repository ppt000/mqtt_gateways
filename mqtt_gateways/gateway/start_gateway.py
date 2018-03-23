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

import sys

import mqtt_gateways.gateway.mqtt_client as mqtt
import mqtt_gateways.utils.app_properties as app
import mqtt_gateways.gateway.mqtt_map as mmap

from mqtt_gateways.utils.load_config import loadconfig
from mqtt_gateways.utils.init_logger import initlogger

from mqtt_gateways.gateway.configuration import CONFIG

#_IN = 0; _OUT = 1 # indices for the message lists

def startgateway(gateway_interface):
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

    # Load the configuration. Check the first command line argument for the filename.
    if len(sys.argv) >= 2: pathgiven = sys.argv[1].strip()
    else: pathgiven = '' # default location in case no file name or path is given
    conffilepath = app.Properties.getPath('.conf', pathgiven)
    cfg = loadconfig(CONFIG, conffilepath)

    # Initialise the root logger.
    logfilepath = app.Properties.getPath('.log', cfg.get('LOG', 'logfilename'))
    emailhost = (cfg.get('LOG', 'host'), cfg.get('LOG', 'port'))
    initlogger(app.Properties.root_logger, app.Properties.name, logfilepath, cfg.getboolean('LOG', 'debug'), emailhost, cfg.get('LOG', 'address'))
    logger = app.Properties.getLogger(__name__)
#    appHelper.initLogger(appHelper.name, logfilepath, cfg.getboolean('LOG', 'debug'), emailhost, cfg.get('LOG', 'address'))
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
    #msglists = [[], []] # pair of message lists
    
    gatewayinterface = gateway_interface(interfaceparams)
    # Load the map data.
    mapfilepath = app.Properties.getPath('.map', cfg.get('MQTT', 'mapfilename'))
    try:
        with open(mapfilepath, 'r') as mapfile:
            map_data = mapfile.read()
    except (OSError, IOError) as err:
        raise OSError(''.join(('Error <', str(err), '> with map file <', mapfilepath, '>.')))
    messagemap = mmap.msgMap(map_data, cfg.get('MQTT', 'root'))
    # Initialise the dictionary to store parameters and to pass to the callbacks
    localdata = {}
    localdata['connected'] = False #  boolean to indicate connection, to be set in the callbacks
    localdata['timeout'] = cfg.getfloat('MQTT', 'timeout') # for the mqtt loop() method
    localdata['msgmap'] = messagemap
    localdata['msglist_in'] = mmap.msglist_in
    # localdata['logger'] = logger # TODO: to remove with implementation of mqtt_client
    localdata['interface'] = gatewayinterface
    # Initialise the MQTT client and connect.
    mqttclient = mqtt.Client(host=cfg.get('MQTT', 'host'),
                            port=cfg.getint('MQTT', 'port'),
                            keepalive=cfg.getint('MQTT', 'keepalive'),
                            client_id=app.Properties.name,
                            userdata=localdata,
                            )

    # Main loop
    while True:
        # Deal with the situation where mqtt is not connected as the loop() method does not automatically reconnect.
        if not localdata['connected']: # the MQTT broker is not connected
            try: mqttclient.reconnect() # try to reconnect
            except (OSError, IOError): # still no connection
                try: raise mqtt.ConnectionError('Client can''t reconnect to broker.') # throttled log
                except mqtt.ConnectionError as err: # not very elegant but works
                    if err.trigger: logger.error(err.report)
        # Call the mqtt loop.
        mqttclient.loop(localdata['timeout'])
        # Call the interface loop.
        gatewayinterface.loop()
        # Publish the messages returned, if any.
        while True:
            try: internal_msg = mmap.msglist_out.pop(0) # send messages on a FIFO basis
            except IndexError: break
            try: mqtt_msg = messagemap.internal2mqtt(internal_msg)
            except ValueError as err:
                logger.info(str(err))
                continue
            mqttclient.publish(mqtt_msg.topic, mqtt_msg.payload, qos=0, retain=False)
