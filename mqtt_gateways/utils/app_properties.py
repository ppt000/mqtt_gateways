'''
docstring
'''

from collections import namedtuple
import logging
import os.path
import sys


this_module = sys.modules[__name__]

AppProperties = namedtuple('AppProperties', ('name', 'path', 'root_logger', 'getPath', 'getLogger'))

def _getLogger(fullmodulename):
    if fullmodulename == '__main__' or fullmodulename == this_module.Properties.name:
        logname = this_module.Properties.name
    else:
        modulename = fullmodulename.split('.')[-1]
        if not modulename: logname = this_module.Properties.name
        else: logname = '.'.join((this_module.Properties.name, modulename))
    return logging.getLogger(logname)

def _getPath(extension, path_given=None):
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
#        return generatefilepath(properties.name, extension, properties.path, path_given)
    dfltname = ''.join((this_module.Properties.name, extension))
    if path_given == '':
        filepath = os.path.join(this_module.Properties.path, dfltname)
    else:
        dirname, filename = os.path.split(path_given.strip())
        if dirname != '': dirname = os.path.normpath(dirname)
        if filename == '': filename = dfltname
        if dirname == '': dirname = this_module.Properties.path
        elif not os.path.isabs(dirname): dirname = os.path.join(this_module.Properties.path, dirname)
        filepath = os.path.join(dirname, filename)
    return os.path.normpath(filepath)

def _initHelper(full_path):
    name = os.path.splitext(os.path.basename(full_path))[0] # first part of the filename, without extension
    path = os.path.realpath(os.path.dirname(full_path)) # full path of the launching script
    root_logger = logging.getLogger(name)
    this_module.Properties = AppProperties(name, path, root_logger, _getPath, _getLogger)

Properties = _initHelper