Summary
=======

.. old text, keep it for now as a comment
   A Framework to Build Consistent Gateways to an MQTT Network

.. include:: summary.rst


.. _project-objective:

Project Objective
*****************

Facilitate the integration of different proprietary protocols and devices into an MQTT network
by creating an abstraction layer that:

* standardises the messages exchanged between the MQTT network and the system being interfaced,
* defines the syntax and keywords used by the MQTT network.

By using the same abstraction layer across different gateways, the developer is assured that these gateways
will always communicate properly and that any change in syntax or keywords will only have to be coded once.

This abstraction layer is in essence a library that the developper uses to build its gateways.  However it is constructed as
a barebone application, or application container, where
the developer has only to define a class with some minimal requirements to describe and implement its interface, as well as
some mapping files that relate MQTT keywords with keywords specific to that interface.
This class is then instantiated and used by the application.

`See Project Description <project_description.html>`_

.. _installation:

Installation
************

The easiest way to install this project is by cloning the whole repository
into a directory named ``mqtt_gateways``.  , as the project, but this is not compulsory.


`See Installation <installation.html>`_

Usage
*****


Implementation
**************

To create a new MQTT gateway:
...assuming that the name used for the new gateway is 'zork'.

Create a directory 'zork' inside the 'mqtt_gateways' package directory (that also contains the directory 'gateway' for example).
Inside that directory one should create at least:

- ``__init__.py`` (empty),
- ``zork2mqtt.py`` (the launcher script, the template provided shoud be enough) and
- ``zork_interface.py`` (the class defining the new interface, which can be called differently if needed, just remember to change the import in the launcher script though; this is the real code to create).

To run the gateway, and to make sure the imports work, execute the launcher script from the directory above the 'mqtt_gateways' package.
Use the command::

	python -m mqtt_gateways.zork.zork2mqtt
	
If launching as a service, make sure the Working Directory is set to be the parent of the 'mqtt_gateways' package.







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

