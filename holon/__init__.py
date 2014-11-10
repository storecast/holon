# -*- coding: utf-8 -*-
"""A python/json-interface to the txtr-reaktor
compatible with its jython/corba-interfaces.
For txtr-reaktor API see http://txtr.com/reaktor/api/

:copyright: (c) 2014 by txtr GmbH.
:license: BSD, see LICENSE for more details.
"""

__version__ = "0.1.0"

# these are imported for module visibility, do not clean up
from reaktor import Reaktor
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
