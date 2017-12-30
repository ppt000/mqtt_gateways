'''
The *dummy* interface class definition. Use it as a template.

This module defines the class ``dummyInterface`` that will be instantiated by the
main gateway module.
Any other code needed for the interface can be placed here or in other
modules, as long as the necessary imports are included of course.
'''

# only import those modules if using the logger provided
import logging
import os.path

# only import this module for the example code in loop()
import time

from mqtt_gateways.gateway.mqtt_map import internalMsg

class dummyInterface():
    '''
    The dummyInterface class doesn't do anything but provides a template.
    
    The minimum requirement for the interface class is to define 2 public
    methods:
    
    - the constructor ``__init__`` which takes 4 arguments,
    - the ``loop`` method.
    
    Parameters
    ----------
    params : dictionary of strings
        This dictionary is initialised by the ``[INTERFACE]`` section in
        the configuration file.  All the options in that section generate an
        entry in the dictionary, with the key being the first part of the
        option, and the value being the second part of the option (after the
        semi-colon ``:``). Use this to pass parameters from the configuration
        file to the interface, for example the name of a port, or the speed
        of a serial communication.
    msgin, msgout : lists of ``internalMsg`` objects
        These lists represent the communication *bus* with the core of the
        application. The list ``msgin`` contains the incoming messages to
        process by this interface, and the list ``msgout`` can be used to
        send messages from this interface to the core application (and
        subsequently to the MQTT network).  The elements of these lists
        should be instantiations of the ``internalMsg`` class.  Use the
        method ``pop(0)`` to read the ``msgin`` list on a FIFO basis and
        the method ``append(msg)`` to fill the ``msgout`` list.
        The constructor should assign these lists to a local attribute
        that the other methods of this class can use when needed.
    path : the full absolute path of the launcher script
        This path can be used to extract the name of the application
        or the directory where it is located.  It can be useful to
        the ``logging`` library to allow proper hierarchical logging
        or to other functions that need to find data files relative to
        the launcher script location.
    
    '''
    
    def __init__(self, params, msgin, msgout, path):
        # use this logger to benefit from the handlers of the core application 
        rootname = os.path.splitext(os.path.basename(path))[0] # first part of the filename, without extension
        self._logger = logging.getLogger(''.join((rootname,".",__name__)))
        # optional welcome message
        self._logger.debug(''.join(('Module <',__name__,'> started.')))
        # example of how to use the 'params' dictionary
        try: port = params['port'] # the 'port' option should be defined in the configuration file
        except KeyError: # if it is not, we are toast, or a default could be provided 
            errormsg = 'The "port" option is not defined in the configuration file.'
            self._logger.critical(''.join(('Module ',__name__,' could not start.\n', errormsg)))
            raise KeyError(errormsg)
        # optional success message
        self._logger.debug(''.join(('Parameter "port" succesfully updated with value <',port,'>')))
        # *** INITIATE YOUR INTERFACE HERE ***
                
        # Keep the message lists locally
        self._msgin = msgin
        self._msgout = msgout
        
        # initialise time for the example only
        self.t0= time.time()
        
    def loop(self):
        ''' The method called periodically by the main loop.
        
        Place here your code to interact with your system.
        '''
        # example code to read the incoming messages list
        while (True):
            try: msg = self._msgin.pop(0) # read messages on a FIFO basis
            except IndexError: break
            # do something with the message; here we log only
            self._logger.debug('Message <',msg.str(),'> received.')
        # example code to write in the outgoing messages list every 10 seconds
        t = time.time()
        if (t - self.t0) > 10:
            msg = internalMsg(iscmd=True,
                              function= 'lighting',
                              gateway= 'dummy',
                              location= 'myroom',
                              action= 'LIGHT_ON')
            self._msgout.append(msg)
            self.t0 = t