# -*- coding: utf-8 -*-
"""A python/json-interface to the txtr-reaktor
compatible with its jython/corba-interfaces.
For txtr-reaktor API see http://txtr.com/reaktor/api/

License: FreeBSD
Support: support@txtr.com

Requirements:
- python >= 2.4
- pycurl
- json:
   * with python 2.6 buildin json will be used
   * with python < 2.6 simplejson if available:
      http://code.google.com/p/simplejson , MIT License
   * as last fallback modified json implementation from Patrick D. Logan:
      http://sourceforge.net/projects/json-py , LGPL, in repository

Install:
- Install python >= 2.4
- Install pycurl
- With python < 2.6 install simplejson

Example:
...
from reaktor import reaktor
token = reaktor.WSAuth.authenticateAnonymous().token
document = reaktor.WSDocMgmt.getDocument(token, document_id)
...
"""


__version__ = "0.0.1"
__license__ = "FreeBSD"
__copyright__ = """
Copyright 2010 txtr GmbH. All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are
permitted provided that the following conditions are met:

   1. Redistributions of source code must retain the above copyright notice, this list of
      conditions and the following disclaimer.

   2. Redistributions in binary form must reproduce the above copyright notice, this list
      of conditions and the following disclaimer in the documentation and/or other materials
      provided with the distribution.

THIS SOFTWARE IS PROVIDED BY TXTR GMBH ``AS IS'' AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those of the
authors and should not be interpreted as representing official policies, either expressed
or implied, of txtr GmbH.
"""
__email__ = "info@txtr.com"
__status__ = "development"


import os
import random
import re
import sys
import sha
import string
import time
import types
import logging
import StringIO
from json import dumps as jsonwrite
from json import loads as jsonread


LOG = logging.getLogger(__name__)
IDCHARS = string.ascii_lowercase+string.digits # for random RPC ID


# http-header User-Agent
USERAGENT = u"hreaktor/%s/%s (py%i.%i.%i)" % \
    (__version__, sys.platform,
     sys.version_info[0], sys.version_info[1], sys.version_info[2])
try:
    USERAGENT = "%s%s" % (USERAGENT[:-1],
    ";%s-%s.%s)" % (os.uname()[0], os.uname()[2], os.uname()[4]))
except AttributeError:
    # no os.uname in win32
    pass


CONNECTTIMEOUT = 20    # connect timeout
RUNTIMEOUT     = 40    # runtime timeout, not applied to downloads
DO_RETRY       = False # retry Reaktor call once in case of failure
RETRY_SLEEP    = 1.    # how many seconds to sleep before retrying (float)

REAKTOR_HOST = u"txtr.com"
REAKTOR_PORT = 443
REAKTOR_SSL  = True
REAKTOR_PATH = u"/json/rpc"


__GETTER_REGEX__ = re.compile("get([A-Z].*)")


# the PyCurlHttpService is the preferred one, as it is assumed to be faster
try:
    from services import PyCurlHttpService
except ImportError:
    from services import HttplibHttpService
    HTTP_SERVICE_CLASS = HttplibHttpService
else:
    HTTP_SERVICE_CLASS = PyCurlHttpService


class ReaktorObject(dict):
    """A local wrapper for datastructures returned by calls to txtr-reaktor.

    hreaktor.Reaktor calls the json-interfaces of txtr-reaktor. Its json-
    responses are decoded into python-dicts and -lists. For our convenience and
    to keep signatures compatible to jython/corba-interfaces to txtr-reaktor
    lets extend python-dict to ReaktorObject and translate all dicts returned
    by txtr-reaktor into instances of this so we can traverse txtr-reaktor
    datastructures as hierarchies of objects.

    You shouldn't need to instantiate ReaktorObject's by yourself.
    """

    @staticmethod
    def to_reaktorobject(attr):
        """Recursive translation of dicts|lists into [lists of] ReaktorObject's
        Internal only.
        """
        attr_type = type(attr)

        if attr_type == types.DictType:
            return ReaktorObject(
    dict((key, ReaktorObject.to_reaktorobject(attr[key])) for key in attr))

        if attr_type == types.ListType:
            return [
    ReaktorObject.to_reaktorobject(list_member) for list_member in attr]

        return attr # attr should be a simple datatype - string, int, ...


    def __init__(self, data = None):
        """Init. Internal only.
        data: dict, defaults to None
        """
        if data:
            dict.__init__(self, data)


    def __getattr__(self, name):
        """Implements dequalification of an unknown attribute.
        Raises AttributeError for unknown attributes.
        """
        match = __GETTER_REGEX__.match(name)
        if match:
             # requested a getter method
            key = match.group(1)
            key = key[0].lower() + key[1:]
            if key in self:
                return lambda: self[key]

        elif name == "name" and len(self) == 1 and name in self:
            # this is a java enum
            return lambda: self["name"]

        else:
            try:
                return self[name]
            except KeyError:
                pass

        raise AttributeError(
            u"ReaktorObject object has no attribute '%s'" % name)


    def __setattr__(self, name, val):
        """Implements setting an attribute.
        Raises RuntimeError because setting attributes makes no sense here.
        """
        raise RuntimeError(u"ReaktorObject object is readonly.")


    def __delattr__(self, name):
        """Implements deleting an attribute.
        Raises RuntimeError because deleting attributes makes no sense here.
        """
        raise RuntimeError(u"ReaktorObject object is readonly.")




class ReaktorError(Exception):
    """Base of errors to be thrown by class Reaktor.
    Meaning of self.code depends on sub classes.
    """
    def __init__(self, code = 0, message = None):
        """Init.
        code: int, error-code
        message: string
        """
        Exception.__init__(self, message)
        self.code, self.message = code, message
        LOG.error("reaktor error: %s %s" % (code, message))

    def __str__(self):
        """Get string for exception.
        """
        return "%s: %s" % (self.code, self.message)


class ReaktorIOError(ReaktorError):
    """ReaktorError to be thrown by class Reaktor,
    caused by IO problems, e.g. in sockets.
    self.code here is actually a curl error code.
    """
    pass


class ReaktorHttpError(ReaktorError):
    """ReaktorError to be thrown by Reaktor,
    caused by the remote reaktor httpserver.
    self.code here is an http status code.
    """
    pass


class ReaktorJSONRPCError(ReaktorError):
    """ReaktorError to be thrown by class Reaktor,
    caused by an RPC ID mismatch in request and response.
    self.code here is an http status code.
    """
    pass


class ReaktorApiError(ReaktorError):
    """ReaktorError to be thrown by class Reaktor,
    caused by the remote reaktor api.
    self.code here is a reaktor error message.
    """
    AUTHENTICATION_INVALID         = u"AUTHENTICATION_INVALID"
    DISCOVERY_SERVICE_ACCESS_ERROR = u"DISCOVERY_SERVICE_ACCESS_ERROR"
    ILLEGAL_ARGUMENT_ERROR         = u"ILLEGAL_ARGUMENT_ERROR"
    UNKNOWN_ENTITY_ERROR           = u"UNKNOWN_ENTITY_ERROR"
    ILLEGAL_CALL                   = u"ILLEGAL_CALL"
    REQUESTED_FEATURE_NOT_FOUND    = u"Requested feature not found."
    DOCUMENT_IS_REMOVED            = u"Document is removed"

    def __init__(self, code = 0, message = None):
        super(ReaktorApiError, self).__init__(code = code, message = message)




class Reaktor(object):
    """A python/json-interface to the txtr-reaktor
    compatible with its jython/corba-interfaces.
    For txtr-reaktor API see http://txtr.com/reaktor/api/

    Attributes of Reaktor-objects dequalify into objects representing
    txtr-reaktor interfaces of the same name. Attributes of such an
    Interface-object in turn dequalify into a function of the interface.
    """
    class Interface(object):
        """Internal only. See Reaktor.
        """
        def __init__(self, interface_name, call):
            """Init. Internal only.
            """
            self._interface_name, self.call = interface_name, call


        def __getattr__(self, function_name):
            """Implements dequalification of an unknown attribute.
            """
            ifcfunc = u"%s.%s" % (self._interface_name, function_name)
            func = lambda *args: self.call(ifcfunc, args)
            self.__dict__[function_name] = func # cache it
            return func


    @property
    def __name__(self):
        """We need a name for this object for newrelic to trace Reaktor.call.

            abs(), because hash is sometimes negative which looks ugly
        """
        return u'%s.%s' % (self.__class__.__name__, abs(hash(self)))


    def __getattr__(self, interface_name):
        """Implements dequalification of an unknown attribute.
        """
        interface = Reaktor.Interface(interface_name, self.call)
        self.__dict__[interface_name] = interface # cache it
        return interface


    def __init__(self, keep_history=False):
        """Init.
        Pass True for keep_history to keep a call history and get
        it with get_history.
        """
        self.history = [] if keep_history else None
        self.http_service = HTTP_SERVICE_CLASS(REAKTOR_HOST, REAKTOR_PORT, REAKTOR_PATH, REAKTOR_SSL, USERAGENT, CONNECTTIMEOUT, RUNTIMEOUT, ReaktorIOError)


    def clear(self):
        """Clear call history if any.
        """
        if self.history:
            self.history = []


    def get_history(self):
        """Get call history if any.
        If passed True to __init__ it returns a list else None.
        """
        return self.history


    def _call(self, post, url):
        """Do the actual call, including retry mechanism and logging.

        :param post: string with POST parameters
        :param url: URL posted to, used for logging
        :return: Response
        """
        error_class = self.http_service.communication_error_class
        try:
            response = self.http_service.call(post)
        except error_class, first_err:
            do_raise = True
            # hard-coding calls _not_ to retry as long as it is only one
            if DO_RETRY and not 'WSShopMgmt.checkoutBasket' in post:
                LOG.error('reaktor error %s, url: %s, DO RETRY' % (
                    first_err, url))
                # sleep and call again
                time.sleep(RETRY_SLEEP)
                try:
                    response = self.http_service.call(post)
                    do_raise = False
                    error = None
                except error_class, retry_err:
                    error = retry_err
            else:
                error = first_err

            if do_raise:
                LOG.error('reaktor error %s, url: %s, RAISING' % (
                    error, url))
                raise error

        return response


    def call(self, function, args):
        """The actual remote call txtr reaktor. Internal only.
        function: string, '<interface>.<function>' of txtr reaktor
        args: list of arguments for '<interface>.<function>'
        Return: ReaktorObject of list of ReaktorObject's
        """
        # some args might not be JSON-serializable, e.g. sets
        params = [list(arg) if isinstance(arg, set) else arg for arg in args]

        # mandatory RPC ID
        request_id = random_id()
        # json-encode request data
        post = jsonwrite({
            u"method": function,
            u"params": params,
            u"id": request_id,
            })
        url = u"%s%sjson=%s" % (self.http_service.base_url,  u"&" if "?" in self.http_service.base_url else u"?", post)

        response = self._call(post, url)

        if not self.history == None:
            self.history.append((url, response.status, int(response.time),))

        LOG.debug("\nRequest:\n%s\nResponse:\n%s" % (post, response.data))

        # raise ReaktorHttpError for http response status <> 200
        if not response.status == 200:
            raise ReaktorHttpError(
                response.status, u"server returned status %i: %s" % (response.status, response.data))

        # json-decode response data
        data = jsonread(response.data)

        # raise ReaktorApiError for reaktor errors
        err = data.get("error")
        if err:
            code = err.get("reaktorErrorCode", err.get("code", "error code unknown"))
            err = err.get("msg", unicode(code))
            raise ReaktorApiError(code, err)

        # check response RPC ID _after_ checking for ReaktorAPIError
        # somebody didn't read http://www.jsonrpc.org/specification
        response_id = data.get("id", "")
        if response_id != request_id:
            raise ReaktorJSONRPCError(
                response.status, u"invalid RPC ID response %s != request %s" % (
                    response_id, request_id))

        # return result as ReaktorObject('s) - if Reaktor doesn't violate the
        # JSONRPC spec by not sending a result.
        data = data.get("result", {})
        return ReaktorObject.to_reaktorobject(data)





# Some convenience stuff:


def hash_password(password):
    """Get a txtr-compatible hash for passed password.
    password: string
    Return: string
    """
    hsh = sha.sha()
    hsh.update(password)
    return hsh.hexdigest()


def random_id(length=8):
    """Generate random id, to be used as RPC ID."""
    return_id = ''
    for i in range(length):
        return_id += random.choice(IDCHARS)
    return return_id


