``mqtt_gateways`` is a python wrapper to build consistent gateways to MQTT networks.

What it does:

* it deals with all the boilerplate code to manage an MQTT connection,
  to load configuration and mapping data, and to create appropriate log handlers,
* it encapsulates the interface in a class declaration with only 2 methods
  ``__init__`` and ``loop``,
* it creates a messaging abstraction layer between the wrapper and the interface,
* it isolates the syntax and keywords of the MQTT network from the internals of the interface.

.. image:: basic_diagram.png
   :scale: 50%