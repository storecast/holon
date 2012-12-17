# -*- coding: utf-8 -*-
# see also README in same directory

__copyright__ = u"2012 txtr GmbH"
__author__    = u"Sascha Dieckmann"
__email__     = u"sascha.dieckmann@txtr.com"


import threading, logging
from django.conf import settings as _settings

from reaktor import \
    ReaktorError, ReaktorHttpError, ReaktorIOError, \
    ReaktorApiError, ReaktorAuthError


# keep call history to be logged eventually
keepHistory = _settings.KEEP_JSONRPC_HISTORY

# cache calls and responses, call reaktor.clear() to clear history
cacheCalls = False

# give every thread its own reaktor object
reaktorPerThread = False


if cacheCalls:
    from caching import CachingReaktor as _Reaktor
else:
    from reaktor import Reaktor as _Reaktor


logger = logging.getLogger(__name__)


reaktor.REAKTOR_HOST = _settings.REAKTOR_HOST
reaktor.REAKTOR_PORT = int(_settings.REAKTOR_PORT)
reaktor.REAKTOR_SSL  = reaktor.REAKTOR_PORT == 443
reaktor.REAKTOR_PATH = u"/json/rpc?v=2"


logger.info("holon: reaktor address is %s:%i%s"    %
        (reaktor.REAKTOR_HOST, reaktor.REAKTOR_PORT, reaktor.REAKTOR_PATH))
logger.info("holon: keep reaktor history: %s"      % keepHistory)
logger.info("holon: keep reaktor cache: %s"        % cacheCalls)
logger.info("holon: reaktor object per thread: %s" % reaktorPerThread)



# the singleton reaktor if not reaktorPerThread
_reaktor = None if reaktorPerThread else _Reaktor(keepHistory)


# public -->

def reaktor():
    """Get reaktor object thats singleton to the current thread.

    You must not save a reference to a reaktor object on module or class
    level so reaktor objects bound to a thread can be dereferenced with
    the termination of the thread. Just always use this function, its cheap.
    """
    if not reaktorPerThread:
        return _reaktor

    thread = threading.currentThread()
    try:
        reaktor = thread._reaktor
    except AttributeError:
        logger.debug("holon: init reaktor for thread %s" % thread)
        reaktor = _Reaktor(keepHistory)
        thread._reaktor = reaktor
    return reaktor

# <--

