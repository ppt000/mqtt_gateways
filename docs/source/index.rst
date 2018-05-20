.. mqtt_gateways documentation master file, created by
   sphinx-quickstart on Thu Dec 28 09:15:08 2017.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. warning::
    As of 20 May 2018, this project has been split into the core framework `mqttgateway <http://mqttgateway.readthedocs.io/en/latest/>`_,
    and the interfaces available, for example `musiccast2mqtt <http://musiccast2mqtt.readthedocs.io/en/latest/musiccast.html>`_.
    Head to those repos for the updates projects.

Welcome to MQTT_Gateways
=========================


``mqtt_gateways`` is a python wrapper to build consistent gateways to MQTT networks.

.. image:: basic_diagram.png
   :scale: 30%
   :align: right

What it does:
-------------

* it deals with all the boilerplate code to manage an MQTT connection,
  to load configuration and mapping data, and to create log handlers,
* it encapsulates the interface in a class that needs only 2 methods
  ``__init__`` and ``loop``,
* it creates an intuitive messaging abstraction layer between the wrapper
  and the interface,
* it isolates the syntax and keywords of the MQTT network from the internals
  of the interface.

Who is it for:
--------------

Developers of MQTT networks in a domestic environment, or *smart homes*,
looking to adopt a definitive syntax for their MQTT messages and
to build gateways with their devices that are not MQTT enabled.


Available gateways
------------------

The repository contains some already developed gateways to existing systems.
The currently available gateways are:

- **dummy**: the template; check the :mod:`mqtt_gateways.dummy` documentation.
- **entry**: example used for the tutorial; check it :doc:`here <tutorial>`.
- **C-Bus**: gateway to the Clipsal-Schneider C-Bus system, via its PCI Serial Interface.
    Check the :doc:`C-Bus <cbus>` documentation.

Contents
********

.. toctree::
   :maxdepth: 2
   
   Overview <overview>
   Installation <installation>
   Concepts <concepts>
   Tutorial <tutorial>
   Configuration <configuration>
   Project Description <description>
   C-Bus Gateway <cbus>
   MusicCast Gateway <musiccast>
   Package Documentation <mqtt_gateways>
   Indices <indices>
