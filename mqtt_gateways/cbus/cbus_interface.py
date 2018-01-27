'''This module defines the :class:`cbusInterface` class.'''

import logging
import re
import time
import os.path

from mqtt_gateways.cbus.cbus_serial import cbusSerial, cbusInitError, cbusConnectionError
from mqtt_gateways.cbus.cbus_data import FUNCTIONS, ACTIONS, LIGHTS, LEVELS

from mqtt_gateways.gateway.mqtt_map import internalMsg

def _checksum(hexstring):
    '''
    Returns True if hexstring is a valid hexadecimal string and if the checksum
    is correct as specified by the C-Bus documentation, otherwise returns False.
    '''
    total = 0
    try:
        for i in range(1, (len(hexstring)/2)+1):
            try: total += int(hexstring[2*(i-1)], 16)*16 + int(hexstring[(2*i)-1], 16)
            except ValueError: return False
    except IndexError: return False
    return total%256 == 0

_PATTERN_MonitoredSAL = '05([0-9A-F]{2})3800([0-9A-F]+)'
''' RegEx patterns to match incoming messages from C-Bus; see docs for terminology.'''

_PATTERN_CALReply = '86[0-9A-F]{4}00([0-9A-F]{2})0738([0-9A-F]{2})([0-9A-F]+)'
''' RegEx patterns to match incoming messages from C-Bus; see docs for terminology.'''

_PATTERN_LevelRequest = '\x5C05FF00730738'
''' Level request pattern (it is just a string here) - it needs to be followed by the Block Start and then \x0D.'''

_CBUSMSGMAXLEN = 16 # max = 21, - 3 for the header, and must be multiple of 4 to be sure.
''' C-Bus actual maximum message length.'''

_STATUS_REQUEST_FREQ = 60
''' Number of seconds between each Status Request - arbitrary.'''

_BLOCK_START = ['00', '20', '40', '60', '80', 'A0', 'C0', 'E0']
''' The 8 different possibilities for _BLOCK_START.'''

_MAXARGNUMBER = 2
''' Maximum number of arguments accepted in a command. Needed for error management.'''

_INTERNAL2CBUS = 0
''' Index for the dictionaries.'''
_CBUS2INTERNAL = 1
''' Index for the dictionaries.'''

class cbusInterface(cbusSerial):
    '''
    Represents the higher layer of communication with the C-Bus interface.

    Args:
        params (dictionary): the parameters from the configuration file
            under the ``[INTERFACE]`` section.
        msglists (list): pair of lists of :class:`internalMsg` objects; the
            first list is for the inbound messages, the second one for the
            outbound messages.
        fullpath (string): full absolute path of the application.
    '''

    def __init__(self, params, msglists, full_path=None):

        if full_path is None: # create NullHandler
            self._logger = logging.getLogger(__name__)
            self._logger.addHandler(logging.NullHandler())
        else: # hook up to the 'root' logger
            root_name = os.path.splitext(os.path.basename(full_path))[0] # first part of the filename, without extension
            self._logger = logging.getLogger(''.join((root_name, '.', __name__)))

        # Check the params dictionary
        try: dev = params['device']
        except KeyError: raise cbusInitError('The <device> option is not defined in the configuration file.')

        self._logger.debug(''.join(('Module <', __name__, '> started.')))
        # Constructor below might throw an exception. Let it bubble, as it is fatal.
        super(cbusInterface, self).__init__(dev, full_path)
        self._t0 = time.time()
        self._block = 0

        # Outgoing messages list
        self._msglist_in = msglists[0]
        self._msglist_out = msglists[1]

        # Build the _functions dictionaries
        self._functions = [FUNCTIONS, {v: k for k, v in FUNCTIONS.items()}]

        # Build the _locations dictionaries
        self._locations = [{}, {}]
        for light in LIGHTS:
            if LIGHTS[light][1] not in self._locations[_INTERNAL2CBUS]: # new location
                self._locations[_INTERNAL2CBUS][LIGHTS[light][1]] = [] # create the key 'local name of location : []'
            self._locations[_INTERNAL2CBUS][LIGHTS[light][1]].append(LIGHTS[light][0])
            # add the C-Bus light code to the list
            self._locations[_CBUS2INTERNAL][LIGHTS[light][0]] = LIGHTS[light][1]
            # create the key 'C-Bus light code : local name of location'

        # Build the _actions dictionaries
        self._actions = [{}, {}]
        for action in ACTIONS:
            self._actions[_INTERNAL2CBUS][action[0]] = action[1]
            if action[1][0] not in self._actions[_CBUS2INTERNAL]:
                self._actions[_CBUS2INTERNAL][action[1][0]] = action[0]

        # Build the '_lights' dictionaries
        self._lights = [{}, {}]
        for light in LIGHTS:
            self._lights[_INTERNAL2CBUS][light] = LIGHTS[light][0]
            self._lights[_CBUS2INTERNAL][LIGHTS[light][0]] = light

        # Build the '_blockstart' list made of the blocks that are actually in use
        self._blockstart = []
        for block in _BLOCK_START:
            block_addr = int(block, 16)
            for light in self._lights[_INTERNAL2CBUS]:
                light_addr = int(self._lights[_INTERNAL2CBUS][light], 16)
                if (light_addr >= block_addr) and (light_addr < (block_addr+32)):
                    # there is at least this light in the current block, keep it
                    self._blockstart.append(block)
                    break

    def loop(self):
        '''The compulsory method called periodically by the gateway.

        The loop deals with inbound messages as expected, but also triggers
        a periodic status request *per block* as per C-Bus documentation.
        This is an extra feature to double check that no state change has been
        missed, but also to get the correct status at startup.
        '''
        # Empty the incoming list first
        while True:
            try: imsg = self._msglist_in.pop(0) # read messages on a FIFO basis
            except IndexError: break
            try: self._execute_command(imsg)
            except cbusConnectionError as err:
                if err.trigger: self._logger.critical(err.report)
        # Launch a status request
        try: self._status_request()
        except cbusConnectionError as err:
            if err.trigger: self._logger.critical(err.report)
        # Read C-Bus system for commands or statuses
        try: self._read_bus()
        except cbusConnectionError as err: self._logger.info(str(err))

    def _execute_command(self, imsg):
        '''
        Executes the command represented by the internal message.

        The internal message might represent a single light to operate on
        or a whole set of lights (for a whole location for example),
        in which case there should be many commands to send.
        The algorithm concatenates the tokens depending on the number of arguments
        required by the action to create single commands (made of an action byte, an
        address byte and eventually a level byte), then concatenates those
        commands so that the maximum amount of messages are sent to the
        interface. According to the documentation, the maximum length of the
        code that can be sent to the serial interface is 21 bytes, excluding the
        leading \x5C and the trailing \x0D. This means 18 bytes for commands
        (excluding the '053800' at the beginning). Therefore the length of
        concatenated commands is tested in order to avoid sending messages that
        are too long.

        Args:
            imsg (:class:`internalMsg` object): the message/command to execute

        Raises:
            cbusConnectionError: in case of a problem writing to the serial interface.
            ValueError: when the message can not be converted in a C-Bus action.
        '''

        # Process the action first
        try: actioncode = self._actions[_INTERNAL2CBUS][imsg.action][0]
        # Byte representing the C-Bus action= first byte of the dict value
        except KeyError:
            raise ValueError(''.join(('Action <', imsg.action, '> not found')))
        argnum = int(actioncode, 16) & 7 # Compute the number of arguments from the last 3 bits (see C-Bus doc)
        if argnum == 1: levelcode = '' # no arguments beyond the location wanted by C-Bus from this command
        else: # this command requires an extra argument, for now it can only be a level
            try: levelcode = self._actions[_INTERNAL2CBUS][imsg.action][1]
            except KeyError: # this should never happen if the dictionary is properly coded
                raise ValueError(''.join(('Action <', imsg.action, '> has not the right internal data to execute')))
            # the level is either hardcoded for 'composite' commands (e.g. LIGHT_LOW)
            #  or should be in the arguments dictionary
            if levelcode == '%%': # this is the syntax chosen to say: 'look in the arguments dictionary'.
                try: levelcode = format(int(imsg.arguments['level'])*255/100, '02X')
                except (KeyError, ValueError):  # the ValueError is for the int() in case it can not return an int
                    self._logger.info('No level found for this command.')
                    return
            else: # the level is hardcoded, keep that value.
                pass
        # Process location and device; if device is defined it has priority.
        try: lights = [self._lights[_INTERNAL2CBUS][imsg.device]] # here 'lights' is a one element list
        except KeyError: # the device is not found or is undefined, try the location
            try: lights = self._locations[_INTERNAL2CBUS][imsg.location]
            # here 'lights' is the array of lights of the location
            except KeyError:
                raise ValueError(''.join(('Invalid location <', imsg.location,
                                          '> device <', imsg.device, '> combination.')))
        codelist = [] # List of commands to send to the interface
        code = ''; length = 0
        for light in lights:
            code = ''.join((code, actioncode, light, levelcode))
            length += 1 + argnum
            if length >= _CBUSMSGMAXLEN: # message has reached its maximum length
                codelist.append(code) # append it to the list
                code = ''; length = 0 # reset
        codelist.append(code) # append the remaining code to the list
        for cbus_cmd in codelist: # send all the messages now
            self.write(''.join(('\x5C053800', cbus_cmd, '\x0D')))
        # send back a confirmation message, same as imsg except that it is a status message
        ireply = internalMsg(iscmd=False, function=imsg.function,
                             gateway=imsg.gateway, location=imsg.location,
                             device=imsg.device, action=imsg.action, arguments=imsg.arguments)
        self._msglist_out.append(ireply)

    def _status_request(self):
        '''
        Launch status request periodically.

        Only one block is requested at a time.
        Depending on the frequency set, it might take some time to go
        through all the blocks.  If all 8 blocks are used, the whole
        cycle takes ``8 * _STATUS_REQUEST_FREQ`` to complete.
        As the initialisation code actually removes the blocks that do not contain
        any active lights, the actual cycle might be shorter.
        '''
        now = time.time()
        if (now - self._t0) > _STATUS_REQUEST_FREQ:
            self._t0 = now
            self.write(''.join((_PATTERN_LevelRequest, self._blockstart[self._block], '\x0D')))
            if self._block == len(self._blockstart)-1: self._block = 0
            else: self._block += 1

    def _read_bus(self):
        '''
        Reads one line from the CBus serial interface and converts it in a command list.

        The line read is a string made of characters that are mostly hexadecimal
        with some special characters as well.  It should always have at the end a <cr> and <lf>.
        The algorithm checks first for special situations (code too short, code ends
        with correct characters, code is an error or represent a restart
        request). Then it checks if it is a 'Monitored SAL' message, which means
        that an input unit (keypad or button) has sent a command to operate lights.
        Then it checks if the code is a 'CAL Reply' message, which means it is a reply
        to a status request and contains the status of one or more lights.

        Raises:
            cbusConnectionError: in case of problems reading the serial interface.
            cbusInitError: in case of problems initialising the serial interface.
        '''
        code = self.readline()  # this call times out if there is no new line to read.
        if code == '': return # if there are any errors at the lower level, we simply do nothing
        # the 'code' should have at least one character and the <cr><lf> sequence at the end.
        if len(code) < 3:
            self._logger.info(''.join(('Code <', code, '> is too short!')))
            return
        # test and remove <cr><lf> at the end; useful only if 'code' was not read with a 'readline()'.
        if code[-2:] != '\r\n':
            self._logger.info(''.join(('Code <', code, '> not ending in <cr><lf>.')))
            return
        code = code[:-2]
        # check special sequences first
        if code == '!': # The PCI cannot accept the (latest?) command
            self._logger.info('Character <!> returned') # no processing for now, skip
            return
        if ((code[-1:] == '+') or (code == '==')): # there has been a Power Up or a Parameter Change
            self._logger.debug('PUN or PCN detected')
            try: self.init_pci_options()
            except cbusInitError: raise # TODO: do something else here rather than crash?
            return
        # Now the 'code' should be an hexadecimal string (pairs of hex chars) ending with a check_sum
        if len(code) < 4:
            self._logger.info(''.join(('Code <', code, '> is too short!')))
            return
        # check checksum and remove it from code
        if not _checksum(code):
            self._logger.info(''.join(('Code <', code, '> has the wrong check_sum.')))
            return
        code = code[:-2]

        cmdlist = []

        # test for Monitored SAL message, which is a command sent internally within C-Bus
        match = re.search(_PATTERN_MonitoredSAL, code)
        if match:
            self._logger.debug(''.join(('Received Monitored SAL message <', code, '>.')))
            application_byte = '38' # this is already determined by the pattern
            source_address = match.group(1) # the source is the device that sent the command originally
            remaining_code = match.group(2)
            while remaining_code != '': # will always run once given the regex pattern
                if len(remaining_code) < 2:
                    self._logger.info(''.join(('Code <', code, '> too short. Skip message.')))
                    return
                action_byte = remaining_code[0:2]
                remaining_code = remaining_code[2:]
                argnum = int(action_byte, 16) & 7 # Compute the number of arguments from the last 3 bits (see C-Bus doc)
                if len(remaining_code) < (argnum*2):
                    self._logger.info(''.join(('Code <', code, '> too short, not enough arguments. Skip message')))
                    return
                if argnum < 1 or argnum > _MAXARGNUMBER:
                    # this should never happen as we write the CBUS_COMMANDS table ourselves...
                    self._logger.info(''.join(('Unexpected number of arguments in code <', code, '>. Skip message.')))
                    return
                destination_address = remaining_code[0:2]
                remaining_code = remaining_code[2:]
                level_byte = ''
                if argnum == 2:
                    level_byte = remaining_code[0:2]
                    remaining_code = remaining_code[2:]
                cmdlist.append([application_byte, action_byte, level_byte, destination_address, source_address])
        else:
            # test for CAL Reply message
            match = re.search(_PATTERN_CALReply, code)
            if match:
                self._logger.debug(''.join(('Received CAL Reply message <', code, '>.')))
                # This is a CAL Reply to a status request; create a list of status messages of type '02' (RAMP:0S:LVL$)
                application_byte = '38' # defined by the pattern
                source_address = '0A' # defined by the pattern
                reply_length = ((int(match.group(1), 16)-224)*2)-6 # number of characters in remaining_code, if correct
                destination_address = match.group(2) # Block start
                remaining_code = match.group(3)
                #self._logger.debug(''.join(('The match groups are reply length <',match.group(1),'>,
                # block start <',match.group(2),'> and code <',match.group(3),'>.')))
                if len(remaining_code) != reply_length: # maybe unnecessary
                    self._logger.info('The reply_length byte does not match the code. Skip message.')
                    return
                while remaining_code != '': # will always run once given the regex pattern
                    if len(remaining_code) < 4:
                        self._logger.info(''.join(('Code <', code, '> too short. Skip message.')))
                        return
                    # decode the level according to documentation
                    action_byte = '02'
                    if remaining_code[0:4] == '0000':
                        if destination_address in self._lights[_CBUS2INTERNAL]:
                            # the unit exists so the code should not be '0000'
                            self._logger.info(''.join(('Light <',
                                                       self._lights[_CBUS2INTERNAL][destination_address],
                                                       '> is unexpectedly offline. Check the fuses.')))
                    else: # the remaining code should be a proper level code
                        try:
                            level_byte = ''.join((LEVELS[remaining_code[2:4]], LEVELS[remaining_code[0:2]]))
                        except KeyError:
                            self._logger.info(''.join(('Level <', remaining_code[0:4],
                                                       '> not recognised. Skip message.')))
                            return
                        cmdlist.append([application_byte, action_byte, level_byte, destination_address, source_address])
                    remaining_code = remaining_code[4:]
                    destination_address = '%0.2X' % (int(destination_address, 16) + 1) # increment the address
            else:  # the message is not recognised
                self._logger.info(''.join(('Code <', code, '> does not match pattern. Skip message.')))
                return

        #=======================================================================
        # Unpack the command list.
        # TODO: Here we could have a more sophisticated process for the location.
        # For now the 'location' is actually a device but we could gather the
        # information of all the devices for a given location and send a single
        # message for that location.
        # A command in the list is a list itself with 5 elements:
        # [application_byte, action_byte, level_byte, destination_address,
        # source_address]
        #=======================================================================

        for com in cmdlist:
            try: fct = self._functions[_CBUS2INTERNAL][com[0]]
            except KeyError:
                self._logger.info(''.join(('Unrecognised function code <', com[0], '>. Skip message.')))
                return

            # substitute commands '0200' and '02FF' with '01' and 'FF' (LIGHT_LVL into LIGHT_ON or LIGHT_OFF)
            if com[1] == '02':
                if com[2] == '00': com[1] = '01'; com[2] = ''
                elif com[2] == 'FF': com[1] = '79'; com[2] = ''

            try: act = self._actions[_CBUS2INTERNAL][com[1]]
            except KeyError:
                self._logger.info(''.join(('Unrecognised action code <', com[1], '>. Skip message.')))
                return

            try: dev = self._lights[_CBUS2INTERNAL][com[3]]
            except KeyError:
                self._logger.info(''.join(('Unrecognised device code <', com[3], '>. Skip message.')))
                return

            #===================================================================
            # try: loc = self._locations[_CBUS2INTERNAL][com[3]]
            # except KeyError:
            #     self._logger.info(''.join(('Unrecognised location code <', com[3],'>. Skip message.')))
            #     return
            #===================================================================

            if com[2] == '': args = {}
            else: args = {'level': str(int(com[2], 16)*100/255)}

            imsg = internalMsg(function=fct,
                               iscmd=False, # they are all status messages
                               location='',
                               device=dev,
                               action=act,
                               arguments=args)
            self._msglist_out.append(imsg)
            self._logger.debug(''.join(('Message stacked with action <', act, '> to device <', dev, '>.')))
