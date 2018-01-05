
**This is a work in progress**

Please find the documentation at:
`<http://mqtt-gateways.readthedocs.io/>`_

Welcome to MQTT_Gateways
=========================

``mqtt_gateways`` is a python wrapper to build consistent gateways to MQTT networks.

.. image:: docs/source/basic_diagram.png
   :scale: 50%

What it does:

* it deals with all the boilerplate code to manage an MQTT connection,
  to load configuration and mapping data, and to create log handlers,
* it encapsulates the interface in a class that needs only 2 methods
  ``__init__`` and ``loop``,
* it creates an intuitive messaging abstraction layer between the wrapper
  and the interface,
* it isolates the syntax and keywords of the MQTT network from the internals
  of the interface.

Who is it for:

	Users of MQTT networks in a domestic environment, or *smart homes*,
	looking to adopt a definitive syntax for their MQTT messages and
	to build gateways with their devices that are not MQTT enabled.


