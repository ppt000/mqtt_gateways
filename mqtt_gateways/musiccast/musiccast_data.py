'''Data for the MusicCast system.'''

TRANSFORM_ARG = {
    'power':        lambda self, value: 'on' if value == 'on' else 'standby',
    # needed only if we create a SET_POWER command
    'mute':         lambda self, value: 'true' if value == 'on' else 'false',
    # needed only if we create a SET_MUTE command
    'volume':       lambda self, value: int(int(value) * self.volume_range / 100),
    'input':        lambda self, value: value, # Assume same names between internal and MusicCast, for now
    'source':       lambda self, value: value, # Assume same names between internal and MusicCast, for now
    'preset':       lambda self, value: str(value) # preset number, could be an int
    }
''' Transforms arguments from internal keyword to MusicCast keyword.
The lambdas have to be called by a Zone object.
'''

ACTIONS = {
    'POWER_OFF':        lambda self: self.set_power(False),
    'POWER_ON':         lambda self: self.set_power(True),
    'SET_VOLUME':       lambda self: self.set_volume(),
    'VOLUME_UP':        lambda self: self.set_volume(True),
    'VOLUME_DOWN':      lambda self: self.set_volume(False),
    # TODO: implement VOLUME_UP and DOWN with step...
    'MUTE_ON':          lambda self: self.set_mute(True),
    'MUTE_OFF':         lambda self: self.set_mute(False),
    'MUTE_TOGGLE':      lambda self: self.set_mute(not self.state['mute']),
    'GET_INPUTS':       lambda self: self.send_reply(), # TODO: send message reply with list of available inputs
    'SET_INPUT':        lambda self: self.set_input(),
    'GET_SOURCES':      lambda self: self.send_reply(), # TODO: send message reply with list of available sources
    'SET_SOURCE':       lambda self: self.set_source(),
    'SOURCE_CD':        lambda self: self.set_source('cd'),
    'SOURCE_NETRADIO':  lambda self: self.set_source('net_radio'),
    'SOURCE_TUNER':     lambda self: self.set_source('tuner'),
    'SOURCE_SPOTIFY':   lambda self: self.set_source('spotify'),
    'CD_BACK':          lambda self: self.set_playback('previous', 'cd'),
    'CD_FORWARD':       lambda self: self.set_playback('next', 'cd'),
    'CD_PAUSE':         lambda self: self.set_playback('pause', 'cd'),
    'CD_PLAY':          lambda self: self.set_playback('play', 'cd'),
    'CD_STOP':          lambda self: self.set_playback('stop', 'cd'),
    'SPOTIFY_PLAYPAUSE':lambda self: self.set_playback('play_pause', 'netusb'),
    'SPOTIFY_BACK':     lambda self: self.set_playback('previous', 'netusb'),
    'SPOTIFY_FORWARD':  lambda self: self.set_playback('next', 'netusb'),
    'TUNER_PRESET':     lambda self: self.set_preset('tuner'),
    'NETRADIO_PRESET':  lambda self: self.set_preset('net_radio')
    }
'''
The dictionary with all the data to process the various commands.

It has to be called from an instance of the class Zone.
'''

_RESPONSE_CODES = {
    0: "Successful request",
    1: "Initializing",
    2: "Internal Error",
    3: "Invalid Request (A method did not exist, a method wasn't appropriate etc.)",
    4: "Invalid Parameter (Out of range, invalid characters etc.)",
    5: "Guarded (Unable to setup in current status etc.)",
    6: "Time Out",
    99: "Firmware Updating",
    100: "Access Error",
    101: "Other Errors",
    102: "Wrong User Name",
    103: "Wrong Password",
    104: "Account Expired",
    105: "Account Disconnected/Gone Off/Shut Down",
    106: "Account Number Reached to the Limit",
    107: "Server Maintenance",
    108: "Invalid Account",
    109: "License Error",
    110: "Read Only Mode",
    111: "Max Stations",
    112: "Access Denied"
    }

_ZONES = ('main', 'zone2', 'zone3', 'zone4')

_INPUTS = ('cd', 'tuner', 'multi_ch', 'phono', 'hdmi1', 'hdmi2', 'hdmi3', 'hdmi4', 'hdmi5', 'hdmi6',
           'hdmi7', 'hdmi8', 'hdmi', 'av1', 'av2', 'av3', 'av4', 'av5', 'av6', 'av7', 'v_aux',
           'aux1', 'aux2', 'aux', 'audio1', 'audio2', 'audio3', 'audio4', 'audio_cd', 'audio',
           'optical1', 'optical2', 'optical', 'coaxial1', 'coaxial2', 'coaxial',
           'digital1', 'digital2', 'digital', 'line1', 'line2', 'line3', 'line_cd',
           'analog', 'tv', 'bd_dvd', 'usb_dac', 'usb', 'bluetooth', 'server', 'net_radio',
           'rhapsody', 'napster', 'pandora', 'siriusxm', 'spotify', 'juke', 'airplay',
           'radiko', 'qobuz', 'mc_link', 'main_sync', 'none')

_SOUNDPROGRAMS = ('munich_a', 'munich_b', 'munich', 'frankfurt', 'stuttgart', 'vienna',
                  'amsterdam', 'usa_a', 'usa_b', 'tokyo', 'freiburg', 'royaumont', 'chamber',
                  'concert', 'village_gate', 'village_vanguard', 'warehouse_loft',
                  'cellar_club', 'jazz_club', 'roxy_theatre', 'bottom_line', 'arena',
                  'sports', 'action_game', 'roleplaying_game', 'game', 'music_video',
                  'music', 'recital_opera', 'pavilion', 'disco', 'standard', 'spectacle',
                  'sci-fi', 'adventure', 'drama', 'talk_show', 'tv_program', 'mono_movie',
                  'movie', 'enhanced', '2ch_stereo', '5ch_stereo', '7ch_stereo', '9ch_stereo',
                  '11ch_stereo', 'stereo', 'surr_decoder', 'my_surround', 'target', 'straight', 'off')

def print1():
    ''' docstring '''
    print 'ZONES:'
    for zon in _ZONES:
        print '\t', zon
    print
    print 'INPUTS:'
    for inp in _INPUTS:
        print '\t', inp
    print
    print 'SOUND PROGRAMS:'
    for snd in _SOUNDPROGRAMS:
        print '\t', snd

if __name__ == '__main__':
    print1()
