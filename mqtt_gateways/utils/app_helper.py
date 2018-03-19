'''

'''

import logging.handlers
import os.path
#from generate_filepath import generatefilepath

class appHelper(object):
    ''' Singleton that exposes application specific variables.
    
    '''

    app_name = ''
    app_path = ''
    logfilepath = ''
    root_logger = None

    def __init__(self, full_path):
        appHelper.initHelper(full_path)

    @staticmethod
    def initHelper(full_path):
        if full_path is not None:
            #fullpath = sys.argv[0] # not ideal but should work most of the time
            appHelper.app_name = os.path.splitext(os.path.basename(full_path))[0] # first part of the filename, without extension
            appHelper.app_path = os.path.realpath(os.path.dirname(full_path)) # full path of the launching script

    @staticmethod
    def initLogger(log_filepath=None, log_debug=False,
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
        appHelper.logfilepath = log_filepath
        appHelper.root_logger = logging.getLogger(appHelper.app_name)
        appHelper.root_logger.setLevel(logging.DEBUG if log_debug else logging.INFO)
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
        appHelper.root_logger.addHandler(stream_handler)
        # create the file handler, for all logs.
        if appHelper.logfilepath is not None:
            formatter = logging.Formatter('%(asctime)s %(module)-20s %(levelname)-8s: %(message)s')
            try: file_handler = logging.handlers.RotatingFileHandler(appHelper.logfilepath, maxBytes=50000, backupCount=3)
            except (OSError, IOError) as err: # there was a problem with the file
                appHelper.root_logger.error(''.join(('There was an error <', str(err), '> using file <', appHelper.logfilepath,
                                      '> to handle logs. No file used.')))
            else:
                appHelper.root_logger.info(''.join(('Using <', appHelper.logfilepath, '> to log the ',
                                     'DEBUG' if log_debug else 'INFO', ' level.')))
                file_handler.setLevel(logging.DEBUG if log_debug else logging.INFO)
                file_handler.setFormatter(formatter)
                appHelper.root_logger.addHandler(file_handler)
        # create the email handler. TODO: if anything is wrong here the handler will trigger
        #   an error when an email has to be sent. Check how to avoid this.
        if email_host is not None and email_address is not None:
            email_handler = \
            logging.handlers.SMTPHandler(email_host, email_address, email_address,
                                         ''.join(('Error from ', appHelper.app_name, '.')))
            email_handler.setLevel(logging.CRITICAL)
            email_handler.setFormatter(formatter)
            appHelper.root_logger.addHandler(email_handler)
        # set the console handler to ERROR
        stream_handler.setLevel(logging.ERROR)

    @staticmethod
    def getLogger(fullmodulename):
        if fullmodulename == '__main__' or fullmodulename == appHelper.app_name:
            logname = appHelper.app_name
        else:
            modulename = fullmodulename.split('.')[-1]
            if not modulename: logname = appHelper.app_name
            else: logname = '.'.join((appHelper.app_name, modulename))
        return logging.getLogger(logname)

    @staticmethod
    def getPath(extension, path_given=None):
        '''
        Generates the full absolute path of a file.
    
        This function builds an absolute path to a file based on 3 'default' arguments
        (the basename of the file, the extension of the file, and an absolute path) and
        an extra argument that represents a valid path.
        Depending on what represents this path (a directory, a file, an absolute or a 
        relative reference) the function will generate a full absolute path, relying on the
        'default' parameters if and when necessary.
        The generation of the full path follows those rules:
    
            - the default name is made of the default basename and the default extension;
            - if the path given is empty, then the full path is the default absolute path
              with the default filename;
            - if the path given contains a filename at the end, this is the filename to be used;
            - if the path given contains an absolute path at the beginning, that is the
              absolute path that will be used;
            - if the path given contains only a relative path at the beginning, then
              the default absolute path will be prepended to the path given. 
    
        Args:
            basename (string): basename without extension, usually the application name
            absdirpath (string): the absolute path of the current application
            ext (string): the extension of the file, in the form '.xxx'. i.e. with the dot
            pathgiven (string): the path given as alternative to the default
        Returns:
            string: a full absolute path
        '''
#        return generatefilepath(appHelper.app_name, extension, appHelper.app_path, path_given)
        dfltname = ''.join((appHelper.app_name, extension))
        if path_given == '':
            filepath = os.path.join(appHelper.app_path, dfltname)
        else:
            dirname, filename = os.path.split(path_given.strip())
            if dirname != '': dirname = os.path.normpath(dirname)
            if filename == '': filename = dfltname
            if dirname == '': dirname = appHelper.app_path
            elif not os.path.isabs(dirname): dirname = os.path.join(appHelper.app_path, dirname)
            filepath = os.path.join(dirname, filename)
        return os.path.normpath(filepath)