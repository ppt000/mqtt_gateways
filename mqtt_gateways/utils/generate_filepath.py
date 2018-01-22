'''
Full file path generator.
'''

import os.path

def generatefilepath(basename, ext, absdirpath, pathgiven):
    '''
    Generates the absolute path of a file.

    This function takes a path as argument and builds an absolute path
    to a file based on default arguments, with some basic rules.
    There are 3 'default' arguments: the basename of the file,
    the extension of the file, and an absolute path.

    from a range of possible
    scenarios. It takes 4 arguments, 3 of them to generate defaults and the last
    one to suggest alternatives from the user. If no alternative from the user
    is provided, the function simply returns the default absolute path with the
    correct extension. If an alternative is provided it could be one of 4 cases,
    depending if the directory path is absolute or relative, and if a filename
    at the end is provided or not. If the path is relative, the application path
    is prepended. If the filename is missing, the default basename is provided. The
    full absolute path is then generated and returned.

    Args:
        basename (string): basename without extension, usually the application name
        absdirpath (string): the absolute path of the current application
        ext (string): the extension of the file, in the form '.xxx'. i.e. with the dot
        pathgiven (string): the path given as alternative to the default, optional
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
