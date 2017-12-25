'''
Created on 15 Nov 2017

@author: Paolo
'''

import os.path

def generatefilepath(name, path, ext, pathgiven = ''):
    '''
    Helper function to generate the right absolute path from a range of possible
    scenarios. It takes 4 arguments, 3 of them to generate defaults and the last
    one to suggest alternatives from the user. If no alternative from the user
    is provided, the function simply returns the default absolute path with the
    correct extension. If an alternative is provided it could be one of 4 cases,
    depending if the directory path is absolute or relative, and if a filename
    at the end is provided or not. If the path is relative, the application path
    is prepended. If the filename is missing, the default name is provided. The
    full absolute path is then generated and returned.
    
    @param name: application name without extension used as filename root.
    @param path: the absolute path of the current application.
    @param ext: the extension of the file, in the form '.xxx'
    @param pathgiven: the path string given as alternative to the default.
    '''
    dfltname = ''.join((name, ext))
    if pathgiven == '':
        filepath = os.path.join(path, dfltname)
    else:
        dirname, filename = os.path.split(pathgiven.strip())
        if dirname !='': dirname = os.path.normpath(dirname)
        if filename == '': filename = dfltname
        if dirname == '': dirname = path
        elif not os.path.isabs(dirname): dirname = os.path.join(path, dirname)
        filepath = os.path.join(dirname, filename)
    return filepath

if (__name__ == '__main__'):
    print 'Test1 -----------------------'
    print generatefilepath('zork', 'C:\\Users\\Paolo\\Test', '.conf', 'data/')
    print 'Test2 -----------------------'
    print generatefilepath('zork', 'C:\\Users\\Paolo\\Test', '.conf', 'dummy2mqtt.conf')
    print 'Test3 -----------------------'
    print generatefilepath('zork', 'C:\\Users\\Paolo\\Test', '.conf', '')
    print 'Test4 -----------------------'
    print generatefilepath('zork', 'C:\\Users\\Paolo\\Test', '.conf', '/etc/dummy2mqtt.conf')