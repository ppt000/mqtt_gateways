'''
The **entry** interface class definition. Use it as a template.

This module defines the class :class:`entryInterface` that will be instantiated by the
main gateway module.
Any other code needed for the interface can be placed here or in other
modules, as long as the necessary imports are included of course.
'''

# only import those modules if using the logger provided
import logging
import os.path

import serial

from mqtt_gateways.gateway.mqtt_map import internalMsg

class entryInterface(object):
    '''
    Doesn't do anything but provides a template.

    The minimum requirement for the interface class is to define 2 public
    methods:

    - the constructor ``__init__`` which takes 4 arguments,
    - the ``loop`` method.

    Args:
        params (dictionary of strings): contains all the options from the configuration file
            This dictionary is initialised by the ``[INTERFACE]`` section in
            the configuration file.  All the options in that section generate an
            entry in the dictionary. Use this to pass parameters from the configuration
            file to the interface, for example the name of a port, or the speed
            of a serial communication.
        msgls (pair of lists of :class:`internalMsg` objects): these lists
            represent the communication *bus* with the core of the
            application. The first list should contain the incoming messages to
            process by this interface, and the second list can be used to
            send messages from this interface to the core application (and
            subsequently to the MQTT network).  The elements of these lists
            should be instantiations of the :class:`internalMsg` class.  Use the
            method ``pop(0)`` to read the lists on a FIFO basis and
            the method ``append(msg)`` to fill the lists.
            The constructor should assign these lists to a local attribute
            that the other methods of this class can use when needed.
            It is strongly advised to *empty* the incoming list at the beginning of
            the process.  The gateway will empty all messages of the outgoing
            list and attempt to send them to the MQTT system.
            The main reason to keep 2 lists instead of one is to simplify
            sending statuses while processing incoming commands one by one.
        path (string): the full absolute path of the launcher script
            This path can be used to extract the name of the application
            or the directory where it is located.  It can be useful to
            the ``logging`` library to allow proper hierarchical logging
            or to other functions that need to find data files relative to
            the launcher script location.

    '''

    def __init__(self, params, msgls, path):
        # use this logger to benefit from the handlers of the core application
        rootname = os.path.splitext(os.path.basename(path))[0] # first part of the filename
        self._logger = logging.getLogger(''.join((rootname, '.', __name__)))
        # optional welcome message
        self._logger.debug(''.join(('Module <', __name__, '> started.')))
        # example of how to use the 'params' dictionary
        try: port = params['port'] # the 'port' option should be defined in the configuration file
        except KeyError: # if it is not, we are toast, or a default could be provided
            errormsg = 'The "port" option is not defined in the configuration file.'
            self._logger.critical(''.join(('Module ', __name__, ' could not start.\n', errormsg)))
            raise KeyError(errormsg)
        # optional success message
        self._logger.debug(''.join(('Parameter "port" successfully updated with value <',
                                    port, '>')))
        # *** INITIATE YOUR INTERFACE HERE ***
        self._ser = serial.Serial(port=port, baudrate=9600, timeout=0.01)

        # Keep the message lists locally
        self._msgl_in = msgls[0]
        self._msgl_out = msgls[1]

    def loop(self):
        ''' The method called periodically by the main loop.

        Place here your code to interact with your system.
        '''
        # example code to read the incoming messages list
        while True:
            try: msg = self._msgl_in.pop(0) # read messages on a FIFO basis
            except IndexError: break
            # do something with the message; here we log first
            self._logger.debug(''.join(('Message <', msg.str(), '> received.')))
            # given the topics subscribed to, we will only test the action
            if msg.action == 'GATE_OPEN':
                try: self._ser.write('21')
                except serial.SerialException:
                    self._logger.info('Problem writing to the serial interface')
        # read the Entry System physical interface for any event
        try: data = self._ser.read(2)
        except serial.SerialException:
            self._logger.info('Problem reading the serial interface')
            return
        if len(data) == 0: return # no event, the read timed out
        if len(data) == 1: # not normal, log and return
            self._logger.info(''.join(('Too short data read: ,',str(data),'>.')))
            return
        # now convert the 'data' into an internal message
        if data[0] == '1':
            device = 'Bell'
            if data[1] == '0': action = 'BELL_OFF'
            elif data[1] == '1': action = 'BELL_ON'
            else:
                self._logger.info('Unexpected code from Entry System')
                return
        elif data[0] == '2':
            device = 'Gate'
            if data[1] == '0': action = 'GATE_CLOSE'
            elif data[1] == '1': action = 'GATE_OPEN'
            else:
                self._logger.info('Unexpected code from Entry System')
                return
        msg = internalMsg(iscmd=False, # it is a status message
                          function='Security',
                          gateway='entry2mqtt',
                          location='gate_entry',
                          device=device,
                          action=action)
        self._msgl_out.append(msg)
        self._logger.debug(''.join(('Message <', msg.str(), '> queued to send.')))
        # let's switch on the lights now if the gate was opened
        if data == '21':
            msg = internalMsg(iscmd=True,
                              function='Lighting',
                              location='gate_entry',
                              action='LIGHT_ON')
            self._msgl_out.append(msg)

