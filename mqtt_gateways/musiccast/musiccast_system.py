'''
Representation of the Audio-Video system, including non-MusicCast devices.

The initialisation process is separated in 2 steps:

#. Load the static data from a JSON file into a local hierarchy made of
   a single system with devices that each have zones, sources and feeds.

#. Attempt to retrieve *live* data from all the MusicCast devices
   and initialise various parameters based on this data.  In case of failure,
   the retrieval of the information is delayed and the functionality of the
   device is not available until it goes back *online*.

The execution of a command is triggered by a lambda function retrieved from the
ACTIONS dictionary (done within the loop in the `musiccast_interface` module).
These lambda functions are methods called from a :class:`Zone` objects that
perform all the steps to execute these actions, including sending the actual
requests to the devices over HTTP (through the `musiccast_comm` module).

'''

import time
import copy

import mqtt_gateways.musiccast.musiccast_exceptions as mcx
import mqtt_gateways.musiccast.musiccast_comm as mcc
from mqtt_gateways.musiccast.musiccast_data import TRANSFORM_ARG, EVENTS

import mqtt_gateways.utils.app_properties as app
_logger = app.Properties.get_logger(__name__)

_INIT_LAG = 600 # seconds, time between re-trials to initialise MusicCast devices
_BUFFER_LAG = 0.5 # seconds, minimum lag between a request and a status refresh
_STALE_CONNECTION = 300 # seconds, maximum time of inactivity before Yamaha API stops sending events

class System(object):
    '''Root of the audio-video system.

    This class initiates first the process of loading the *static* data into
    local attributes from the JSON file.  Some checks are performed.
    Configuration errors coming from a bad description of the system in the file
    are fatal.

    Then it initiates the process of retrieving MusicCast parameters from the
    MusicCast devices through HTTP requests.  In case of connection errors, the
    device concerned is put in a *not ready* state, and its update delayed.

    The initialisation process also starts the events listener, which is unique
    across all MusicCast devices.

    Args:
        json_data (string): JSON valid code describing the system.
            Check it against the available schema.
        msgl (MsgList object): the outgoing message list

    Raises:
        Any of AttributeError, IndexError, KeyError, TypeError, ValueError:
            in case the unpacking of the JSON data fails, for whatever reason.
    '''

    def __init__(self, json_data, msgl):

        # Initialise the events listener.
        listen_port = 41100 # TODO: check what port to use
        mcc.set_socket(listen_port)

        # Assign locally the message attributes
        self.msgl = msgl
        self.msgin = None
        self.msgout = None
        self.arguments = {}

        # Create the list of devices; this unwraps the whole JSON structure
        devices = []
        for device_data in json_data['devices']:
            devices.append(Device(device_data, self))
        self.devices = tuple(devices)
        self.mcdevices = tuple([dev for dev in devices if dev.musiccast])
        self.devicemcid_dict = {}
        for dev in self.mcdevices:
            self.devicemcid_dict[dev.mcid] = dev
        self.deviceyamid_dict = {} # updated within Device.load_musiccast method

        # Find the device connected to each feed once and for all.
        for dev in self.devices:
            for feed in dev.feeds:
                try: feed.remote_dev = [x for x in self.devices
                                        if x.id == feed.remote_dev_id][0]
                except IndexError: # device for that feed was not found
                    _logger.info(''.join(('Device ', feed.remote_dev_id,
                                          ' not defined.')))
                    feed.remote_dev = None

        # Now we can initialise MusicCast related fields
        for dev in self.mcdevices: dev.load_musiccast()

    def refresh(self):
        ''' Performs various periodic checks and refreshers.
        
        Refresh: refresh cycle, only certain requests trigger a cycle,
        otherwise it is the lag.
        
        '''
        for dev in self.mcdevices: dev.refresh()
            
    def load_msg(self, msg):
        '''
        Load locally internal message coming from the mapping engine.

        Load message, unpack arguments and transform them to the MusicCast
        protocol for easy access later by the lambda functions. The arguments in
        `msg.arguments` are strings of *internal* keywords. They need to be
        transformed into a MusicCast format (even it is only really needed for
        values like volume or booleans). The *local* dictionary `self.arguments`
        contains the same keys as `msg.arguments` but with transformed values.
        '''
        self.msgin = msg
        self.arguments.clear()
        if not msg.arguments: return
        for arg in msg.arguments: # copy arguments
            self.arguments[arg] = msg.arguments[arg]

    def reply(self):
        return self.msgout

    def listen_musiccast(self):
        ''' Checks if a MusicCast event has arrived and parses it.
        
        This method uses the dictionary EVENTS based on all possible fields that
        a MusicCast can have (see Yamaha doc for more details).  This
        dictionary has only 2 levels and every 'node' is either a dict or a
        callable.  Any *event* object received from a MusicCast device should
        have a structure which is a subset of the EVENTS one.  The algorithm
        goes through the received *event* structure in parallel of going through
        the EVENTS one.  If there is a key mismatch, the specific key in *event*
        that cannot find a match in EVENTS is ignored.  If there is a key match,
        the lambda function found as value of that key in EVENTS is called with
        the value of that same key found in *event* (the *argument*).
        
        TODO: check if more than one event could be received in a single call.
        '''

        event = mcc.get_event() # event is a dictionary. see Yamaha doc.
        if event is None: return

        # Find device within the event dictionary
        device_id = event.pop('device_id', None) # read and remove key
        if device_id is None:
            mcx.CommsError('Event has no device_id. Discard event.')
        try: device = self.deviceyamid_dict[device_id]
        except KeyError:
            raise mcx.ConfigError(''.join(('device_id <', str(device_id),
                                           '> not found. Discard event.')))

        # Read event dictionary and call lambda for each key match found
        flist = [] # list of all lambdas to call; the elements are pairs (func, arg)
        for key1 in event:
            try: isdict = isinstance(EVENTS[key1], dict) 
            except KeyError:
                _logger.info(''.join(('Event has an unknown item <',
                                              str(key1), '>. Ignore item.')))
                continue
            if isdict:
                if not isinstance(event[key1], dict):
                    raise mcx.ConfigError('Unexpected structure of event. Discard event.')
                for key2 in event[key1]:
                    try: func = EVENTS[key1][key2]
                    except KeyError:
                        _logger.info(''.join(('Event has an unknown item <',
                                              str(key2), '>. Ignore.')))
                        continue
                    if func is not None:
                        arg = event[key1][key2]
                        flist.append((func, arg))
            else:
                func = EVENTS[key1]
                if func is not None:
                    arg = event[key1]
                    flist.append((func, arg))
        # now execute the lambdas
        while True:
            try: func, arg = flist.pop(0)
            except IndexError: break
            try: func(device, arg)
            except mcx.AnyError as err:
                _logger.info(''.join(('Problem with token in event. Ignore. Error:\n\t',
                                      repr(err))))

class Device(object):
    ''' Represents a device in the audio-video system.

    Most methods are used by the lambdas to deal with the incoming events.
    Events arrive with a device identifier.

    Args:
        device_data (JSON string): a JSON type string representing a device.
        system (System object): the parent system of this device.
    '''

    def __init__(self, device_data, system):
        self.system = system
        self.id = device_data['id']
        self.model = device_data.get('model', None)
        self.protocol = device_data.get('protocol', None)
        self.gateway = device_data.get('gateway', None)
        self.musiccast = (self.protocol == 'YEC')
        if self.musiccast: self.host = device_data['host']
        else: self.host = device_data.get('host', None)
        # Load the zones, feeds and sources from the static data.
        zones = []
        for zone_data in device_data['zones']:
            zones.append(Zone(zone_data, self))
        self.zones = tuple(zones)
        feeds = []
        for feed_data in device_data['feeds']:
            feeds.append(Feed(feed_data, self))
        self.feeds = tuple(feeds)
        sources = []
        for source_data in device_data['sources']:
            sources.append(Source(source_data, self))
        self.sources = tuple(sources)
        # MusicCast related attributes
        if self.musiccast:  # this is a MusicCast device
            self.ready = False
            self.conn = mcc.musiccastComm(self.host)
            self.dev_info = None
            self.features = None
            # dictionaries to help, initialised in load_musiccast
            self.mcinfotype_dict = {}
            self.mczone_dict = {}
            self.mcsource_dict = {}
            # refresh related attribute
            self.zone_index = 0
            self.zone_num = len(self.zones)

    def mcready(self):
        ''' Returns True is the device is MusicCast ready to be operated.'''
        return self.musiccast and self.ready

    def load_musiccast(self):
        '''Initialisation of MusicCast related characteristics.
        
        This method will make HTTP requests to all relevant devices,  In case of failure, the device
        `ready` attribute is simply left `False` and the device will not be available to be
        operated. This method can be called again at any time to try again this initialisation.
        
        Returns:
            boolean: True is initialisation succeeded
        '''
        if self.ready: return True # ready already!
        try:
            if not self.dev_info:
                self.dev_info = self.conn.mcrequest('system', 'getDeviceInfo')
            self.system.deviceyamid_dict[self.dev_info['device_id']] = self
            if not self.features:
                self.features = self.conn.mcrequest('system', 'getFeatures')
            for zone in self.zones:
                zone.load_musiccast()
                self.mczone_dict[zone.mcid] = zone
            for source in self.sources:
                source.load_musiccast()
                self.mcsource_dict[source.mcid] = source    
        except mcx.CommsError as err:
            _logger.info(''.join(('Cannot initialise MusicCast device ',
                                  self.id,
                                 '. Error:\n\t', repr(err))))
            return False
        except mcx.ConfigError as err:
            # These are unrecoverable errors
            _logger.info(''.join(('MusicCast device ', self.id,
                                  ' has to be disabled. Error:\n\t', repr(err))))
            #self.musiccast = False # TODO: remove from mcdevices list then! or do something else
            return False
        # success
        self.ready = True
        _logger.debug(''.join(('MusicCast initialisation of device ',
                               self.id, ' completed successfully.')))
        return True

    def init_infotype(self, play_info_type):
        ''' Returns a new or an existing instance of PlayInfo.

        Args:
            play_info_type (string): one of **tuner**, **cd**, or **netusb**.

        Raises:
            ConfigError: if the play_info_type is not recognised.
        '''
        if play_info_type in self.mcinfotype_dict:
            return self.mcinfotype_dict[play_info_type]
        if play_info_type == 'tuner':
            self.mcinfotype_dict[play_info_type] = Tuner(self)
            return self.mcinfotype_dict[play_info_type]
        elif play_info_type == 'cd':
            self.mcinfotype_dict[play_info_type] =  CD(self)
            return self.mcinfotype_dict[play_info_type]
        elif play_info_type == 'netusb':
            self.mcinfotype_dict[play_info_type] = NetUSB(self)
            return self.mcinfotype_dict[play_info_type]
        else:
            raise mcx.ConfigError(''.join(('PlayInfoType <', play_info_type, ' does not exist.')))

    def find_infotype(self, play_info_type):
        ''' Retrieves the info_type instance.'''
        try: return self.mcinfotype_dict[play_info_type]
        except KeyError:
            raise mcx.ConfigError(''.join(('InfoType <', play_info_type, '> not found.')))

    def find_mczone(self, mcid):
        ''' Returns the MusicCast zone from its id.

        Args:
            mcid (string): MusicCast id of the zone.  Normally one of 'main,
                zone2, zone3, zone4'.  See list _ZONES.

        Raises:
            ConfigError: if the zone is not found, either because it is not a
                valid zone or because it does not exist in this device.
        '''
        try: return self.mczone_dict[mcid]
        except KeyError:
            raise mcx.ConfigError(''.join(('MusicCast zone ', mcid,
                                           ' not found in device ', self.id, '.')))

    def find_mcsource(self, mcid):
        ''' Returns the MusicCast source from its id.
        
        Args:
            mcid (string): MusicCast id of the source.  Normally a subset from the list _SOURCES.

        Raises:
            ConfigError: if the zone is not found, either because it is not a valid zone or because
                it does not exist in this device.
        '''
        try: return self.mcsource_dict[mcid]
        except IndexError:
            raise mcx.ConfigError(''.join(('MusicCast source ', mcid,
                                           ' not found in device ', self.id, '.')))

    def refresh(self):
        ''' Refresh status of device.
        
        There are 2 reasons why one needs to refresh the status of a device:
        
        1- because the MusicCast devices need to receive at least one request every 10 minutes (with
        the right headers) so that they keep sending events;
        
        2- because this gateway has sent a **set** command and it is good to check if the command
        has indeed *delivered*.  It seems though that there is need to wait a bit before requesting
        a fresh status as experience shows that firing a **getStatus** request straight after a
        command does not reflect the change even if the command is supposed to be successful.
        
        '''
        now = time.time()
        # check if the device is online
        if not self.ready: # try to initialise MusicCast device at regular intervals
            if now - self.init_time > _INIT_LAG:
                self.load_musiccast()
            return # return anyway: if init was ok, nothing happened recently anyway
        # check if a request has been made *too* recently
        if now - self.conn.request_time < _BUFFER_LAG:
            return
        # check now if there are zones that have requested a status refresh
        for _count in range(self.zone_num):
            zone = self.zones[self.zone_index]
            self.zone_index = (self.zone_index + 1) % self.zone_num
            if zone.status_refresh: # status refresh has been requested
                _logger.debug('Refresh status on request.')
                zone.refresh_status()
                return
        # check if it is time to refresh the device so it keeps sending the events
        if now - self.conn.request_time > _STALE_CONNECTION:
            _logger.debug('Refreshing the connection after long inactivity.')
            zone = self.zones[self.zone_index]
            self.zone_index = (self.zone_index + 1) % self.zone_num
            zone.refresh_status()
            return

class Feed(object):
    ''' Represents an input on the device that is not a source.

    A feed within a MusicCast system is an input for which the `play_info_type`
    field within the getFeatures structure is set to **none**.

    Args:
        feed_data (JSON style structure): the **feed** characteristics.
        device (Device object): the parent device.
'''
    def __init__(self, feed_data, device):
        self.device = device
        self.id = feed_data['id']
        self.remote_dev_id = feed_data['device_id']
        self.remote_dev = None # assigned later when all devices initialised
        if self.device.musiccast: self.mcid = feed_data['mcid']

class Source(object):
    ''' Represents a source on the device.

    A source within a MusicCast system is an input for which the
    `play_info_type` field within the getFeatures structure is set to a
    different value than **none**, normally either **cd**, **tuner** or
    **netusb**.

    Args:
        source_data (JSON style structure): the **source** characteristics.
        device (Device object): the parent device.
    '''
    def __init__(self, source_data, device):
        self.device = device
        self.local_zone = None # the zone from same device that has its input set on this source
        self.id = source_data['id']
        if self.device.musiccast: self.mcid = source_data['mcid']
        self.usedby = []

    def load_musiccast(self):
        '''Initialisation of MusicCast related characteristics.
        
        This method uses the objects retrieved from previous HTTP requests.
        It can be called again at any time to try again this initialisation.
        '''
        try:
            for inp in self.device.features['system']['input_list']:
                if inp['id'] == self.mcid:
                    play_info_type = inp['play_info_type']
        except KeyError:
            mcx.CommsError('getFeatures object does not contain the keys '\
                           '<system>, <input_list>, <id> or <play_info_type>.')
        self.info = self.device.init_infotype(play_info_type)

    def current_local_zone(self):
        ''' Updates the 'local' zone for this source.
        
        Returns the zone object from the same device that has its input set on this source.
        If there is no zone with an input set to this source (i.e. this source is not playing on
        this device), it returns None.
        
        Returns:
            :class:Zone object: the zone playing that source, or None.
        '''
        for zone in self.device.zones:
            if zone.get_status_item('input') == self.mcid: return zone
        return None

class Zone(object):
    ''' Represents a zone on the device.

    Args:
        zone_data (JSON style structure): the **zone** characteristics.
        device (Device object): the parent device.
    '''
    def __init__(self, zone_data, device):
        self.device = device # a reference to the parent device
        self.id = zone_data['id']
        self.location = zone_data['location']
        self.amplified = (self.location != '')
        if self.device.musiccast:
            self.mcid = zone_data['mcid']
            self.zonesource = None # reference to the zone playing the source
            self.status = {}
            self.status_time = 0 # time of last successful status request
            self.status_refresh = False # set to True if the status needs to be refreshed

    def load_musiccast(self):
        '''Initialisation of MusicCast related characteristics.
        
        This method uses the objects retrieved from previous HTTP requests.
        It can be called again at any time to try again this initialisation.
        '''
        # find the zone in the features dictionary
        try:
            fzone = [zone for zone in self.device.features['zone']\
                      if zone['id'] == self.mcid][0]
        except (IndexError, KeyError) as err:
            raise mcx.ConfigError(''.join(('Cannot retrieve zone ', self.id, ' in device ',
                                           self.device.id, ' from getFeatures.\n\tError:',
                                           repr(err))))

        # find the volume range in fzone structure and set volume parameters.
        try:
            frange = [item for item in fzone['range_step']\
                       if item['id'] == 'volume'][0]
            self.volume_range = frange['max'] - frange['min']
            self.volume_min = frange['min']
            self.volume_step = frange['step']
        except (IndexError, KeyError):
            raise mcx.ConfigError(''.join(('Cannot retrieve volume information'\
                                           ' for zone ', self.id,
                                           ' in device ', self.device.id,
                                           ' from getFeatures.')))            
        
        # retrieve the status of the zone and store it locally
        self.refresh_status()

        # create source related dictionaries
        # dict of local source id -> source object
        self.localsrc = {}
        for src in self.device.sources:
            self.localsrc[src.id] = src
        # dict MusicCast remote sources id -> (source object, feed object)
        self.mcremotesrc = {}
        # dict non-MusicCast remote sources id -> (source object, feed object)
        self.nonmcremotesrc = {}
        for feed in self.device.feeds:
            if feed.remote_dev is None: continue # TODO: remove once feed is removed
            for src in feed.remote_dev.sources:
                if src.device.musiccast:
                    if src.id not in self.mcremotesrc:
                        self.mcremotesrc[src.id] = []
                    self.mcremotesrc[src.id].append((src, feed))
                else:
                    if src.id not in self.nonmcremotesrc:
                        self.nonmcremotesrc[src.id] = []
                    self.nonmcremotesrc[src.id].append((src, feed))

    def transform_arg(self, key, value):
        '''Transforms a message argument from internal to MusicCast.

        Args:
            key (string): internal name of argument.
            value (string): internal representation of the value.

        Returns:
            string: the MusicCast representation of the value.
        '''
        # Retrieve the function that transforms the argument from the
        #   internal representation to the MusicCast one.
        try: func = TRANSFORM_ARG[key]
        except KeyError:
            raise mcx.LogicError(
                ''.join(('Argument ', str(key),
                         ' does not have a transformation.')))
        try: mc_value = func(self, value)
        except (TypeError, ValueError): # errors to catch in case of bad format
            raise mcx.LogicError(
                ''.join(('Value ', str(value),' of argument ', str(key),
                         ' seems of the wrong type.')))
        return mc_value # ignore mc_key for now

    def refresh_status(self):
        ''' Retrieve the state of the zone and store it locally.'''
        old_status = copy.deepcopy(self.status)
        self.status = self.device.conn.mcrequest(self.mcid, 'getStatus')
        self.check_state(old_status)
        self.status_time = time.time()
        self.status_refresh = False

    def get_status_item(self, item):
        ''' Returns an item in the status dictionary
        
        Args:
            item (string): a valid key in the **status** dictionary.

        Raises:
            ConfigError: in case the item does not exist.
        
        Returns:
            string: the value of the item.
        '''
        if item not in self.status: # only allow existing keys
            raise mcx.ConfigError(''.join(('Item <', item,
                                           '> not a state item.')))
        return self.status[item]

    def update_status_item(self, item, value):
        ''' Updates an item in the status dictionary
        
        Args:
            item (string): a valid key in the **status** dictionary.
            value (string): the new value of item.

        Raises:
            ConfigError: in case the item does not exist.
        '''
        if item not in self.status: # only allow existing keys
            raise mcx.ConfigError(''.join(('Item <', item,
                                           '> not a state item.')))
        self.status[item] = value
        # TODO: one could request the status refresh here so that the events trigger it...

    def set_power(self, power):
        ''' Sets the power of the zone.

        Args:
            power (boolean): converted into 'on' or 'standby'.
        '''
        if not self.device.mcready():
            raise mcx.LogicError(''.join(('The device ', self.device.id,
                                          ' is not available.')))
        power_txt = 'on' if power else 'standby'
        cmdtxt = 'setPower?power={}'.format(power_txt)
        self.device.conn.mcrequest(self.mcid, cmdtxt)
        self.update_status_item('power', power_txt)
        self.status_refresh = True
        # TODO: update zone values, inputs, etc...?
        self.send_reply('OK', ''.join(('power is ', self.status['power'])))

    def power_on(self):
        ''' Helper function returning True if power of zone is ON.'''
        return self.status['power'] == 'on'

    def set_volume(self, up=None):
        ''' Sets the volume of the zone.

        Args:
            up (boolean): if given defines if volume is stepped up or down, if
              not then the volume to set has to be in the arguments.
        '''
        if not self.device.mcready():
            raise mcx.LogicError(''.join(('The device ', self.device.id,
                                          ' is not available.')))
        if not self.power_on():
            raise mcx.LogicError(''.join(('The device ', self.device.id,
                                          ' is not turned on.')))
        if up is None:
            try: volume = self.device.system.arguments['volume']
            except KeyError:
                raise mcx.LogicError('No volume argument found in command.')
            mc_volume = self.transform_arg('volume', volume)
            mc_volume = min(max(mc_volume, self.volume_min),
                            (self.volume_min + self.volume_range))
            self.device.conn.mcrequest(self.mcid,
                                       ''.join(('setVolume?volume=',
                                                str(mc_volume))))
        else:
            self.device.conn.mcrequest(self.mcid,
                                       ''.join(('setVolume?volume=',
                                                'up' if up else 'down')))
            # calculate volume level to update locally
            mc_volume = self.status['volume']
            mc_volume += (1 if up else -1) * self.volume_step
            mc_volume = min(max(mc_volume, self.volume_min),
                            (self.volume_min + self.volume_range))
        self.update_status_item('volume', mc_volume)
        self.status_refresh = True
        self.send_reply('OK', ''.join(('volume is ', str(mc_volume))))
        # TODO: we need a reverse transformation here...

    def set_mute(self, mute):
        ''' Sets the mute property of the zone.

        Args:
            mute (boolean): converted into 'true' or 'false'
        '''
        if not self.device.mcready():
            raise mcx.LogicError(''.join(('The device ', self.device.id,
                                          ' is not available.')))
        if not self.power_on():
            raise mcx.LogicError(''.join(('The device ', self.device.id,
                                          ' is not turned on.')))
        mute_txt = 'true' if mute else 'false'
        self.device.conn.mcrequest(self.mcid,
                                   ''.join(('setMute?enable=', mute_txt)))
        self.status['mute'] = mute_txt
        self.status_refresh = True
        self.send_reply('OK', ''.join(('mute is ', mute_txt)))

    def set_input(self, input_id=None):
        ''' Sets the input of the zone.

        This methods simply switches the input of the current zone.  It does
        not matter if the input is a source or not.  No other action is
        performed, so if for example the input is a source on the same device
        and it needs to be started or tuned, this is not done here.
        
        Args:
            input_id (string): 
        '''
        if not self.device.mcready():
            # TODO: assume the command works anyway and set the input accordingly in the status?
            raise mcx.LogicError(''.join(('The device ', self.device.id,
                                          ' is not available.')))
        if not self.power_on():
            raise mcx.LogicError(''.join(('The device ', self.device.id,
                                          ' is not turned on.')))
        if input_id is None: # check if the source is in the arguments
            try: input_id = self.device.system.arguments['input']
            except KeyError:
                raise mcx.LogicError('No input argument found in command.')
        input_mcid = self.transform_arg('input', input_id)
        self.device.conn.mcrequest(self.mcid,
                                   ''.join(('setInput?input=', input_mcid)))
        self.update_status_item('input', input_mcid)
        self.status_refresh = True
        self.send_reply('OK', ''.join(('input is ', input_mcid)))

    def _update_usedby_lists(self, source=None):
        ''' Updates the new source selection for all available sources.
        
        Args:
            source (Source object): the new source used by this zone; if None,
                this method only removes all existing links to it (even if
                there should be only one existing link at maximum).
        '''
        # Remove the zone from any possible source usedby list
        anysrc = []
        anysrc.extend(self.device.sources)
        anysrc.extend([src for feed in self.device.feeds\
                       for src in feed.device.sources])
        _logger.debug(''.join(('usedby_lists - anysrc= ', str(anysrc))))
        for src in anysrc:
            if self in src.usedby: src.usedby.remove(self)
        # now add the zone to the new source
        if source is not None: source.usedby.append(self)

    def get_zoneofsource(self, source_id):
        ''' Returns the Zone from which the source is playing
        
        Only valid for a device playing the source that is MusicCast. 
        '''
        # assuming all devices are MusicCast
        # check the current device first
        for zone in self.device.zones:
            if source_id == self.get_status_item('input'): # TODO: Problem between id and mcid!!!
                return zone
        # TODO: to finish!!!!!!

    def set_source(self, source_id=None):
        ''' Sets the source for the current zone, if available.
        
        Args:
            source_id (string): source keyword in internal vocabulary.

        This command is complex and involves a lot of decision making if it
        needs to take into account the most diverse set-ups. In most cases,
        every amplified zone will only have one choice per source, and if that
        source is unavailable for any reason (because the device it comes from
        is playing another source for another zone, for example), then there is
        nothing else to do and the command fails. But this method wants also to
        take care of the more complicated cases, where a zone has multiple
        option to select a given source, so that if one is unavailable it can
        choose another one.

        Also, this command has to deal with the case where the zone making the
        call is not a MusicCast one. That is because the source it will connect
        to might be MusicCast and has to be processed by this command.
        Therefore, all the following cases are possible:
        
        - zone and source are non MusicCast devices: do nothing;
        - zone and source are on same MusicCast device: easy;
        - zone is MusicCast but source is not: less easy;
        - zone and source are different but both MusicCast: a bit tricky;
        - zone is not MusicCast but source is: a bit of a pain...

        Finally, dealing with the source is complicated by the fact that the
        command should not grab the source requested without checking first if
        it is already used by another zone.
        
        The algorithm checks first if a source is present, valid and
        available. Once the device with that source is found, check if it is
        MusicCast, and if so try to 'lock' it (e.g. turn it on). If
        successfully, check if the amplifying device is also MusicCast, and if
        so switch the input accordingly.
        '''
        # Resolve source_id
        if source_id is None: # check if the source is in the arguments 
            try: source_id = self.device.system.arguments['source']
            except KeyError: raise mcx.LogicError('No source argument found.')
        _logger.debug(''.join(('set_source - source_id = ', str(source_id))))
        # Priority 1: find the source on the same device.
        #   The search is made on the internal keyword, not the MusicCast one,
        #   as we might be on a non MusicCast zone.
        if source_id in self.localsrc:
            src = self.localsrc[source_id]
            if self.device.mcready():
                _logger.debug('set_source - source found on same device')
                self.set_input(src.mcid)
                self.zonesource = self
                self._update_usedby_lists(src)
                return
            else:
                raise mcx.LogicError(''.join(('Cannot set source ',
                                              source_id,
                                              ' on device ',
                                              self.device.id, '.')))
        _logger.debug('set_source - source not found on same device')
        # Source not found on the same device.
        #   Look for source in all devices connected to the feeds.
        #   Priority 2: prefer MusicCast devices.
        if source_id in self.mcremotesrc:
            # Priority 2a: join a source that is already playing.
            for item in self.mcremotesrc[source_id]:
                src = item[0]
                if src.usedby: # usedby list not empty, it is playing: join it
                    feed = item[1]
                    self.set_input(feed.mcid)
                    self.zonesource = src.usedby[0].zonesource
                    self._update_usedby_lists(src)
                    _logger.debug(''.join(('set_source - join zonesource ',
                                           str(self.zonesource.id),
                                           ' on feed ', feed.mcid)))
                    return
            # At this stage, no source is already playing.
            # Find the first source with a free 'conduit' zone.
            #   We decide not to use sources which are on devices with purely
            #   amplifying zones, because that would mean switching ON a zone
            #   which is a location that has not asked to be changed.
            for item in self.mcremotesrc[source_id]:
                src = item[0]
                zonelist = [zone for zone in src.device.zones
                            if not zone.amplified]
                _logger.debug(''.join(('set_source - zonelist: ',
                                       str(zonelist))))
                # zonelist is the list of 'conduit' zones in that device.
                #   Usually there is 1 at most but let's imagine there are more.
                for zone in zonelist:
                    # Only use if it is off. If it is ON, it is being used by
                    #   another source otherwise it would have been captured
                    #   before.
                    if not zone.power_on():
                        feed = item[1]
                        zone.set_power(True)
                        zone.set_input(feed.mcid)
                        self.zonesource = zone
                        self._update_usedby_lists(src)
                        _logger.debug(''.join(('set_source - use zone: ', zone.id, ' on feed ', feed.mcid)))
                        return
        # At this stage there are no usable MusicCast ready sources to use.
        # We care to find a non-MusicCast source only to set the right input
        #   on the current zone, but if it is not MusicCast ready, we do not
        #   care anyway and we can leave.
        if not self.device.mcready():
            raise mcx.LogicError(''.join(('No MusicCast ready source ',
                                          source_id,
                                          ' found for this non-MusicCast'\
                                          ' zone.')))
        if source_id not in self.nonmcremotesrc:
            raise mcx.LogicError(''.join(('Source ', source_id,
                                          ' cannot be found for this zone.')))
        for item in self.nonmcremotesrc[source_id]:
            src = item[0]
            if src.usedby:
                feed = item[1]
                break
            src = None
        if src is None: # no source found already playing, take the first one
            src = self.nonmcremotesrc[source_id][0][0]
            feed = self.nonmcremotesrc[source_id][0][1]
        self.set_input(feed.mcid)
        self.zonesource = None # it doesnt matter as it isnt a MusicCast device
        self._update_usedby_lists(src)
        _logger.debug(''.join(('set_source - use feed ', feed.mcid)))

    def set_playback(self, action, source_id=None):
        '''Triggers the specified playback action.

        To be able to play a source, it has to be selected first, so that
        the attribute `zonesource` is defined properly.
        The zone `zonesource` is expected to be MusicCast otherwise nothing can
        be done anyway.

        
        Args:
            action (string): the action to send to the MusicCast device.
            source_id (string): the internal keyword of the source to be
                played, if supplied, otherwise it is expected to be in the
                arguments.
        '''

        # Basic checks first...
        if not self.zonesource:
            raise mcx.LogicError(''.join(('No zonesource defined in zone ',
                                          self.id, ' of device ',
                                          self.device.id)))
        zone = self.zonesource
        if not zone.device.mcready():
            raise mcx.LogicError(''.join(('The device ', zone.device.id,
                                          ' is not available.')))
        if not zone.power_on():
            raise mcx.LogicError(''.join(('The device ', zone.device.id,
                                          ' is not turned on.')))

        # Check that the source is already selected on this zone.
        # Retrieve first the source...
        if source_id is None: # check if the source is in the arguments
            try: source_id = self.device.system.arguments['source']
            except KeyError:
                raise mcx.LogicError('No source argument found in command.')
        source_mcid = self.transform_arg('source', source_id)
        # ...and check the input.
        if source_mcid != zone.status['input']:
            raise mcx.LogicError(''.join(('Can''t execute action ', action,
                                          ' for source ', source_id,
                                          ' while device ', zone.device.id,
                                          ' is playing input ',
                                          zone.status['input'], '.')))
        # Check that this zone is allowed to operate this source.
        # First retrieve the source object for this source_mcid
        source = zone.device.find_mcsource(source_mcid)
        if not source.usedby: # This should never happen; if so, it's a bug
            raise mcx.ConfigError(''.join(('Source ', source_mcid,
                                           ' in device ', zone.device.id,
                                           ' has an empty usedby list.')))
        if zone != source.usedby[0]:
            raise mcx.LogicError('Not allowed to operate this source.')
        # Now we can send the command.
        mcaction = self.transform_arg('action', action)
        zone.device.conn.mcrequest(source.play_info_type,
                                   ''.join(('setPlayback?playback=', mcaction)))
        zone.send_reply('OK', ''.join(('playback set to ', action)))

    def set_preset(self,  source_id=None):
        '''Set the preset specified in the arguments for the source.

        Args:
            action (string): the action to send to the MusicCast device.
            source_id (string): the internal keyword of the source to be
                preset, if supplied, otherwise it is expected to be in the
                arguments.  It can only be **tuner** or **netusb**.
        '''
        if not self.zonesource:
            raise mcx.LogicError(''.join(('No zonesource defined in zone ',
                                          self.id, ' of device ',
                                          self.device.id)))
        # Retrieve first the source.
        if source_id is None: # check if the source is in the arguments
            try: source_id = self.device.system.arguments['source']
            except KeyError:
                raise mcx.LogicError('No source argument found in command.')
        source_mcid = self.transform_arg('source', source_id)

        if source_mcid not in ('tuner', 'net_radio'):
            raise mcx.LogicError(''.join(('Source ', source_mcid,
                                          ' does not have presets.')))

        zone = self.zonesource
        if not zone.device.mcready():
            raise mcx.LogicError(''.join(('The device ', zone.device.id,
                                          ' is not available.')))
        if not zone.power_on():
            raise mcx.LogicError(''.join(('The device ', zone.device.id,
                                          ' is not turned on.')))
        if zone.status['input'] != source_mcid:
            raise mcx.LogicError(''.join(('Can''t preset ', source_mcid,
                                          ' while device ', zone.device.id,
                                          ' is playing input ',
                                          zone.status['input'], '.')))
        # Check that this zone is allowed to operate this source.
        zlist = zone.device.find_mcsource(source_mcid).usedby
        if not zlist: # This should never happen; if it does, it is a bug
            raise mcx.ConfigError(''.join(('Source ', source_mcid,
                                           ' in device ', zone.device.id,
                                           ' has an empty usedby list.')))
        if zone != zlist[0]:
            raise mcx.LogicError('Not allowed to operate this source.')
        if source_mcid == 'tuner':
            # TODO: load various characteristics in load_musiccast
            try: preset_type = zone.device.features['tuner']['preset']['type']
            except KeyError:
                raise mcx.LogicError('Cannot read the tuner preset type'\
                                     ' in the features.')
            if preset_type == 'common': band = 'common'
            else: # assume (preset_type == 'separate') as the only other option 
                band = 'dab' # for now that's the only preset we want to use.
                # TODO: include other bands selection.
            bandtxt = '&band={}'.format(band)
            qualifier = 'tuner'
        else: # source_mcid == 'net_radio'
            bandtxt = ''
            qualifier = 'netusb'
        try: max_presets = int(zone.device.features[qualifier]['preset']['num'])
        except (ValueError, KeyError):
            raise mcx.LogicError('Cannot read the tuner max presets in'\
                                 ' the features.')
        try: preset_num = int(self.arguments['preset'])
        except (KeyError, ValueError):
            raise mcx.LogicError('No valid preset argument found.')
        if preset_num < 1 or preset_num > max_presets:
            raise mcx.LogicError(''.join(('Preset ', str(preset_num),
                                          ' is out of range.')))
        cmdtxt = 'recallPreset?zone={}{}&num={:d}'.format(zone.id,
                                                          bandtxt, preset_num)
        zone.device.conn.mcrequest(qualifier, cmdtxt)
        zone.send_reply('OK', ''.join(('preset ', source_mcid,
                                       ' to number ', str(preset_num))))

    def str_status(self):
        ''' Returns the full status dictionary.'''
        return ''.join(([''.join(('\n\t\t\t', key, ': ',str(self.status[key])))
                         for key in self.status]))

    def str_zone(self):
        '''Returns the identification of a zone.'''
        return ''.join((self.device.id, '.', self.id))

    def dump_zone(self):
        '''Returns most characteristics of a zone.'''
        lst = []
        lst.append('ZONE ')
        lst.append(self.str_zone())
        lst.append('\n\tZonesource present: ')
        lst.append('Yes' if self.zonesource else 'No')
        if self.zonesource:
            lst.append('\n\t\tZonesource is: ')
            lst.append(self.zonesource.str_zone())
        lst.append('\n\tIs MusicCast? ')
        lst.append('Yes' if self.device.musiccast else 'No')
        lst.append('\n\t\tMusicCast id: ')
        lst.append(str(self.mcid))
        lst.append('\n\t\tState is')
        lst.append(self.str_status())
        return ''.join(lst)

    def check_state(self, old_status):
        ''' Compare status. Only for debug purposes. '''
        try:
            _logger.debug(''.join(('power: ', str(self.status['power']),
                                   ' vs old ', str(old_status['power']))))
            _logger.debug(''.join(('input: ', str(self.status['input']),
                                   ' vs old ', str(old_status['input']))))
            _logger.debug(''.join(('volume: ', str(self.status['volume']),
                                   ' vs old ', str(old_status['volume']))))
            _logger.debug(''.join(('mute: ', str(self.status['mute']),
                                   ' vs old ', str(old_status['mute']))))
        except KeyError:
            _logger.debug('check_state failed.')

    def send_reply(self, response, reason):
        ''' docstring '''
        #=======================================================================
        # imsg = self.device.system.copy()
        # imsg.gateway = None
        # imsg.device = self.device.data.id
        # imsg.source = app.Properties.name
        # self.device.system.msgl.push(imsg.reply(response, reason))
        #=======================================================================
        return

class PlayInfo(object):
    '''Represents information that is not source specific in Yamaha API.

    Some of the information about sources in MusicCast devices are only available for groups of
    sources, and not source by source.  This is true for the **netusb** type, which covers a wide
    range of sources (*server*, *net_radio*, and all streaming services).  This information can not
    be stored on a source by source basis but in an ad-hoc structure that sources will link to.
    For any device, there can be only one instance of each type (**cd**, **tuner** and **netusb**)
    so the instantiation of these classes is triggered by the Source object initialisation, that
    finds out of what type it is and then calls a sort of factory method within the parent Device
    object that in then decides to instantiate a new object if it does not exist yet or returns the
    existing object (a sort of singleton pattern).
    
    Args:
        play_info_type (string): one of **tuner**, **cd**, or **netusb**.
        device (Device object): parent device of the source.
    '''

    def __init__(self, play_info_type, device):
        self.type = play_info_type
        self.device = device
        self.play_info = None

    def update_play_info(self):
        ''' Retrieves the play_info structure.

        The sources involved in this command are **tuner**, **cd**, and all
        sources part of the **netusb** group.
        '''
        self.play_info = self.device.conn.mcrequest(self.type, 'getPlayInfo')

    def update_preset_info(self):
        ''' Retrieves the preset_info structure.
        
        The `getPresetInfo` request involves only types **tuner** and **netusb**. Treatment in
        either case is different, see the Yamaha doc for details.
        '''
        raise mcx.LogicError(''.join(('Type <', self.type, '> does not have preset info.')))

    def update_play_time(self, value):
        ''' Updates the play_time attribute with the new value.

        Only concerns MusicCast types **cd** and **netusb**.
        The **play_time** event get sent every second by MusicCast devices
        once a cd or a streaming service starts playing.  Maybe it is not
        necessary to process it every second.

        Args:
            value (integer in string form): the new value of play_time.
        '''
        raise mcx.LogicError(''.join(('Type <', self.type, '> does not have play time info.')))

    def update_play_message(self, value):
        ''' Updates the play_message attribute with the new value.

         This event only applies to the **netusb** group.

        Args:
            value (string): the new value of play_message.
        '''
        raise mcx.LogicError(''.join(('Type <', self.type, '> does not have play message info.')))

class Tuner(PlayInfo):
    ''' Tuner specific information.
    
    Args:
        device (Device object): parent device.
    '''

    def __init__(self, device):
        super(Tuner, self).__init__('tuner', device)
        try: self.preset_type = self.device.features['tuner']['preset']['type']
        except KeyError:
            raise mcx.CommsError('getFeatures object does not contain the'\
                                 '<tuner><preset><type> key.')
        if self.preset_type == 'separate':
            try: func_list = self.device.features['tuner']['func_list']
            except KeyError:
                raise mcx.CommsError('getFeatures object does not contain'\
                                     ' the <tuner><preset><func_list> key.')
            self.info_bands = [band for band in func_list if band in ('am', 'fm', 'dab')]
        self.preset_info = []

    def update_preset_info(self):
        ''' Retrieves the preset_info structure.
        
        Info type == **tuner**: the request requires a `band` argument that depends on the
        features of the device.  As the structure returned by the request is a list of objects that
        always include the band that the preset relates to, we can concatenate all the preset lists.
        '''

        if self.preset_type == 'common':
            response = self.device.conn.mcrequest('tuner', 'getPresetInfo?band=common')
            try: self.preset_info  = response['preset_info']
            except KeyError:
                raise mcx.CommsError('getPresetInfo did not return a preset_info field.')
        elif self.preset_type == 'separate':
            preset_info = []
            for band in self.info_bands:
                response = self.device.conn.mcrequest('tuner',
                                                      ''.join(('getPresetInfo?band=',band))) 
                try: preset_info.extend(response['preset_info'])
                except KeyError:
                    raise mcx.CommsError('getPresetInfo did not return a preset_info field.')
            self.preset_info = preset_info # update attribute only after all worked properly

class CD(PlayInfo):
    ''' CD specifc information.

    Args:
        device (Device object): parent device.
    '''

    def __init__(self, device):
        super(CD, self).__init__('cd', device)
        self.play_time = '0'

    def update_play_time(self, value):
        ''' Updates the play_time attribute with the new value.

        Args:
            value (integer in string form): the new value of play_time.
        '''
        self.play_time = value

class NetUSB(PlayInfo):
    '''NetUSB specific information.
    Args:
        device (Device object): parent device.
    '''
    def __init__(self, device):
        super(NetUSB, self).__init__('netusb', device)
        self.preset_info = None
        self.play_time = '0'
        self.play_message = ''

    def update_preset_info(self):
        ''' Retrieves the preset_info structure.

        Info type == **netusb**: the request is sent *as is* and the structure
        returned includes a list of objects where one of fields indicates the
        input that the preset relate to (I am not sure what the input can be
        anything else that **net_radio** though).
        '''
        self.preset_info = self.device.conn.mcrequest(self.type, 'getPresetInfo')

    def update_play_time(self, value):
        ''' Updates the play_time attribute with the new value.

        Note: There is an uncertainty on which source is playing when the type is **netusb**.  The
        event does not give any extra information.  It probably means that there can only be one
        source that can play at any given time in the **netusb** group, even if there are multiple
        zones in the device.

        Args:
            value (integer in string form): the new value of play_time.
        '''
        self.play_time = value

    def update_play_message(self, value):
        ''' Updates the play_message attribute with the new value.

        Args:
            value (string): the new value of play_message.
        '''
        self.play_message = value

