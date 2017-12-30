Installation
============

Assuming the 'root' directory has been called ``mqtt_gateways`` as advised, then the directory structure of the relevant files should look
like this:

mqtt_gateways (root)
|
+- mqtt_gateways
   |
   +- gateway
   |  |
   |  +- __init__.py
   |  +- mqtt_map.py
   |  \- start_gateway.py
   |
   +- utils
   |  |
   |  +- __init__.py
   |  +- exception_throttled.py
   |  +- generate_filepath.py
   |  +- init_logger.py
   |  \- load_config.py
   |
   +- dummy
      |
      +- __init__.py
      +- dummy_interface.py
      +- dummy2mqtt.py
      \- data
         |
         +- dummy2mqtt.conf
         \- dummy2mqtt.map

The core engine of the project is the ``gateway`` directory with a main module ``start_gateway.py``
that initialises everything that needs to and launches the main loop.  The ``mqtt_map.py`` module
defines a standard message class and a 'map' class that implements standard translation methods.  These methods
rely on map files (to be created by the developper) to translate keywords between MQTT and 'internal' languages.

The ``utils`` directory is what it says, a group of utility functions used elsewhere.

The ``dummy`` directory is the first gateway which is just there to show how it works.
Any gateway should have a name describing the system it is interfacing.  Here it is *dummy* but in reality it will be
something like *zingcee* or *zonos* for example.
The gateway will be defined in a package with its own name (here ``dummy``) and will be called as an application as ``dummy2mqtt``
(or ``zingcee2mqtt`` or ``zonos2mqtt``).  As a consequence, all data files will be called like the application ``dummy2mqtt``
followed by the relevant extension.
The gateway package has its own directory (called ``dummy``) under ``mqtt_gatewways``, containing at least 2 modules:
``dummy_interface.py`` where the ``dummyInterface`` class has to be defined,
and ``dummy2mqtt.py`` which is the launcher script.

The ''dummyInterface`` class has to define at least 2 methods: the constructor ``__init__()`` and the method ``loop()`` which
will be called periodically to process the events of the system being interfaced.
In this case, nothing will be done by these methods.

The ``dummy2mqtt.py`` launcher script is provided as a template, and any new gateway should not need to change much to this script
in order to make it work.

The ``dummy``directory has a sub-directory ``data`` containing 2 files: ``dummy2mqtt.conf`` which is the configuration file,
and ``dummy2mqtt.map`` which is the map file needed for the translation of keywords as described above.

Configuration
=============

The configuration file has a standard *INI* syntax, with sections identified by ``[SECTION]`` and options within sections identified by ``option=value``.
The gateway being developped can use the ``[INTERFACE]`` section where any number of options can be inserted.  These will be made available to the application
through a dictionary initialised with all the ``option:value``pairs.
In the case of the ``dummy`` gateway the configuration file is just there to give the address of the MQTT broker and some file locations (maps and log files)
if different from default.  The configuration file provided uses the sub-directory ``data`` for all files (which is not the default),
so that this installation (cloned from the repository) can work as is.  As a consequence, the log file will also be written in this directory.

The address of the MQTT broker should be provided in the same format as expected by the paho.mqtt library,
usually a raw IP address (192.168.1.55 for example), but anything else that the library will accept will be passed as is.
The default port is 1883, if it is different it can be also indicated in the configuration file.

Launch
======

The only purpose of launching the ``dummy`` gateway is to make sure that all modules are there, the data files are found, and that
the application can connect to the MQTT broker.
The application should be launched from the 'root' directory, here the first ``mqtt_gateways`` directory.  From there, type

python -m mqtt_gateways.dummy.dummy2mqtt data/

The ``data/`` argument simply indicated where the configuration file is.
If no errors appear then one can go and check the log file (inside the ``data`` directory) to see if all is going fine.
There should always be some logs from the initialising process.  After that there could be nothing if everything is fine.
To have more details, switch the ``debug`` option in the configuration file to ``on``, but the ``dummy`` gateway will only
show if the connection with the MQTT broker is succesfull or not, any subscriptions made and that's probably it.
The subscriptions are based on the map file, which is discussed below.

The Map file
============

The map file provides all the 'implementation dependent' MQTT data.  This is made of all the topics to subscribe to,
as well as the actual mappings between the MQTT keywords and the ones used in the current specific gateway.
These mappings should be provided for all the 'concepts' (location, device, ...) and keywords used by the gateway
(see the project description for more details).
The map file contains one piece of data per line.  Each line starts with the 'concept' that the piece of data is part of
(consider that each 'concept' is basically a separate dictionary, except for topics that go simply in a list).
It is followed by ``:`` and then the data: the actual topic to subscribe to, or a pair written as
``MQTT_keyword,Internal_keyword`` (2 keywords separated by a comma ``,``).

The map file provided for the ``dummy`` gateway is just there as example and is not used.  It is however loaded,
and the topics that are there should be subscribed to when the application is launched.

Testing
=======

The only thing that can be tested with the ``dummy`` gateway is the MQTT connection.  As described above, the log file should
provide some information regarding connection and subscriptions.
If a MQTT 'monitor' is available, one can subscribe to the same topics and send commands to those topics with the keywords
mentioned in the map file to see what happens.  In DEBUG mode, one should see some logs showing the messaging translation
process.
Once again, see the project description for more information.


  Each line contains one piece of data, made of the 

