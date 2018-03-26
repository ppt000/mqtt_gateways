'''
Representation of the Audio-Video system state.
'''

import json
from collections import namedtuple

import mqtt_gateways.musiccast.musiccast_http as mchttp
import mqtt_gateways.musiccast.musiccast_data as mcdata
import mqtt_gateways.musiccast.musiccast_exceptions as mcx

import mqtt_gateways.utils.app_properties as app
_logger = app.Properties.get_logger(__name__)

# Records for the devices data
Root = namedtuple('Root', ('devices'))
DeviceData = namedtuple('DeviceData', ('id', 'model', 'protocol', 'host', 'gateway', 'zones', 'sources', 'feeds'))
ZoneData = namedtuple('ZoneData', ('id', 'location', 'mc_id'))
SourceData = namedtuple('SourceData', ('id', 'qualifier', 'mc_id'))
FeedData = namedtuple('FeedData', ('id', 'device_id', 'mc_id'))
JSON_INDEX = {'root': Root, 'devices': DeviceData, 'zones': ZoneData,
              'sources': SourceData, 'feeds': FeedData}

class System(object):
    '''  If location is empty it will not be loaded
    in the dictionary, which is what we want for devices that are 'pure players' but
    still have a zone definition in MusicCast for some of the commands. '''
    def __init__(self, jsonfilepath):
        # load the static data about the devices; errors are fatal.
        try:
            with open(jsonfilepath, 'r') as json_file:
                json_data = json.load(json_file)
        except (IOError, OSError):
            _logger.critical(''.join(('Can''t open ', jsonfilepath, '. Abort.')))
            raise
        except ValueError:
            _logger.critical(''.join(('Can''t JSON-parse ', jsonfilepath, '. Abort.')))
            raise
        # change the dictionaries into namedtuples, just to be clear that this data is immutable
        # also this process ensures all the required fields are present, event if set to None
        try:
            self.data = self._unpack_dicts(json_data, 'root')
        except StandardError:
            _logger.critical('Something went wrong unpacking the JSON data. Abort.')
            raise
        # initialise the _NullDevice
        #_NullDevice = Device(DeviceData('NullDevice', '', '', '', '', [], [], []))
        # create the list of devices
        self.devices = []
        for device_data in self.data.devices:
            device = Device(device_data)
            self.devices.append(device)

        # === The following members could be methods used at run-time, but as the
        # underlying data is immutable it is better to compute them once and store.
        # Now that devices are created we can update the feeds with references to their device
        for dev in self.devices:
            for feed in dev.feeds:
                found = [x for x in self.devices if x.data.id == feed.data.device_id]
                if found: feed.device = found[0]
                else: # device for that feed was not found
                    _logger.info(''.join(('Device ', feed.data.device_id, ' not defined.')))
                    feed.device = None # _NullDevice
        # identify the devices that have MusicCast enabled feeds connected to them
        for dev in self.devices:
            dev.mc_feed = any([feed.device.musiccast for feed in dev.feeds if feed.device is not None])
            # now we can initialise MusicCast related fields
        for dev in self.devices:
            dev.init_musiccast()

    def _unpack_dicts(self, obj, idx):
        ''' Unpacks the dictionaries within the JSON structure into
        pre-defined namedtuples.'''
        if isinstance(obj, list): #type(obj) is list:
            tup = ()
            for item in obj:
                tup += (self._unpack_dicts(item, idx),)
            return tup
        if isinstance(obj, dict): # type(obj) is dict:
            args = ()
            for key in JSON_INDEX[idx]._fields:
                if key not in obj:
                    args += (None,)
                else:
                    args += (self._unpack_dicts(obj[key], key),)
            return JSON_INDEX[idx]._make(args)
        return obj

class Device(object):
    ''' docstring '''

    def __init__(self, device_data):
        #if device_data is None: # allocate to NullDevice
        #    self.data = _NullDevice # DeviceData('NullDevice', '', '', '', '', [], [], [])
        #else:
        self.data = device_data
        self.musiccast = (self.data.protocol == 'YEC')
        self.zones = []
        self.feeds = []
        # load the zones and feeds from the static data
        for zone_data in self.data.zones: self.zones.append(Zone(zone_data, self))
        for feed_data in self.data.feeds: self.feeds.append(Feed(feed_data))

    def init_musiccast(self):
        ''' docstring '''
        if self.musiccast:  # this is a MusicCast device
            self.online = False
            self.connection = mchttp.musiccastHttp(self.data.host)
            self.features = {}
            try: self.refresh_features()
            except mcx.mcError: pass # TODO: refine
        for zone in self.zones:
            zone.init_musiccast()

    def refresh_features(self):
        ''' Raises errors if the request fails.'''
        self.features.clear()
        self.features = self.connection.sendrequest('system', 'getFeatures')

class Feed(object):
    ''' docstring '''
    def __init__(self, feed_data):
        self.data = feed_data
        self.device = None

class Zone(object):
    ''' docstring '''

    msgl_out = None
    msgin = None
    arguments = {}
    response = {}

    def __init__(self, zone_data, device):
        self.data = zone_data
        self.device = device
        self.zonesource = None

    def init_musiccast(self):
        ''' docstring '''
        # MusicCast dependent members
        if self.device.musiccast:
            self.state = {'ready': False, 'power': False, 'input': '', 'volume': 0, 'mute': False}
            self.get_state()

    def get_state(self):
        ''' docstring '''
        self.state['ready'] = False
        # check first if features is updated
        if not self.device.features:
            try: self.device.refresh_features()
            except mcx.mcError as err:
                raise mcx.mcDeviceError(''.join(('The getFeatures structure can not updated.\n\t Error:', repr(err))))
        # find the zone in features
        fzone = [zone for zone in self.device.features['zone'] if zone['id'] == self.data.id]
        if not fzone:
            raise mcx.mcConfigError(''.join(('Zone ', self.data.id, ' in device ',
                                             self.device.data.id, 'not found in getFeatures.')))
        frange = [item for item in fzone[0]['range_step'] if item['id'] == 'volume'][0] # find the volume range
        self.volume_range = frange['max'] - frange['min']
        self.volume_min = frange['min']
        self.volume_step = frange['step']
        # Initialise fields with a 'getStatus'call
        try: status = self.device.connection.sendrequest(self.data.mc_id, 'getStatus')
        except mcx.mcError as err:
            raise mcx.mcDeviceError(''.join(('The getStatus information can not be retrieved.\n\t Error:', repr(err))))
        self.state['power'] = (status['power'] == 'on')
        self.state['input'] = status['input']
        self.state['volume'] = int(status['volume'] * 100 / self.volume_range)
        self.state['mute'] = (status['mute'] == 'true')
        self.state['ready'] = True

    def load_msg(self, msg):
        '''
        Unpacks arguments coming from the mapping engine
        and transform them to the MusicCast protocol.

        iargs (as in 'internal representation of arguments') should be a
        dictionary whose keys are the name of the argument and their value is
        expressed in the 'internal' way, whatever that means (if it is a string, it
        will be the internal keyword for that value).
        This is a 'tolerant' method: errors are caught within the method, logged and silenced.
        '''
        Zone.msgin = msg
        Zone.arguments.clear()
        if msg.arguments is None: return # might be unnecessary, but just in case
        for arg in msg.arguments:
            # retrieve the function that transforms the argument from the
            # internal representation to the MusicCast one.
            try: func = mcdata.TRANSFORM_ARG[arg]
            except KeyError:
                _logger.info(''.join(('Argument ', str(arg), ' does not have a transformation. Discard.')))
                continue # ignore the argument if there is no transformation for it
            try: mc_arg = func(self, msg.arguments[arg])
            except ValueError: # this is probably the only error to catch from a transformation
                _logger.info(''.join(('Value ', str(msg.arguments[arg]), ' of argument ',
                                      str(arg), ' seems of the wrong type. Discard.')))
                continue # ignore the argument as it is probably badly formatted
            Zone.arguments[arg] = [msg.arguments[arg], mc_arg]

    def send_command(self, command, qualifier=None):
        ''' docstring '''
        Zone.response.clear()
        if qualifier is None: qualifier = self.data.mc_id
        _logger.debug(''.join(('send_command to device ', self.device.data.id)))
        Zone.response = self.device.connection.sendrequest(qualifier, command)
        return

    def send_reply(self, response, reason):
        ''' docstring '''
        imsg = Zone.msgin.copy()
        imsg.gateway = None
        imsg.device = self.device.data.id
        imsg.source = app.Properties.name
        Zone.msgl_out.append(imsg.reply(response, reason))
        return

    def set_power(self, power):
        ''' Sets the power of the zone.'''
        if not self.device.musiccast:
            raise mcx.mcLogicError(''.join(('The device ', self.device.data.id, ' is not MusicCast.')))
        cmdtxt = 'setPower?power={}'.format('on' if power else 'standby')
        self.send_command(cmdtxt)
        self.state['power'] = power
        self.send_reply('OK', ''.join(('power is ', 'on' if power else 'standby')))
        return

    def set_volume(self, up=None):
        ''' Sets the volume of the zone.'''
        if not self.device.musiccast:
            raise mcx.mcLogicError(''.join(('The device ', self.device.data.id, ' is not MusicCast.')))
        if not self.state['power']:
            raise mcx.mcLogicError(''.join(('The device ', self.device.data.id, ' is not turned on.')))
        if up is None:
            volume = max(min(Zone.arguments['volume'][1], self.volume_min),
                         (self.volume_min + self.volume_range))
            self.send_command(''.join(('setVolume?volume=', str(volume))))
        else:
            self.send_command(''.join(('setVolume?volume=', 'up' if up else 'down')))
            volume += (1 if up else -1) * self.volume_range
            volume = max(min(volume, self.volume_min), (self.volume_min + self.volume_range))
        self.state['volume'] = volume
        self.send_reply('OK', ''.join(('volume is ', str(volume))))
        return

    def set_mute(self, mute=None):
        ''' Sets the mute of the zone.'''
        if not self.device.musiccast:
            raise mcx.mcLogicError(''.join(('The device ', self.device.data.id, ' is not MusicCast.')))
        if not self.state['power']:
            raise mcx.mcLogicError(''.join(('The device ', self.device.data.id, ' is not turned on.')))
        self.send_command(''.join(('setMute?enable=', 'true' if mute else 'false')))
        self.state['mute'] = mute
        self.send_reply('OK', ''.join(('mute is ', 'on' if mute else 'off')))
        return

    def set_input(self, input_kwd=None):
        ''' Sets the input of the zone.

        This is a 'raw' (or deterministic) command, in the sense that it just switches the input
        of the current zone.  It does not matter if the input is actually a source
        or not.  No other action is performed, so if for example the input is a source
        on the same device and it needs to be started or tuned, this is not done here.
        '''
        if not self.device.musiccast:
            raise mcx.mcLogicError(''.join(('The device ', self.device.data.id, ' is not MusicCast.')))
        if not self.state['power']:
            raise mcx.mcLogicError(''.join(('The device ', self.device.data.id, ' is not turned on.')))
        if input_kwd is None: # check if the source is specified in the arguments dictionary
            try: input_args = Zone.arguments['input'] # source_args = [internal keyword, MusicCast keyword]
            except KeyError: raise mcx.mcSyntaxError('No input argument found in command.')
            input_mckwd = input_args[1]
        else: input_mckwd = mcdata.TRANSFORM_ARG['input'](self, input_kwd)
        self.send_command(''.join(('setInput?input=', input_mckwd)))
        self.state['input'] = input_mckwd
        self.send_reply('OK', ''.join(('input is ', input_mckwd)))
        return

    def set_source(self, source_kwd=None):
        '''
        source_kwd = source keyword in internal vocabulary

        This command is expected to be 'smart', in the sense that the source
        keyword...
        The algorithm checks first if the source is present, valid and available.
        Once the device with that source is found, check if it is MusicCast,
        and if so try to 'lock' it (e.g. turn it on). If successfully, check if
        the amplifying device is also MusicCast, and if so switch the input
        accordingly.
        '''
        if source_kwd is None: # check if the source is specified in the arguments dictionary
            try: source_args = Zone.arguments['source'] # source_args = [internal keyword, MusicCast keyword]
            except KeyError: raise mcx.mcSyntaxError('No source argument found.')
            source_kwd = source_args[0]
        # check if the wanted source is available on the same device
        for source in self.device.data.sources:
            if source_kwd == source.id: # source found
                if self.device.musiccast:
                    self.set_input(source.mc_id) # change the input to the source
                    self.state['input'] = source.mc_id # update internal state
                    self.zonesource = self
                    #self.send_reply('OK', '') # the reply is already sent by set_input
                    return
                else: # the current device also plays the source but it is not MusicCast
                    raise mcx.mcLogicError(''.join(('Can''t set source ', source_kwd,
                                                    ' on non MusicCast device ', self.device.data.id)))
        # source not found on the same device, look for it in all devices connected to the feeds
        devicelist = [feed.device for feed in self.device.feeds\
                      for source in feed.device.data.sources if source.id == source_kwd]
        # devicelist is a list of all devices who have a source which is source_kwd
        if not devicelist: # there are no devices that can play this source
            raise mcx.mcError(''.join(('Source ', source_kwd,
                                       ' cannot be found anywhere.\n\t\
                                        Could be a syntax issue or a configuration issue.')))
        mc_devicelist = [device for device in devicelist if device.musiccast]
        # mc_devicelist is the sub-list of MusicCast devices only
        foundzone = None
        for dev in mc_devicelist:
            # check if any zone is already on and playing what
            zones_on = [zone for zone in dev.zones if zone.state['power']]
            if not zones_on: # all zones are off, use the first zone on that device
                foundzone = dev.zones[0]
                break
            else: # check if any zone is playing the same source
                zones_same = [zone for zone in zones_on if zone.state['input'] == source_kwd]
                if zones_same: # there is a zone playing the same source, use the first one
                    foundzone = zones_same[0]
                    break
                else: # no zone playing this source and the device is on; skip to next one
                    continue
        if foundzone is None: # no MusicCast device found that plays the source
            nonmc_devicelist = [device for device in devicelist if not device.musiccast]
            if nonmc_devicelist: # there are non MusicCast devices playing the source
                #self.devsource = nonmc_devicelist[0] # pick the first one (and pray...)
                pass
            else:
                # one could adapt the message depending if all MusicCast are busy or non-existent here...
                raise mcx.mcError(''.join(('Source ', source_kwd,
                                           ' cannot be played by any available MusicCast device.')))
        else: # send the commands to the zone found that plays the source
            self.zonesource = foundzone
            if not foundzone.state['power']: # only send commands if the zone is not already playing
                foundzone.set_power(True) # turn on the zone
                mc_id = [source.mc_id for source in foundzone.device.data.sources if source.id == source_kwd][0]
                # mc_id must be there and we take the first element of the comprehension list
                foundzone.set_input(mc_id) # set the right input
        # data on source is successfully updated, deal with the current device now
        if self.device.musiccast:
            foundinput = [feed for feed in self.device.feeds\
                          if feed.data.device_id == self.zonesource.device.data.id][0]
            self.set_input(foundinput.data.mc_id)

    def set_playback(self, action, source_kwd=None):
        ''' docstring '''
        if not self.zonesource:
            raise mcx.mcLogicError(''.join(('No zonesource defined in zone ', self.data.id,
                                            ' of device ', self.device.data.id)))
        zone = self.zonesource
        if not zone.device.musiccast:
            raise mcx.mcLogicError(''.join(('The device ', zone.device.data.id, ' is not MusicCast.')))
        if not zone.state['power']:
            raise mcx.mcLogicError(''.join(('The device ', zone.device.data.id, ' is not turned on.')))
        if source_kwd is None: source_mcid = zone.state['input']
        else:
            source_mcid = mcdata.TRANSFORM_ARG['input'](zone, source_kwd)
        if source_mcid != zone.state['input']:
            raise mcx.mcError(''.join(('Can''t execute action ', action, ' for source ', source_kwd,
                                       ' while device ', zone.device.data.id,
                                       ' is playing input ', zone.state['input'])))
        zone.send_command(''.join(('setPlayback?playback=', action)), source_mcid)
        zone.send_reply('OK', ''.join(('playback set to ', action)))

    def set_preset(self, source_mcid):
        ''' docstring

        source_mcid should be the mc_id of the source
        '''
        if source_mcid not in ('tuner', 'net_radio'): return
        if not self.zonesource:
            raise mcx.mcLogicError(''.join(('No zonesource defined in zone ', self.data.id,
                                            ' of device ', self.device.data.id)))
        zone = self.zonesource
        if not zone.device.musiccast: raise mcx.mcLogicError(''.join(('The device ', zone.device.data.id,
                                                                      ' is not MusicCast.')))
        if not zone.state['power']:
            raise mcx.mcLogicError(''.join(('The device ', zone.device.data.id, ' is not turned on.')))
        if zone.state['input'] != source_mcid:
            raise mcx.mcError(''.join(('Can''t preset tuner while device ', zone.device.data.id,
                                       ' is playing input ', zone.state['input'])))
        if source_mcid == 'tuner':
            try: preset_type = zone.device.features['tuner']['preset']['type']
            except KeyError: raise mcx.mcConfigError('Can''t read the tuner preset type in the features.')
            if preset_type == 'common': band = 'common'
            elif preset_type == 'separate': band = 'dab' # for now that's the only preset we want to use. TODO: refine.
            else: raise mcx.mcDeviceError(''.join(('Unknown preset type ', preset_type)))
            bandtxt = '&band={}'.format(band)
            qualifier = 'tuner'
        else:
            bandtxt = ''
            qualifier = 'netusb'
        try: max_presets = int(zone.device.features[qualifier]['preset']['num'])
        except (ValueError, KeyError): raise mcx.mcConfigError('Can''t read the tuner max presets in the features.')
        try: preset_num = Zone.arguments['preset'][0] # preset_num = [internal keyword (int), MusicCast keyword (str)]
        except KeyError: raise mcx.mcSyntaxError('No preset argument found.')
        if preset_num < 1 or preset_num > max_presets:
            raise mcx.mcLogicError(''.join(('Preset ', str(preset_num), ' is out of range.')))
        cmdtxt = 'recallPreset?zone={}{}&num={:d}'.format(zone.data.id, bandtxt, preset_num)
        zone.send_command(cmdtxt, qualifier)
        zone.send_reply('OK', ''.join(('preset ', source_mcid, ' to number ', str(preset_num))))

    def str_state(self):
        ''' docstring '''
        return ''.join(([''.join(('\n\t', key, ': ', str(self.state[key]))) for key in self.state]))

    def str_zone(self):
        ''' docstring '''
        return ''.join((self.device.data.id, '.', self.data.id))
