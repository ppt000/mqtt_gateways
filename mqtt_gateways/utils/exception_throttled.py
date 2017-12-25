'''
Created on 25 Nov 2017

@author: PierPaolo
'''

import time

_THROTTLELAG = 10 # in seconds

class ThrottledException(Exception):
    _count = 0
    _timer = time.time()-(1.1*_THROTTLELAG) # to have the first error logged
    def __init__(self, msg=None, throttlelag=_THROTTLELAG, module_name=None):
        self.msg = msg
        if module_name is None: modulestring = ''
        else: modulestring = ''.join((' in module ', module_name))
        self.trigger = False
        t = time.time()
        dt = t - ThrottledException._timer
        if dt > throttlelag:
            self.trigger = True            
            if (ThrottledException._count == 0) or (dt > (2 * throttlelag)):
                self.report = ''.join(('Fresh error',modulestring,':\n\t -> ', msg))
            else:
                self.report = ''.join(('There have been ',str(ThrottledException._count + 1),
                                     ' errors', modulestring,' in the past ',
                                     "{:.2f}".format(dt),' seconds. Latest error was:\n\t -> ',msg))
            ThrottledException._count = 0
            ThrottledException._timer = t
        else:
            ThrottledException._count += 1
        super(ThrottledException, self).__init__(self.msg)