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
    ReaktorError, ReaktorHttpError, ReaktorIOError, ReaktorApiError
from holon.caching import CachingReaktor


# keep call history to be logged eventually
KEEP_HISTORY = settings.KEEP_JSONRPC_HISTORY

# cache calls and responses, call reaktor.clear() to clear history
CACHE_CALLS = False

# give every thread its own reaktor object
REAKTOR_PER_THREAD = False


LOG = logging.getLogger(__name__)

# the internal settings are optional, they only apply to the json-rpc communication with the reaktor;
# in some installations one may take advantage from skins sitting with reaktor in the same local network
if getattr(settings, "REAKTOR_HOST_INTERNAL", "") and getattr(settings, "REAKTOR_PORT_INTERNAL", ""):
    reaktor.REAKTOR_HOST = settings.REAKTOR_HOST_INTERNAL
    reaktor.REAKTOR_PORT = int(settings.REAKTOR_PORT_INTERNAL)
else:
    reaktor.REAKTOR_HOST = settings.REAKTOR_HOST
    reaktor.REAKTOR_PORT = int(settings.REAKTOR_PORT)

reaktor.REAKTOR_SSL  = reaktor.REAKTOR_PORT == 443
reaktor.REAKTOR_PATH = getattr(settings, 'REAKTOR_PATH', '/api/1.36.0/rpc')
reaktor.CONNECTTIMEOUT = getattr(settings, 'HOLON_CONNECTTIMEOUT', 20)
reaktor.RUNTIMEOUT = getattr(settings, 'HOLON_RUNTIMEOUT', 40)
reaktor.DO_RETRY = getattr(settings, 'HOLON_DO_RETRY', False)
reaktor.RETRY_SLEEP = getattr(settings, 'HOLON_RETRY_SLEEP', 1.)


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

