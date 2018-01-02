Installation
============

Copying the repository
**********************

The easiest way to install this project is by cloning the whole repository
into a directory named ``mqtt_gateways``.
The only non-standard dependency is the **paho.mqtt** library.
Please install it if you do not have it already in your environment.

The directory structure of the relevant files should look like this:

.. code-block:: none

	mqtt_gateways/   (root)
	|
	\- mqtt_gateways/   (package)
	   |
	   +- __init__.py
	   |
	   +- gateway/
	   |  +- __init__.py
	   |  +- mqtt_map.py
	   |  \- start_gateway.py
	   |
	   +- utils/   (files not shown here)
	   |
	   +- dummy/
	      +- __init__.py
	      +- dummy_interface.py
	      +- dummy2mqtt.py
	      \- data/
	         +- dummy2mqtt.conf
	         \- dummy2mqtt.map

The core engine of the project is the ``gateway`` sub-package with
the main module ``start_gateway.py``
that initialises everything and launches the main loop.
The ``mqtt_map.py`` module defines a class for internal messages
and a *map* class for translation methods between internal
and MQTT messages.
These methods rely on mapping data to be provided by the developer
to be discussed later.

The ``utils`` sub-package is a set of utility functions.

The ``dummy`` sub-package is the first interface.
It doesn't do anything except helping to check the set-up
and understand the inner workings of the application.

The ``dummy`` sub-package has a sub-directory ``data`` containing 2 files:
the configuration file ``dummy2mqtt.conf`` and the map file ``dummy2mqtt.map``.

Configuration
*************

The configuration file has a standard ``INI`` syntax,
with sections identified by ``[SECTION]`` and options within sections identified by ``option=value``.
The gateway being developped can use the ``[INTERFACE]`` section
where any number of options can be inserted and will be made available to the application
through a dictionary initialised with all the ``option:value`` pairs.

In the case of the ``dummy`` gateway the configuration file is just
there to give the address of the MQTT broker.
Edit the ``dummy2mqtt.conf`` file in the ``[MQTT]`` section:

.. code-block:: none

	[MQTT]
	host: 127.0.0.1
	#port: 1883

The address of the MQTT broker should be provided in the same format
as expected by the **paho.mqtt** library, usually a raw IP address
(``192.168.1.55`` for example),
but anything else that the library will accept will be passed as is.
The default port is 1883, if it is different it can also be indicated
in the configuration file.

For more details about the ``.conf`` file, defaults and command line arguments,
go to `Configuration <configuration.html>`_.

Launch
******

The application should be launched from the *root* directory;
in our case it is the first ``mqtt_gateways`` directory.
From there, type:

.. code-block:: none

	python -m mqtt_gateways.dummy.dummy2mqtt data/

The ``data/`` argument indicates where the configuration file is.
In this case it indicates the sub-directory ``data`` inside the
sub-package ``dummy`` where the launcher script ``dummy2mqtt.py``
resides.

The application only outputs 1 line to start with:
it indicates the location of the log file.
Thereafter it only outputs errors, if any, so if nothing happens
it is a good sign.  More information can be found in the log file,
which in our case is located inside the ``data`` directory, as long
as the configuration file has been used *as is*.
Let the process run a minute or so, then stop it (type ``Ctrl-C``
for example) and check the log file.  It should start with a banner
message to indicate the application has started, then a list of the
full configuration used.  Logs from previous runs are kept so make sure
to 'start from the end' of the file to read the latest logs.
If the MQTT connection is succesfull it should say so as well as
displaying the topics to which the application has subscribed.
Thereafter, there should be some ``DEBUG`` level logs to indicate
the messages sent and received, if any (there should be none at this stage).

For more details on 

First run
*********

Launch again the application in the background (same as before
with an ``&`` at the end), and watch the log file:

.. code-block:: none

	python -m mqtt_gateways.dummy.dummy2mqtt data/ &
	tail -f mqtt_gateways/dummy/data/dummy2mqtt.log

After the start-up phase, the **dummy** interface logs (at a DEBUG level)
any MQTT it receives and emits a unique message every 30 seconds.
Watch the messages being sent periodically from the logs.
Start your favourite MQTT monitor app (I use ``mqtt-spy``).  Connect to your
MQTT broker and subscribe to the topic:

.. code-block:: none

	home/+/dummy/+/+/+/C

You should see the messages arriving every 30 seconds in the MQTT monitor,
as well as in the log.
Publish now a message from the MQTT monitor:

.. code-block:: none

	topic: home/lighting/dummy/office/undefined/me/C
	payload: LIGHT_ON

You should see in the log that the message has been received
by the gateway, and that it has been processed correctly, meaning that
even if it does not do anything, the translation methods have worked.

The Mapping data
****************

The mapping data is the link between MQTT and the internal language of the interface.
It maps every keyword in the MQTT vocabulary into the equivalent keyword in the interface.
This mapping is a very simple one-to-one relationship for every keyword, and its use is only
to isolate the internal code from any changes in the MQTT vocabulary.
For the *dummy* interface, the mapping data is provided by the text file
``dummy2mqtt.map`` in the ``data`` folder.
  
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





Rejected Text
*************

.. full directory tree

	mqtt_gateways/   (root)
	\- mqtt_gateways/   (package)
	   +- __init__.py
	   +- gateway/
	   |  +- __init__.py
	   |  +- mqtt_map.py
	   |  \- start_gateway.py
	   |
	   +- utils/
	   |  +- __init__.py
	   |  +- exception_throttled.py
	   |  +- generate_filepath.py
	   |  +- init_logger.py
	   |  \- load_config.py
	   |
	   +- dummy/
	      +- __init__.py
	      +- dummy_interface.py
	      +- dummy2mqtt.py
	      \- data/
	         +- dummy2mqtt.conf
	         \- dummy2mqtt.map

	         
.. COMMENT
	*It is not compulsory to name it that way but we will assume to be the case here.*

.. COMMENT out the following paragraph for now
	Other ways of installing this framework, as a library for example, might be implemented later, but frankly this is not really a library,
	so I am not sure it should be installed that way.
	There is a ``setup.py`` file to build distributions and to install them but I have not tested
	it so far and that's why I have not posted this on PyPI (yet?).  I am not sure either it is necessary anyway.


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

