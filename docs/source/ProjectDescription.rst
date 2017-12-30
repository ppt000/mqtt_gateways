Project Description
===================

.. image:: images/DomesticIOT.JPG

Genesis
*******

It all started when I realised that `MQTT <http://mqtt.org/>`_ was a really robust protocol while looking for a reliable way to connect the devices in my home.
I was running an MQTT broker (mosquitto) on a server for a while, with some clients subscribing and publishing messages.

As none of my devices were natively MQTT enabled (very few are), I needed an interface to translate messages from my devices (or sets of devices)
to MQTT messages and back.  More importantly, I needed this interface to be able to communicate to other interfaces without having to
re-write code every time I would need to change something. All this is pretty much standard stuff in the IoT world.

As I did not find any *simple* tool to do this, I decided to write a re-usable abstraction layer to build MQTT gateways.

Concepts
********

Without going back to the wheel, I needed to step back and appreciate what a message is made of in general, and what messages need
to do in a domestic IoT environment.  By the way, this frames the target audience of this project: it is for domestic use in small networks.

Messages have a source, a destination and a content.  As much as the source being present in a message is a 'nice to have', the destination and content are
pretty much essential, otherwise there is no message.
An MQTT message has a topic and a payload.  Generally a topic could be identified as destination and the payload as content.  In reality,
the topic carries often more than pure destination information, and this makes the MQTT protocol particularly powerful and versatile.
This is important to keep in mind.

Destination
-----------

Any 'receiving' MQTT client is a potential destination that needs to subscribe to all the topics that could be addressed to it.
Any 'sender' client needs to address a variety of devices and systems, but
does not want to be constrained by a very restrictive addressing system, where a particular device needs to
be addressed with a particular name, or worse, with an id that might change each time the device is replaced, for example.  Rather,
the addressing system needs to be based on real-life concepts that are less likely to change with time, if at all.  These concepts
are essentially the characteristics of a device that, taken together, define hopefully uniquely that device.
Empirically, I have found that the following characteristics could be enough to define a device:

- function: what the device does (lighting, security, audiovideo, ...);
- location: where is the device or where it's action is being felt (an audio amplifier might be in a basement but it is powering speakers in the bedroom);
- gateway: which application is managing that device, if any;
- device: a unique identifier for the device, as a last resort.

Any message having a combination of these characteristics (but not necessarily all of them) shoud be able to address properly
a device.

Content
-------

The content of a message in the context of domestic IoT can be split into:

- a type: *command* for messages that are requiring an action to be performed, or *status* for messages
that only broadcast to interested parties that some status has changed;
- a characteristic of the device that needs to be changed in case of a *command*, or that needs to broadcast
its state in case of a *status* (e.g. 'device=on' which can mean 'turn it on' if the type is *command*,
or can mean 'device is now on' if type is *status*).

Source
------

Any message can carry its source, which can be a device or a gateway, depending on what makes more sense.
Again, this should never be compulsory but can be very helpful to filter messages.

Summary
-------

There are therefore 7 'concepts' (function, location, gateway, device, type, content, source) in a message for our project framework.
Out of these 7 concepts, only 1 has predefined values (the type which can only be a command or a status).  All the 
other ones have any number of possible values in the MQTT syntax. They each are a table in the database representation
of the domestic network and therefore their corresponding values in the internal code of the gateway needs to be provided in the
mapping file.