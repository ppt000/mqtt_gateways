'''
'''

import httplib
import json

import mqtt_gateways.musiccast.musiccast_exceptions as mcx
import mqtt_gateways.utils.app_properties as app
_logger = app.Properties.getLogger(__name__)

_TIMEOUT = 2

class musiccastHttp(httplib.HTTPConnection, object): # the 'object' is there for a reason
    ''' docstring '''

    def __init__(self, host):
        self._host = host
        self._timeout = _TIMEOUT
        super(musiccastHttp, self).__init__(self._host, timeout=self._timeout)

    def sendrequest(self, qualifier, mc_command):
        '''
        Currently the requests are always method = 'GET' and version = 'v1'.
        The command includes any argument added.
        '''
        _logger.debug(''.join(('Sending request: ', '/'.join(('/YamahaExtendedControl/v1',qualifier,mc_command)))))
        try: self.request('GET','/'.join(('/YamahaExtendedControl/v1',qualifier,mc_command)))
        except httplib.HTTPException as err:
            raise mcx.mcConnectError(''.join(('Can''t send request, HTTP error:\n\t', repr(err))))

        try: response = self.getresponse()
        except httplib.HTTPException as err:
            raise mcx.mcHTTPError(''.join(('Device not responding with HTTP error:\n\t', repr(err))))

        if response.status != 200:
            raise mcx.mcHTTPError(''.join(('Problem with HTTP request. Status: ',
                                       httplib.responses[response.status], ' - Reason ', response.reason)))

        dict_response = json.loads(response.read()) # TODO: catch any errors?

        if dict_response['response_code'] != 0:
            raise mcx.mcDeviceError(''.join(('Unsuccessful request. Response Code from device: ',
                                       str(dict_response['response_code']))))

        _logger.debug('Request answered successfully.')

        return dict_response
