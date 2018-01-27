'''This module defines the :class:`cbusSerial` class representing the low-level
communication layer with the C-Bus PCI serial interface.
'''

import logging
import time
import os.path
import string

import serial

from mqtt_gateways.utils.exception_throttled import ThrottledException

_MYPRINTABLE = ''.join((string.digits, string.letters, string.punctuation))

def _s2p(hexs):
    '''
    Helper to log properly the commands sent to C-BUS. It catches non printable
    characters and replaces them with hex string in the form 'xFF'.
    Note: s2p = string to printable.

    Args:
        hexs (string): hexadecimal string.

    Returns:
        string: the argument with non printable characters replaced by their hex value.
    '''
    return ''.join(c if c in _MYPRINTABLE else '\\x%02X' % ord(c) for c in hexs)

# pylint: disable=bad-whitespace
_REQUESTS = [
    ['Interface Options 1 Settings Live','@2A3001','8230301E','~@A3300030','3230009E'],
    #                                             the set code ^ starts with a reset char '~'
    ['Interface Options 1 Power Up Settings','@1A4101','8241300D','@A3410030','3241008D'],
    ['Interface Options 2','@1A3E01','823E0040','@A33E0000','323E0090'],
    ['Interface Options 3','@1A4201','82420F2D','@A342000F','3242008C']
    ]
'''
Hard coded data needed to request and set specific parameters of
the C-Bus serial interface, as well as the values of these parameters that are
needed for this interface to operate properly. More specifically:

    - Options 1: SMART mode ON and MONITOR ON, all else OFF;
    - Options 2: all OFF;
    - Options 3: PCN, LOCAL_SAL, PUN and EXSTAT ON.

The format is: [Parameter Name for reference, Request code, Desired Answer, Set Command code, Acknowledge code]
'''
# pylint: enable=bad-whitespace

_PAUSE = 0.1
''' in seconds, to leave time to the PCI to process the commands; completely arbitrary, might be useless.'''

_THROTTLELAG = 600
''' in seconds, lag to throttle communication error with the PCI.'''

class cbusError(Exception):
    '''Local Exception.'''
    pass

class cbusInitError(Exception):
    '''Initialisation of the Serial Interface Error.'''
    pass

# pylint: disable=too-few-public-methods
class cbusConnectionError(ThrottledException):
    '''Connection Error for the Serial Interface.'''
    def __init__(self, msg=None):
        super(cbusConnectionError, self).__init__(msg, throttlelag=_THROTTLELAG, module_name=__name__)
# pylint: enable=too-few-public-methods

class cbusSerial(serial.Serial):
    '''
    Represents the low-level communication layer with the C-Bus PCI serial interface.

    It is an extension of the Serial class. It allows to open
    the port specifically to communicate with the C-Bus interface, as well as
    initiate its parameters.  The methods defined override the serial library
    ones; they mostly catch the exceptions and log the errors if any. Any code
    using these methods must make sure that values returned are tested and that
    any behaviour producing inconsistent results might mean simply that the port
    is not working, exceptions are being caught and 'dummy' parameters are being
    returned by the methods.  This should allow to write non-blocking code that
    deals with the bad connection only at some specific points, for example in
    the main loop, and not at each write or read command. The 'failed' boolean
    field is set to True each time a read or write operation generates an error,
    and is set back to False every time such operations are successful.  The
    outer code can check this field to know simply if the latest operation was
    successful or not.

    The constructor tries to open the port but might not succeed.  Therefore the class
    instance is always created but the port might be open or not.
    Use the serial library methods ``open()`` to later open the port in case of failure,
    and ``is_open()`` to test if it is opened already.

    Args:
        port (string): port name, passed as is to the Serial library
        full_path (string): used to 'hook' to the root logger; should contain
            the application name

    Raises:
        cbusInitError: if the serial interface can not be opened.
    '''

    def __init__(self, port, full_path=None):
        if full_path is None: # create NullHandler
            self._logger = logging.getLogger(__name__)
            self._logger.addHandler(logging.NullHandler())
        else: # hook up to the 'root' logger
            root_name = os.path.splitext(os.path.basename(full_path))[0] # first part of the filename, without extension
            self._logger = logging.getLogger(''.join((root_name, '.', __name__)))

        self._logger.debug(''.join(('Module <', __name__, '> started.')))
        try:
            super(cbusSerial, self).__init__(port, baudrate=9600, bytesize=serial.EIGHTBITS,
                                             parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                                             timeout=0.1, xonxoff=False, rtscts=False,
                                             write_timeout=1, dsrdtr=False, inter_byte_timeout=None)
        except serial.SerialException:
            raise cbusInitError('Serial Interface did not open. Check that it is connected.')
        except ValueError:
            raise cbusInitError('Serial Interface did not start because the parameters are incorrect.')
        self.init_pci_options() # this call might raise its own error.

    def readline(self):
        '''
        Reads a full line from the serial interface. Overrides parent class method.

        Raises:
            cbusConnectionError: in case of a SerialException from the interface

        .. TODO: Consider stripping the data before returning it?
        '''
        try:
            data = super(cbusSerial, self).readline()
        except serial.SerialException:
            raise cbusConnectionError('readline on C-Bus reported a SerialException.')
        if data != '': self._logger.debug(''.join(('Reading <', _s2p(data), '> from serial interface.')))
        return data

    def write(self, code):
        '''
        Writes the code to the interface. Overrides parent class method.

        Args:
            code (string): characters or bytes to write to the serial interface

        Returns:
            int: number of characters or bytes written to the interface

        Raises:
            cbusConnectionError: if there are any problems during the writing process
        '''
        if code == '': return 0
        self._logger.debug(''.join(('Writing code <', _s2p(code), '> to serial interface.')))
        try:
            nbytes = super(cbusSerial, self).write(code)
        except serial.SerialException:
            raise cbusConnectionError('Write on C-Bus reported a SerialException.')
        if nbytes != len(code):
            raise cbusConnectionError('Unexpected length written on C-Bus serial interface.')
        return nbytes

    def init_pci_options(self):
        '''
        Initialises the parameters of the PCI interface.

        This code relies on the ``_REQUESTS`` list of parameters.
        Going through every item of the list, the code asks for the status
        of a parameter 'block', checks the reply against what is expected,
        requests an update with the correct values in case they aren't, and
        checks the reply to the update to make sure it has been accepted.

        Raises:
            cbusInitError: if something fatal happens during this process
        '''

        # Reset options
        self.write('~') # reset to BASIC mode
        self.readline()
        time.sleep(_PAUSE)
        self.write('\r|\r') # and now in SMART mode
        self.readline()
        time.sleep(_PAUSE)
        for req in _REQUESTS:
            self.write(''.join((req[1], '\x0D'))) # request the current settings
            time.sleep(_PAUSE)
            data = self.readline().strip()
            if data == req[2]: # reply as expected
                self._logger.debug(''.join((req[0], ' has already the right parameters set.')))
            else: # not the reply expected
                self.write(''.join((req[3], '\x0D'))) # send the Set Command code
                time.sleep(_PAUSE)
                data = self.readline().strip()
                if data[:len(req[4])] == req[4]: # acknowledge as expected; the index in data removes the echo
                    self._logger.debug(''.join(('Settings change request for ', req[0], ' has been acknowledged.')))
                else: # not the acknowledge expected
                    self.close() # there is a problem with the serial interface, close it
                    raise cbusInitError(''.join(('Problem with Serial Interface setting parameters for ', req[0])))
