'''This module contains the data necessary to decode or encode C-Bus messages.'''

# pylint: disable=bad-whitespace

LIGHTS = {
    'Kitchen_Spots':                ['01',           'Kitchen'],
    'Kitchen_UnderUnit':            ['02',           'Kitchen'],
    'TVRoom_Spots':                 ['03',            'TVRoom'],
    'DiningRoom_Pendant':           ['04',        'DiningRoom'],
    'DiningRoom_Socket':            ['05',        'DiningRoom'],
    'LivingRoom_Spots':             ['06',        'LivingRoom'],
    'LivingRoom_Wall':              ['07',        'LivingRoom'],
    'Office_Socket':                ['08',            'Office'],
    'Office_Spots':                 ['09',            'Office'],
    'Bedroom_Bedside':              ['0A',           'Bedroom'],
    'Bedroom_Socket':               ['0B',           'Bedroom'],
    'Bedroom_Spots':                ['0C',           'Bedroom'],
    'Bathroom_Spots':               ['0D',          'Bathroom']
    }
'''
Dictionary of lights names with their C-Bus codes and their location.

The dictionary is in the form ``'internal name of device/light':['C-Bus address',
'location name']``.
This dictionary allows to build at once the devices dictionary as well as the
location one.  Obviously the lights names must be unique, as well as the corresponding
C-Bus codes. This setup ensures every item (light name, location name, light
C-Bus code) appears only once and there are no risks of duplicates.
'''


ACTIONS = [
    ['LIGHT_ON',      ['79']],
    ['LIGHT_OFF',     ['01']],
    ['LIGHT_LVL',     ['02', '%%']],
    ['RAMP_0S_LVL',   ['02', '%%']], # same as 'LIGHT_LVL'
    ['RAMP_4S_LVL',   ['0A', '%%']],
    ['RAMP_8S_LVL',   ['12', '%%']],
    ['RAMP_12S_LVL',  ['1A', '%%']],
    ['RAMP_20S_LVL',  ['22', '%%']],
    ['RAMP_30S_LVL',  ['2A', '%%']],
    ['RAMP_40S_LVL',  ['32', '%%']],
    ['RAMP_60S_LVL',  ['3A', '%%']],
    ['RAMP_90S_LVL',  ['42', '%%']],
    ['RAMP_2M_LVL',   ['4A', '%%']],
    ['RAMP_3M_LVL',   ['52', '%%']],
    ['RAMP_5M_LVL',   ['5A', '%%']],
    ['RAMP_7M_LVL',   ['62', '%%']],
    ['RAMP_10M_LVL',  ['6A', '%%']],
    ['RAMP_15M_LVL',  ['72', '%%']],
    ['RAMP_17M_LVL',  ['7A', '%%']],
    ['TERMINATERAMP', ['09']],
    # Add custom made actions from here
    ['LIGHT_LOW',     ['02','55']],
    ['LIGHT_MEDIUM',  ['02','AA']]
]
'''
List of local actions and their C-Bus hex code equivalent.

Only *short commands* are used here (as defined in C-Bus documentation)
as *long commands* seem to be only needed for labels.
The 3 last bits of short commands indicate the number of arguments required. In
practice, only the ``ON`` and ``OFF`` commands (and ``TERMINATERAMP``, rarely used) require
one argument only (the Address) while all the others (the ``RAMP to LEVEL`` ones)
require two arguments (the Address and the Level to reach). No other commands
are allowed.

The list is made of pairs where the first element is the internal name of the action
and the second element is another list made of the C-Bus codes representing this action.
This list of C-Bus codes has one or two elements.  The first one represents the actual
action code in C-Bus (``ON``, ``OFF``, ``RAMP``, ...) and the second one represents the ``LEVEL``
to reach in the ``RAMP`` case.  In the case of *standard* actions, the argument is left
*variable* and has to be communicated as an argument of the action; in this case
the convention is to represent it with a ``%%``.

The code allows to create different ways to execute the same action, e.g. switching a
light to a *medium* level can be achieved with the action ``LIGHT_LVL`` and a parameter ``AA``
or with the custom made action ``LIGHT_MEDIUM``.  Add your own actions at the end of the list.

This data is represented in a list because the order here matters
to build the reverse dictionary.  The reverse dictionary will only contain the *standard*
actions, which means that in the translation from C-Bus to MQTT, the custom-made actions
are not taken into account.
'''

FUNCTIONS = {
    'Lighting': '38'
    }
'''
Dictionary of Functions or Applications as defined in C-Bus.

The dictionary is in the form ``'internal name':'C-Bus code'``.
This dictionary should not be modified but can be appended with
additional Applications from C-Bus.
'''

LEVELS = {
    '55':'F',
    '56':'E',
    '59':'D',
    '5A':'C',
    '65':'B',
    '66':'A',
    '69':'9',
    '6A':'8',
    '95':'7',
    '96':'6',
    '99':'5',
    '9A':'4',
    'A5':'3',
    'A6':'2',
    'A9':'1',
    'AA':'0'
}
'''
Dictionary for the correspondence of levels definition in C-Bus status replies.

From C-Bus documentation. Do not change.
'''
