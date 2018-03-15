'''Interface for MusicCast.'''

from mqtt_gateways.gateway.mqtt_map import internalMsg
from mqtt_gateways.utils.app_helper import appHelper
from mqtt_gateways.musiccast.musiccast_system import System, Zone
from mqtt_gateways.musiccast.musiccast_exceptions import *
from mqtt_gateways.musiccast.musiccast_data import ACTIONS


class musiccastInterface(object):
    '''The Interface.
    
    Resolves the JSON file path and calls the System class in musiccast_system.
    Creates the locations dictionary.
    '''

    def __init__(self, params, msgls, path):
        self._logger = appHelper.getLogger(__name__)

        # Keep the message lists locally
        self._msgl_in = msgls[0]
        self._msgl_out = msgls[1]

        try: jsonpath = params['jsonpath']
        except KeyError:
            self._logger.info('The "jsonpath" option is not defined in the configuration file. Using ".".')
            jsonpath = '.'
        jsonfilepath = appHelper.getPath('.json', jsonpath)

        # instantiate the system structure
        self._system = System(jsonfilepath)
        # attach the outgoing message list to the static member msgl_out of the Zone class
        Zone.msgl_out = self._msgl_out
        # create the location to zone dictionary; each key is a location, the value is the Zone object
        self._locations = {zone.data.location: zone for dev in self._system.devices for zone in dev.zones if zone.data.location}
        # TODO: check locations in the map?

    def loop(self):
        ''' The method called periodically by the main loop.
        '''

        # process the incoming messages list
        while True:
            try: msg = self._msgl_in.pop(0) # read messages on a FIFO basis
            except IndexError: break # no more messages
            self._logger.debug(''.join(('Processing message: ', msg.str())))
            # determine is the message is 'assertive'
            if msg.gateway == 'musiccast': assertive = True
            # get the zone for this location
            try: zone = self._locations[msg.location]
            except KeyError: # the location is not found
                errtxt = ''.join(('Location ', msg.location, ' not found.'))
                self._logger.info(errtxt)
                if assertive: self._msgl_out.append(msg.reply('Error', errtxt))
                continue # ignore message and go onto next

            # discard immediately if no device linked to that location can be operated by musiccast
            if not zone.device.musiccast and not zone.device.mc_feed:
                if assertive:
                    self._msgl_out.append(msg.reply('Not Applicable', 'No MusicCast device involved in this command.'))
                continue

            try: func = ACTIONS[msg.action]
            except KeyError: # the action is not found
                errtxt = ''.join(('Action ', msg.action, ' not found.'))
                self._logger.info(errtxt)
                if assertive: self._msgl_out.append(msg.reply('Error', errtxt))
                continue # ignore message and go onto next

            zone.load_msg(msg)

            try: func(zone)
            except mcLogicError as err:
                self._logger.info(''.join(('Logic Error: ', err.message)))
                continue
            except mcConnectError as err:
                self._logger.info(''.join(('Connection Error: ', err.message)))
                continue
            except mcHTTPError as err:
                self._logger.info(''.join(('HTTP Error: ', err.message)))
                continue
            except mcDeviceError as err:
                self._logger.info(''.join(('Device Error: ', err.message)))
                continue
            except mcError as err:
                self._logger.info(''.join(('Error: ', err.message)))
                continue
            try: self._logger.debug(''.join(('State of zone ', zone.str_zone(), ' is now: ', zone.str_state())))
            except AttributeError as err: self._logger.debug(''.join(('Cannot display message.\n', repr(err))))
            try: self._logger.debug(''.join(('Source device is: ', zone.zonesource.device.data.id)))
            except AttributeError as err: self._logger.debug(''.join(('Cannot display message.\n', repr(err))))
            try: self._logger.debug(''.join(('State of zone ', zone.zonesource.str_zone(), ' is now: ', zone.zonesource.str_state())))
            except AttributeError as err: self._logger.debug(''.join(('Cannot display message.\n', repr(err))))

        # example code to write in the outgoing messages list
        #=======================================================================
        # msg = internalMsg(iscmd=True,
        #                   function='',
        #                   gateway='dummy',
        #                   location='Office',
        #                   action='LIGHT_ON')
        # self._msgl_out.append(msg)
        # self._logger.debug(''.join(('Message <', msg.str(), '> queued to send.')))
        #=======================================================================

# if device['protocol'] == 'YNCA': conn.request('GET','@SYS:PWR=?\r\n')

if __name__ == '__main__':
    #===========================================================================
    # mci = musiccastInterface(params, msgls, path)
    # for dev in mci._system.devices:
    #     print dev.data.id
    #     if dev.musiccast:
    #         for zone in dev.zones:
    #             print '\tZone ','-'.join((zone.data.id, str(zone.state['power']), zone.state['input'], str(zone.state['volume']), str(zone.state['mute'])))
    # imsg = internalMsg()
    # imsg.location = 'cinemaroom'
    # imsg.action = 'SELECT_SOURCE'
    # imsg.arguments = {'source': 'spotify', 'volume': '20', 'power': 'on', 'tune': 'off'}
    # msgls[0].append(imsg)
    # mci.loop()
    #===========================================================================
    pass