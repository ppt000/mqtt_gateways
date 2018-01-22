'''
Full file path generator.
'''

import os.path

def generatefilepath(basename, ext, absdirpath, pathgiven):
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
    dfltname = ''.join((basename, ext))
    if pathgiven == '':
        filepath = os.path.join(absdirpath, dfltname)
    else:
        dirname, filename = os.path.split(pathgiven.strip())
        if dirname != '': dirname = os.path.normpath(dirname)
        if filename == '': filename = dfltname
        if dirname == '': dirname = absdirpath
        elif not os.path.isabs(dirname): dirname = os.path.join(absdirpath, dirname)
        filepath = os.path.join(dirname, filename)
    return filepath

if __name__ == '__main__':
    print 'Test1 -----------------------'
    print generatefilepath('zork', 'C:\\Users\\Paolo\\Test', '.conf', 'data/')
    print 'Test2 -----------------------'
    print generatefilepath('zork', 'C:\\Users\\Paolo\\Test', '.conf', 'dummy2mqtt.conf')
    print 'Test3 -----------------------'
    print generatefilepath('zork', 'C:\\Users\\Paolo\\Test', '.conf', '')
    print 'Test4 -----------------------'
    print generatefilepath('zork', 'C:\\Users\\Paolo\\Test', '.conf', '/etc/dummy2mqtt.conf')
