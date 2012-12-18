# -*- coding: utf-8 -*-
"""A python/json-interface to the txtr-reaktor
compatible with its jython/corba-interfaces.
For txtr-reaktor API see http://txtr.com/reaktor/api/
"""
__copyright__ = u"2012 txtr GmbH"
__author__    = u"Sascha Dieckmann"
__email__     = u"sascha.dieckmann@txtr.com"


import threading, logging
from django.conf import settings

from holon.reaktor import Reaktor, \
    ReaktorError, ReaktorHttpError, ReaktorIOError, \
    ReaktorApiError, ReaktorAuthError
from holon.caching import CachingReaktor


# keep call history to be logged eventually
KEEP_HISTORY = settings.KEEP_JSONRPC_HISTORY

# cache calls and responses, call reaktor.clear() to clear history
CACHE_CALLS = False

# give every thread its own reaktor object
REAKTOR_PER_THREAD = False


LOG = logging.getLogger(__name__)


reaktor.REAKTOR_HOST = settings.REAKTOR_HOST
reaktor.REAKTOR_PORT = int(settings.REAKTOR_PORT)
reaktor.REAKTOR_SSL  = reaktor.REAKTOR_PORT == 443
reaktor.REAKTOR_PATH = u"/json/rpc?v=2"

LOG.info("holon: reaktor address is %s:%i%s"    %
        (reaktor.REAKTOR_HOST, reaktor.REAKTOR_PORT, reaktor.REAKTOR_PATH))
LOG.info("holon: keep reaktor history: %s"      % KEEP_HISTORY)
LOG.info("holon: keep reaktor cache: %s"        % CACHE_CALLS)
LOG.info("holon: reaktor object per thread: %s" % REAKTOR_PER_THREAD)


# the reaktor class to be used to instanciate reaktor objects
REAKTOR_CLASS = CachingReaktor if CACHE_CALLS else Reaktor


# the singleton reaktor if not REAKTOR_PER_THREAD
REAKTOR = None if REAKTOR_PER_THREAD else REAKTOR_CLASS(KEEP_HISTORY)


# public -->

def reaktor():
    """Get reaktor object thats singleton to the current thread.

    You must not save a reference to a reaktor object on module or class
    level so reaktor objects bound to a thread can be dereferenced with
    the termination of the thread. Just always use this function, its cheap.
    """
    if REAKTOR_PER_THREAD:

        thread = threading.currentThread()
        try:
            reaktor_instance = thread.reaktor
        except AttributeError:
            LOG.debug("holon: init reaktor for thread %s" % thread)
            reaktor_instance = REAKTOR_CLASS(KEEP_HISTORY)
            thread.reaktor = reaktor_instance

        return reaktor_instance

    return REAKTOR

# <--

