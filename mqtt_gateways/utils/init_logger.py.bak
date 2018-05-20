'''
Function to initialise the 'root' logger with pre-defined handlers.

Usage (from the main script):

TODO: change the following import example

.. code-block:: none

    from init_logger import initlogger
    
    # Use the name of the application as 'module_name':
    logger = logging.getLogger('module_name')
    initlogger(logger, 'module_name' , filepath, [log_debug])

'''

import logging.handlers
import socket

def initlogger(logger, log_id, log_filepath=None, log_debug=False,
               email_host=None, email_address=None):
    '''
    The logger passed as parameter should be sent by the 'root' module if
    hierarchical logging is the objective. The logger is then initialised with
    the following handlers:

    - the standard 'Stream' handler will always log level ERROR and above;
    - a rotating file handler, with fixed parameters (max 50kB, 3 rollover
      files); the level for this handler is DEBUG if the parameter 'log_debug' is
      True, INFO otherwise; the file name for this log is given by the
      log_filepath parameter which is used as is; an error message is logged in
      the standard handler if there was a problem creating the file;
    - an email handler with the level set to ERROR;

    Args:
        logger: the actual logger object to be initialised;
        log_id (string): identifies the logger, ideally the name of the
            calling module;
        log_filepath (string): the log file path, used 'as is';
            if it is relative, no guarantee is made of where it actually points to;
        log_debug (boolean): a flag to indicate if DEBUG logging is required, or only
            INFO;
        email_host (string): host of the email server in the form of a tuple (host, port);
        email_address (string): email address where to send the messages.

    Returns:
        Nothing

    Raises:
        any IOErrors thrown by file handling methods are caught, but smtp
            methods might produce exceptions that are not caught for now.
    '''
    logger.setLevel(logging.DEBUG if log_debug else logging.INFO)
    #===========================================================================
    # Reminder of various format options:
    # %(processName)s is always <MainProcess>
    # %(module)s is always the name of the current module where the log is called
    # %(filename)s is always the 'module' field with .py afterwards
    # %(pathname)s is the full path of the file 'filename'
    # %(funcName)s is the name of the function where the log has been called
    # %(name) is the name of the current logger
    #===========================================================================
    # create the console handler. It should always work.
    formatter = logging.Formatter('%(name)-20s %(levelname)-8s: %(message)s')
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO) # set the level to INFO temporarily to log what happens in this module
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    # create the file handler, for all logs.
    if log_filepath is not None:
        formatter = logging.Formatter('%(asctime)s %(module)-20s %(levelname)-8s: %(message)s')
        try: file_handler = logging.handlers.RotatingFileHandler(log_filepath, maxBytes=50000, backupCount=3)
        except (OSError, IOError) as err: # there was a problem with the file
            logger.error(''.join(('There was an error <', str(err), '> using file <', log_filepath,
                                  '> to handle logs. No file used.')))
        else:
            logger.info(''.join(('Using <', log_filepath, '> to log the ',
                                 'DEBUG' if log_debug else 'INFO', ' level.')))
            file_handler.setLevel(logging.DEBUG if log_debug else logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
    # create the email handler
    if email_host is not None and email_address is not None:
        try: email_handler = logging.handlers.SMTPHandler(email_host,
                                                          email_address,
                                                          email_address,
                                                          ''.join(('Error message from application ',
                                                                   log_id, '.')))
        except (OSError, IOError, socket.timeout, socket.error) as err:
            # TODO: populate with actual errors that might happen and deal with them
            logger.error(''.join(('There was an error <', str(err),
                                  '> using email to handle logs. No emails used.')))
        else:
            email_handler.setLevel(logging.CRITICAL)
            email_handler.setFormatter(formatter)
            logger.addHandler(email_handler)
    # set the console handler to ERROR
    stream_handler.setLevel(logging.ERROR)
