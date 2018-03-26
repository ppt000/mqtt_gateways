'''
Exceptions definitions for the MusicCast package.

All are inherited from the Exception class, with the member
'message' available.
'''

# TODO: Categorise errors =====================================================
# Connection not working
# Device offline?
# Wrong commands, not recognised
# Data read not as expected
# Arguments from commands missing or wrong type

class mcError(Exception):
    pass

class mcConfigError(mcError):
    pass

class mcConnectError(mcError):
    ''' There is no connection, so network might be down, or
    local interface not working...'''
    pass

class mcDeviceError(mcError):
    ''' The device responds but could not execute whatever was asked.'''
    pass

class mcSyntaxError(mcError):
    pass

class mcHTTPError(mcError):
    ''' Protocol error, there was misunderstanding in the communication.'''
    pass

class mcLogicError(mcError):
    pass

class mcProtocolError(mcError):
    pass
