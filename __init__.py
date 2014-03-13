# -*- coding: utf-8 -*-
"""A python/json-interface to the txtr-reaktor
compatible with its jython/corba-interfaces.
For txtr-reaktor API see http://txtr.com/reaktor/api/
"""
__copyright__ = "2013 txtr GmbH"
__email__ = "info@txtr.com"
__status__ = "development"


from caching import CachingReaktor
from django.conf import settings
from reaktor import Reaktor
import threading, logging
# the errors are imported for module visibility, do not clean up
from reaktor import ReaktorApiError
from reaktor import ReaktorAuthError
from reaktor import ReaktorAccessError
from reaktor import ReaktorArgumentError
from reaktor import ReaktorEntityError
from reaktor import ReaktorIllegalCallError
from reaktor import ReaktorError
from reaktor import ReaktorHttpError
from reaktor import ReaktorIOError
from reaktor import ReaktorJSONRPCError


# cache calls and responses, call reaktor.clear() to clear history
CACHE_CALLS = False

# give every thread its own reaktor object
REAKTOR_PER_THREAD = False


logger = logging.getLogger(__name__)
# logger.info("holon: reaktor address is %s:%i%s"    %
#         (reaktor.REAKTOR_HOST, reaktor.REAKTOR_PORT, reaktor.REAKTOR_PATH))
# logger.info("holon: keep reaktor history: %s"      % KEEP_HISTORY)
# logger.info("holon: keep reaktor cache: %s"        % CACHE_CALLS)
# logger.info("holon: reaktor object per thread: %s" % REAKTOR_PER_THREAD)


# the reaktor class to be used to instanciate reaktor objects
REAKTOR_CLASS = CachingReaktor if CACHE_CALLS else Reaktor


# the singleton reaktor if not REAKTOR_PER_THREAD
REAKTOR = None if REAKTOR_PER_THREAD else REAKTOR_CLASS(**settings.REAKTORS['default'])


def reaktor(conf='default'):
    """Get reaktor object thats singleton to the current thread.

    You must not save a reference to a reaktor object on module or class
    level so reaktor objects bound to a thread can be dereferenced with
    the termination of the thread. Just always use this function, it's cheap.
    """
    if REAKTOR_PER_THREAD:

        thread = threading.currentThread()
        try:
            reaktor_instance = thread.reaktor[conf]
        except AttributeError:
            logger.debug("holon: init reaktor for thread %s" % thread)
            reaktor_instance = REAKTOR_CLASS(**settings.REAKTORS['default'])
            if not thread.reaktor:
                thread.reaktor = {}
            thread.reaktor[conf] = reaktor_instance

        return reaktor_instance

    return REAKTOR
