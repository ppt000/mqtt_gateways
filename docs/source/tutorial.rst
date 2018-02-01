Tutorial
========

.. note::
	This is a work in progress!

Let's go through a practical example, with a very simple protocol.

The Need
********
Our gate has an entry system, or intercom. Visitors push the bell button, and (if all goes well...)
after a brief conversation someone let them in by pushing a gate release button in the
house. Residents have a code to let themselves in: they enter the code and the system releases the
gate.

I would like to receive messages about these events, so I can trigger other events (like switching
on lights). I would also like to trigger the gate release independently of the entry system.

As this system is not *connected* (and I don't want to change it), I need to interface it
to my network.

The Solution
************
The system exposes the electrical contacts that operate the bell and the gate. An Arduino
will sense the electrical contacts going HIGH or LOW and can communicate these levels to
a Raspberry Pi (or any other computer) via the USB connection. The Arduino can also be told
to switch ON or OFF a relay to release the gate.

Implementation
**************
This is actually something very close of what I have had to do. I have used an Arduino Micro
with some basic circuitry connected to the interrupt pins and programmed it so that it would
communicate through the serial interface (in this case via the USB connection) with very simple
messages for each event: each message is a pair of characters, the first indicating the contact
and the second indicating its state.  As there are only 2 contacts, and their states could only
be ON or OFF, the 4 messages are ``10``, ``11``, ``20`` and ``21``.

The Arduino code debounces the signals it senses and sends 1 message when the contact goes
ON (``11`` or ``21``) and another one when it goes off (``10`` or ``20``). It can also receive messages,
but only the one triggering the gate release makes sense (``21``).  There is no need to trigger the bell via MQTT
(no ``11`` or ``10``), and the Arduino does not wait for the message to turn the gate release OFF (``20``);
it does it automatically after 3 seconds, for security.

Finally, I connect the Arduino and the Raspberry Pi via the USB connection. All that is left is
writing the code for the Raspberry Pi to exchange those messages with the MQTT network.  For that we will
create a gateway.  Let's call it **entry**; the project folder will be under ``mqtt_gateways``, at the same
level as ``gateway`` and ``dummy``, and called also ``entry``.  The launcher script will be
called ``entry2mqtt`` and will be located inside the ``entry`` folder.  But first we need to define
the functionalities of this gateway.

The map file
************

A good place to start is to write the map file as it forces to list the functionalities that we want to
implement.

Here we want the gateway to broadcast the state changes of the bell (1) and the gate release (2),
as well as open the gate when commanded to (3).  Additionally, we would like the light at the gate to be switched
on when the gate is opened (4) (this could be done in another application that receives the *gate open* broadcast,
but it is useful to show how it can be done inside this gateway).  We therefore have 4 *events* to model
with our message characteristics (see :doc:`Concepts <concepts>`).

.. csv-table:: Model
   :header: "Event", "Function", "Gateway", "Location", "Device", "Type", "Action"

   "Bell Ring", "Security", "entry2mqtt", "gate_entry", "entry_system", "Status", "BELL_ON"
   "Bell End", "Security", "entry2mqtt", "gate_entry", "entry_system", "Status", "BELL_OFF"
   "Gate Open", "Security", "entry2mqtt", "gate_entry", "entry_system", "Status", "GATE_OPEN"
   "Gate Close", "Security", "entry2mqtt", "gate_entry", "entry_system", "Status or Command", "GATE_CLOSE"
   "Light On", "Lighting", "unknown", "gate_entry", "unknown", "Command", "LIGHT_ON"
   "Light Off", "Lighting", "unknown", "gate_entry", "unknown", "Command", "LIGHT_OFF"

There a few important points to make here:

- The *status* messages sent by this gateway need to be unequivocal.  By having the **Gateway**
  characteristic set to this gateway name should already make those messages unique.
- Ideally these messages should also be *overloaded* with information, so that other applications
  have a range of possibilities for topics to subscribe to, depending of which keywords they happen
  to know.  In the example above, specifying the **Device** gives an extra layer of identification
  that is redundant but gives more options for subscription topics.
- The *command* messages need to embody as much information as possible to ensure they reach
  their destination.  However here we will assume that we do not know the **Gateway** or the **Device**
  that operates the lights.  So we only specify the **Function**, the **Location** and the **Action**
  and *hopefully* the application in charge of the lighting will receive the message and execute
  the command.


.. note::
	What follows does not make sense... yet! Updates coming soon.


In the folder ``mqtt_gateways/data`` create the file ``entry2mqtt.map``.


Create package
**************

Create directory ``siedle`` within ``mqtt_gateways``.
Create ``__init__.py``.  Leave empty or add just a module docstring.
