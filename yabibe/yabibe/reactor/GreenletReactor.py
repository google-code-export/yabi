# Use epoll() as our base reactor
from twisted.internet.epollreactor import EPollReactor as GreenletBaseReactor

# seconds between running the greenthreads. 0.0 for flat out 100% CPU
GREENLET_MAX_PUMP_RATE = 0.01

class GreenletReactor(GreenletBaseReactor):
    """This reactor does the stackless green thread pumping in the main thread, interwoven with the reactor pump"""
    
    def doIteration(self, timeout):
        """Calls the base reactors doIteration, and then fires off all the stackless threads"""
        if timeout > STACKLESS_MAX_PUMP_RATE:
            timeout = STACKLESS_MAX_PUMP_RATE
        try:    
            #stackless.schedule()
            pass
        except Exception, e:
            print "Uncaught Exception in greenlet thread"
            import traceback
            traceback.print_exc()
        return GreenletBaseReactor.doIteration(self,timeout)

def install():
    """
    Install the epoll() reactor.
    """
    p = GreenletReactor()
    from twisted.internet.main import installReactor
    installReactor(p)

class GreenletTaskSwitcher(object):
    def __init__(self):
        self._tasks = []
        
    def tasklet(self, func):
        gr = greenlet(func)
        self._tasks.append(gr)

    def schedule(self):
        pass
    
    def switch_next(self):
        # switch to the next greenlet
        if not self._tasks:
            return
            
        task = self._tasks.pop(0)
        task.switch()
        self._tasks.append(task)
        
        
            
            
        
        
