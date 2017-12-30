
*This is a work in progress*

`<http://mqtt-gateways.readthedocs.io/>`_

MQTT_Gateways
==================
A Framework to Build Consistent Gateways to an MQTT Network

Project Objective
*********************
Facilitate the integration of different proprietary protocols and devices into an MQTT network
by creating an abstraction layer that:
- standardises the messages exchanged between the MQTT network and the system being interfaced,
- defines the syntax and keywords used by the MQTT network.
By using the same abstraction layer across different gateways, the developper is assured that these gateways
will always communicate properly as they share the same code, and that any change in syntax or keywords will
only have to be coded once.

This abstraction layer is in essence a library that the developper uses to build its gateways, with the particularity
that it is constructed as a barebone application, or application 'shell', with the entry points already defined and where
the developer only has to define a class with some minimal requirements to describe and implement its interface, as well as
some mapping files that relate MQTT keywords with keywords specific to that interface.
This class is then instantiated and used by the application, where all the MQTT messaging mechanics are already defined.

 


Installation
***************


Usage
*******


Implementation
***************




To create a new MQTT gateway:
...assuming that the name used for the new gateway is 'zork'.

Create a directory 'zork' inside the 'mqtt_gateways' package directory (that also contains the directory 'gateway' for example).
Inside that directory one should create at least:
	'__init__.py' (empty),
	'zork2mqtt.py' (the launcher script, the template provided shoud be enough) and
	'zork_interface.py' (the class defining the new interface, which can be called differently if needed, just remember to change the import in the launcher script though; this is the real code to create).

To run the gateway, and to make sure the imports work, execute the launcher script from the directory above the 'mqtt_gateways' package.
Use the command:
	python -m mqtt_gateways.zork.zork2mqtt
If launching as a service, make sure the Working Directory is set to be the parent of the 'mqtt_gateways' package.
