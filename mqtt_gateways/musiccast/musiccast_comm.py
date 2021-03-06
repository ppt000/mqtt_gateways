'''
Low-level communication module with the MusicCast system.

Reviewed on 16 May 2018 by Paolo.
'''

import sys
import socket
import select
import httplib
import json
import time


import mqtt_gateways.musiccast.musiccast_exceptions as mcx
import mqtt_gateways.utils.app_properties as app
_logger = app.Properties.get_logger(__name__)

_HTTP_TIMEOUT = 10 # The time-out for the HTTP requests.
_SOCKET_TIMEOUT = 0.01 # The time-out when checking the socket for incoming events, in seconds.

MCSOCKET = None
MCPORT = None
_THIS = sys.modules[__name__]

def set_socket(listen_port):
    ''' Instantiates a socket and binds it to the port provided.

    Also initialises the 2 module 'constants' MCSOCKET and MCPORT.

    Args:
        listen_port (int): the local port to bind to the socket.

    Raises:
        CommsError: in case of failure to bind the socket to the port.
    '''
    _THIS.MCPORT = listen_port
    if _THIS.MCSOCKET is None:
        try:
            _THIS.MCSOCKET = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            _THIS.MCSOCKET.bind(('', listen_port))
            _THIS.MCSOCKET.setblocking(0)
        except socket.error as err:
            raise mcx.CommsError(''.join(('Can\'t open listener socket. Error:\n\t', repr(err))))
        _logger.debug('Socket successfully opened.')

def get_event():
    ''' Checks the socket for events broadcasted by the MusicCast devices.

    TODO: check max length of the events and more than one event could arrive at once

    The 'body' of the event (see below) is in the form:
    ('{"main":{"power":"on"},"device_id":"00A0DED57E83"}', ('192.168.1.44', 38507))
    or:
    ('{"main":{"volume":88},"zone2":{"volume":0}, "device_id":"00A0DED3FD57"}', ('192.168.1.42', 46514))
    '''
    event = select.select([_THIS.MCSOCKET], [], [], _SOCKET_TIMEOUT)
    if event[0]: # there is an event
        body = event[0][0].recvfrom(1024)
        _logger.debug(''.join(('Event received: ', str(body))))
        try: dict_response = json.loads(body[0])
        except ValueError as err:
            raise mcx.CommsError(''.join(('The received event is not in JSON format. Error:\n\t',
                                          repr(err))))
        return dict_response
    return None

class musiccastComm(object):
    ''' Manages the low-level calls to the MusicCast devices.

    Every instance represents a single live connection to a given MusicCast
    device, represented simply by a host address.

    Args:
        host (string): the HTTP address for the host, as recognisable
            by the httplib library.
    '''

    def __init__(self, host):
        self._host = host
        self._timeout = _HTTP_TIMEOUT
        self._headers = {'X-AppName': 'MusicCast/0.2(musiccast2mqtt)',
                         'X-AppPort': str(_THIS.MCPORT)}
        self.request_time = 0
        _logger.debug(''.join(('Header: ', str(self._headers))))

    def mcrequest(self, qualifier, mc_command):
        ''' Sends a single HTTP request and returns the response.

        This method sends the request and read the response step by step in
        order to catch properly any error in the process. Currently the requests
        are always with method = 'GET' and version = 'v1'.

        Args:
            qualifier (string): the token in the MusicCast syntax representing
                either a zone or a source, depending on the type of command
                sent;
            mc_command (string): the command to send at the end of the request;
                it has to include any extra argument if there are any.

        Raises:
            commsError: in case of any form of Communication Error with the device.

        Returns:
            dictionary: the dictionary equivalent of the JSON structure sent back as a reply
                from the device.
        '''

        conn = httplib.HTTPConnection(self._host, timeout=self._timeout)

        _logger.debug(''.join(('Sending to address <', self._host, '> the request: ',
                               '/'.join(('/YamahaExtendedControl/v1', qualifier, mc_command)))))

        try: conn.request(method='GET',
                          url='/'.join(('/YamahaExtendedControl/v1',
                                        qualifier, mc_command)),
                          headers=self._headers)
        except httplib.HTTPException as err:
            conn.close()
            raise mcx.CommsError(''.join(('Can\'t send request. Error:\n\t',
                                          repr(err))))

        # insert a delay here?

        try: response = conn.getresponse()
        except httplib.HTTPException as err:
            conn.close()
            raise mcx.CommsError(''.join(('Can\'t get response. Error:\n\t',
                                          repr(err))))

        if response.status != 200:
            conn.close()
            raise mcx.CommsError(''.join(('HTTP response status not OK.\n'\
                                          '\tStatus: ', httplib.responses[response.status],
                                          '\n\tReason: ', response.reason)))

        try: dict_response = json.loads(response.read())
        except ValueError as err:
            conn.close()
            raise mcx.CommsError(''.join(('The response from the device is not'\
                ' in JSON format. Error:\n\t', repr(err))))

        if dict_response['response_code'] != 0:
            conn.close()
            raise mcx.CommsError(''.join(('The response code from the'\
                                          ' MusicCast device is not OK. Actual code:\n\t',
                                          str(dict_response['response_code']))))

        _logger.debug('Request answered successfully.')

        conn.close()
        self.request_time = time.time()
        return dict_response
