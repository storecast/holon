# -*- coding: utf-8 -*-
import os
import random
import re
import sys
import hashlib
import string
import logging
import urllib2
import inspect
from importlib import import_module
from json import dumps as jsonwrite
from json import loads as jsonread
from . import services
from . import __version__


logger = logging.getLogger(__name__)
# provide a separate logger for easing configuration
logger_request = logging.getLogger('holon.request')


# http-header User-Agent
USERAGENT = u"hreaktor/%s/%s (py%i.%i.%i)" % (
    __version__, sys.platform,
    sys.version_info[0],
    sys.version_info[1],
    sys.version_info[2]
)
try:
    USERAGENT = "%s%s" % (
        USERAGENT[:-1],
        ";%s-%s.%s)" % (os.uname()[0], os.uname()[2], os.uname()[4])
    )
except AttributeError:
    # no os.uname in win32
    pass


__GETTER_REGEX__ = re.compile("get([A-Z].*)")


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
        if isinstance(attr, dict):
            return ReaktorObject(dict((key, ReaktorObject.to_reaktorobject(attr[key])) for key in attr))

        if isinstance(attr, list):
            return [ReaktorObject.to_reaktorobject(list_member) for list_member in attr]

        return attr  # attr should be a simple datatype - string, int, ...

    def __init__(self, data=None):
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


class ReaktorMeta(type):
    """Metaclass for the reaktor object. It hijacks the kwargs on Reaktor class
    instantiation and replaces the http service params by a shiny object of the
    given type, built with the given params.
    """
    def __call__(self, *args, **kw):
        kwargs = dict(**kw)
        http_service = kwargs.pop('http_service')
        http_class = self.import_class_from_ns(http_service)

        # build kwargs for http service
        keys = inspect.getargspec(services.HttpService.__init__).args
        http_kwargs = dict(zip(keys, [None] * len(keys)))
        http_kwargs.pop('self')
        for k in http_kwargs:
            http_kwargs[k] = kwargs.pop(k, None)

        http_service = self.build_http_service(http_class, http_kwargs)
        try:
            o = super(ReaktorMeta, self).__call__(http_service, *args, **kwargs)
            return o
        except TypeError as e:
            raise RuntimeError(e)

    def import_class_from_ns(self, ns):
        http_ns, http_class = ('.' + ns).rsplit('.', 1)
        abs_ns = self.__module__.rsplit('.', 1)[0] + http_ns
        module = import_module(abs_ns)
        return getattr(module, http_class)

    def build_http_service(self, http_service_class, conf):
        error_class = conf.get('communication_error_class')
        if isinstance(error_class, basestring):
            conf['communication_error_class'] = self.import_class_from_ns(error_class)
        if not conf['user_agent']:
            conf['user_agent'] = USERAGENT
        return http_service_class(**conf)


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
        def __init__(self, interface_name, endpoint):
            """Init. Internal only.
            """
            self._interface_name, self.endpoint = interface_name, endpoint

        def __getattr__(self, function_name):
            """Implements dequalification of an unknown attribute.
            """
            ifcfunc = u"%s.%s" % (self._interface_name, function_name)
            func = lambda *args, **kwargs: self.endpoint.call(ifcfunc, args, **kwargs)
            self.__dict__[function_name] = func  # cache it
            return func

    __metaclass__ = ReaktorMeta

    @property
    def __name__(self):
        """We need a name for this object for newrelic to trace Reaktor.call.
        abs(), because hash is sometimes negative which looks ugly
        """
        return u'%s.%s' % (self.__class__.__name__, abs(hash(self)))

    def __getattr__(self, interface_name):
        """Implements dequalification of an unknown attribute.
        """
        interface = Reaktor.Interface(interface_name, self)
        self.__dict__[interface_name] = interface  # cache it
        return interface

    def __init__(self, http_service, keep_history=False):
        """Init.
        Pass True for keep_history to keep a call history and get
        it with get_history.
        """
        self.history = [] if keep_history else None
        self.http_service = http_service

    def clear(self):
        """Clear call history if any.
        """
        if self.history:
            self.history = []

    def call(self, function, args, data_converter=None, headers=None):
        """The actual remote call txtr reaktor. Internal only.
        function: string, '<interface>.<function>' of txtr reaktor
        args: List of arguments for '<interface>.<function>'
        data_converter: The callable used to cast the JSON structure a python
                        instance (defaults to `ReaktorObject.to_reaktorobject`)
        headers: Additional headers to pass in
        return: Instance(s) built using the provided `data_converter`
        """
        # some args might not be JSON-serializable, e.g. sets
        params = [list(arg) if isinstance(arg, set) else arg for arg in args]

        # mandatory RPC ID
        request_id = id_generator()
        # json-encode request data
        post = jsonwrite({u"method": function,
                          u"params": params,
                          u"id": request_id})

        response = None
        try:
            response = self.http_service.call(post, headers or {})
        finally:
            resp_status = response.status if response else 'ERR'
            resp_time = response.time if response else -1
            resp_data = response.data if response else None

            summary = dict(
                request=u'POST {fn} {params} {protocol}'.format(
                    fn=function, params=params,
                    protocol=self.http_service.protocol
                ),
                status=resp_status,
                length=len(post),
                duration=resp_time,
                request_id=request_id,
                headers=headers
            )

            if self.history is not None:
                self.history.append(summary)

            logger_request.info(summary['request'], extra=summary)
            if resp_data:
                logger.debug(resp_data)

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
            msg = err.get("msg", unicode(code))
            call_id = err.get("callId")
            if code == ReaktorApiError.AUTHENTICATION_INVALID:
                raise ReaktorAuthError(msg, call_id)
            elif code == ReaktorApiError.DISCOVERY_SERVICE_ACCESS_ERROR:
                raise ReaktorAccessError(msg, call_id)
            elif code == ReaktorApiError.ILLEGAL_ARGUMENT_ERROR:
                raise ReaktorArgumentError(msg, call_id)
            elif code == ReaktorApiError.UNKNOWN_ENTITY_ERROR:
                raise ReaktorEntityError(msg, call_id)
            elif code == ReaktorApiError.ILLEGAL_CALL:
                raise ReaktorIllegalCallError(msg, call_id)
            else:
                raise ReaktorApiError(msg, code, call_id)

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
        if data_converter is None:
            data_converter = ReaktorObject.to_reaktorobject
        return data_converter(data)

    def get_remote_version(self):
        reaktor_host = self.http_service.host
        reaktor_port = '8080' if 'intern' in reaktor_host else self.http_service.port
        try:
            version_txt = urllib2.urlopen('http://%s:%s/api/version.txt' % (reaktor_host, reaktor_port))
            prefix = 'version: '
            for line in version_txt:
                if line.startswith(prefix):
                    return line[len(prefix):].strip()
        except urllib2.HTTPError as e:
            return e.msg
        finally:
            try:
                version_txt.close()
            except NameError:
                pass

    def get_api_version(self):
        return re.sub(r'/api/(.*)/rpc', r'\1', self.http_service.path)


class ReaktorError(Exception):
    """Base of errors to be thrown by class Reaktor.
    Meaning of self.code depends on sub classes.
    """
    def __init__(self, message=None, code=0, call_id=None):
        """Init.
        code: int, error-code
        message: string
        call_id: string, id used for reaktor debugging
        """
        super(Exception, self).__init__(message)
        self.code, self.message, self.call_id = code, message, call_id
        logger.error("reaktor error: %s" % str(self))

    def __str__(self):
        """Get string for exception."""
        return "%s | callId: %s | %s" % (self.code, self.call_id, self.message)


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
    AUTHENTICATION_INVALID = u"AUTHENTICATION_INVALID"
    DISCOVERY_SERVICE_ACCESS_ERROR = u"DISCOVERY_SERVICE_ACCESS_ERROR"
    ILLEGAL_ARGUMENT_ERROR = u"ILLEGAL_ARGUMENT_ERROR"
    UNKNOWN_ENTITY_ERROR = u"UNKNOWN_ENTITY_ERROR"
    ILLEGAL_CALL = u"ILLEGAL_CALL"
    REQUESTED_FEATURE_NOT_FOUND = u"Requested feature not found."
    DOCUMENT_IS_REMOVED = u"Document is removed"


class ReaktorAuthError(ReaktorApiError):
    code = ReaktorApiError.AUTHENTICATION_INVALID

    def __init__(self, message=None, call_id=None):
        super(ReaktorApiError, self).__init__(message, self.code, call_id)


class ReaktorAccessError(ReaktorApiError):
    code = ReaktorApiError.DISCOVERY_SERVICE_ACCESS_ERROR

    def __init__(self, message=None, call_id=None):
        super(ReaktorApiError, self).__init__(message, self.code, call_id)


class ReaktorArgumentError(ReaktorApiError):
    code = ReaktorApiError.ILLEGAL_ARGUMENT_ERROR

    def __init__(self, message=None, call_id=None):
        super(ReaktorApiError, self).__init__(message, self.code, call_id)


class ReaktorEntityError(ReaktorApiError):
    code = ReaktorApiError.UNKNOWN_ENTITY_ERROR

    def __init__(self, message=None, call_id=None):
        super(ReaktorApiError, self).__init__(message, self.code, call_id)


class ReaktorIllegalCallError(ReaktorApiError):
    code = ReaktorApiError.ILLEGAL_CALL

    def __init__(self, message=None, call_id=None):
        super(ReaktorApiError, self).__init__(message, self.code, call_id)


# Some convenience stuff:

def hash_password(password):
    """Get a txtr-compatible hash for passed password.
    password: string
    Return: string
    """
    hsh = hashlib.sha1()
    hsh.update(password)
    return hsh.hexdigest()


def id_generator(size=8, chars=string.ascii_lowercase + string.digits):
    """Generate random id, to be used as RPC ID."""
    return ''.join(random.choice(chars) for x in range(size))
