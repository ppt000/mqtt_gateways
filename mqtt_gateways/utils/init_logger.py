'''
Created on 1 May 2017

Function to initialise the 'root' logger with pre-defined handlers.

@author: PierPaolo

Usage:
# Use the name of the application as 'module_name':
logger = logging.getLogger('module_name')
init_logger.initlogger(logger, 'module_name' , filepath, [log_debug])

'''

import logging.handlers
import socket

def initlogger(logger, log_id, log_filepath=None, log_debug=False, email_host=None, email_address=None):
    '''
    The logger passed as parameter should be sent by the 'root' module if
    hierarchical logging is the objective. The logger is then initialised with
    the following handlers:
    
    - the standard 'Stream' handler will always log level ERROR and above;
    this should send those messages to the console output, the syslog and/or
    journald, depending on how the application is being launched;
    
    - a rotating file handler, with fixed parameters (max 50kB, 3 rollover
    files); the level for this handler is DEBUG if the parameter 'log_debug' is
    True, INFO otherwise; the file name for this log is given by the
    log_filepath parameter which is used as is; an error message is logged in
    the standard handler if there was a problem creating the file;
    
    - an email handler with the level set to ERROR;
    
    @param logger: the actual logger object to be initialised; don't call
    getLogger otherwise it will not be a 'root' logger.
    @param log_id: a string to identify the logger. Ideally the name of the
    current module.
    @param log_filepath: the debug/info log file path; the path is used 'as is',
    if it is relative, no guarantee is made of where it actually points to.
    @param log_debug: a flag to indicate if DEBUG logging is required, or only
    INFO.
    @param email_host: host of the email server in the form of a tuple (host, port)
    @param email_address: email address where to send the messages.
    
    @return: nothing
    
    @errors: any IOErrors thrown by file handling methods are caught, but smtp
    methods might produce exceptions that are not caught for now.
    '''
    logger.setLevel(logging.DEBUG if log_debug else logging.INFO)
    '''
    Reminder of various format options:
    %(processName)s is always <MainProcess>
    %(module)s is always the name of the current module where the log is called
    %(filename)s is always the 'module' field with .py afterwards
    %(pathname)s is the full path of the file 'filename'
    %(funcName)s is the name of the function where the log has been called
    %(name) is the name of the current logger
    '''
    # create the console handler. It should always work.
    formatter = logging.Formatter('%(name)-20s %(levelname)-8s: %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO) # set the level to INFO temporarily to log what happens in this module
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    # create the file handler, for all logs.
    if log_filepath is not None:
        formatter = logging.Formatter('%(asctime)s %(module)-20s %(levelname)-8s: %(message)s')
        try: fh = logging.handlers.RotatingFileHandler(log_filepath, maxBytes= 50000, backupCount=3)
        except (OSError, IOError) as e: # there was a problem with the file
            logger.error(''.join(('There was an error <',str(e),'> using file <',log_filepath,'> to handle logs. No file used.')))
        else:
            logger.info(''.join(('Using <',log_filepath,'> to log the ','DEBUG' if log_debug else 'INFO',' level.')))
            fh.setLevel(logging.DEBUG if log_debug else logging.INFO)
            fh.setFormatter(formatter)
            logger.addHandler(fh)
    # create the email handler
    if email_host is not None and email_address is not None:
        try: em = logging.handlers.SMTPHandler(email_host,
                                               email_address,
                                               email_address,
                                                ''.join(('Error message from application ', log_id,'.')))
        except (OSError, IOError, socket.timeout, socket.error) as e: # TODO: populate with actual errors that might happen and deal with them
            logger.error(''.join(('There was an error <',str(e),'> using email to handle logs. No emails used.')))
        else:
            em.setLevel(logging.CRITICAL)
            em.setFormatter(formatter)
            logger.addHandler(em)
    # set the console handler to ERROR
    ch.setLevel(logging.ERROR)