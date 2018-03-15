'''
'''

import httplib
import json

from mqtt_gateways.musiccast.musiccast_exceptions import mcConnectError, mcDeviceError, mcHTTPError
from mqtt_gateways.utils.app_helper import appHelper

_TIMEOUT = 2

class musiccastHttp(httplib.HTTPConnection, object):
    ''' docstring '''

    def __init__(self, host):
        self._logger = appHelper.getLogger(__name__)
        self._host = host
        self._timeout = _TIMEOUT
        super(musiccastHttp, self).__init__(self._host, timeout=self._timeout)

    def sendrequest(self, qualifier, mc_command):
        '''
        Currently the requests are always method = 'GET' and version = 'v1'.
        The command includes any argument added.
        '''
        self._logger.debug(''.join(('Sending request: ', '/'.join(('/YamahaExtendedControl/v1',qualifier,mc_command)))))
        try: self.request('GET','/'.join(('/YamahaExtendedControl/v1',qualifier,mc_command)))
        except httplib.HTTPException as err:
            raise mcConnectError(''.join(('Can''t send request, HTTP error:\n\t', repr(err))))

        try: response = self.getresponse()
        except httplib.HTTPException as err:
            raise mcHTTPError(''.join(('Device not responding with HTTP error:\n\t', repr(err))))

        if response.status != 200:
            raise mcHTTPError(''.join(('Problem with HTTP request. Status: ',
                                       httplib.responses[response.status], ' - Reason ', response.reason)))

        dict_response = json.loads(response.read()) # TODO: catch any errors?

        if dict_response['response_code'] != 0:
            raise mcDeviceError(''.join(('Unsuccessful request. Response Code from device: ',
                                       str(dict_response['response_code']))))

        self._logger.debug('Request answered successfully.')

        return dict_response
