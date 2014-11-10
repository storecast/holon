"""
HttpService base interface.
This abstracts the differences between libraries to handle requests and their
responses (computing request duration, for example).
An HttpService is supposed to be injected into an API object upon its
construction.
"""
from collections import namedtuple


Response = namedtuple('Response', ('status', 'data', 'time'))


class HttpService(object):
    """
    Base class defining what a HttpService is in holon
    """

    def __init__(self, host=None, port=None, path=None, ssl=None,
                 user_agent=None, connect_timeout=None, run_timeout=None,
                 communication_error_class=None):
        self.host = host
        self.port = port
        self.path = path
        self.ssl = ssl if ssl is not None else port == 443
        self.user_agent = user_agent
        self.connect_timeout = connect_timeout
        self.run_timeout = run_timeout
        self.communication_error_class = communication_error_class or Exception

    def call(self, method, params, request_id):
        """
        :param method : the json-rpc method to call, e.g. WSReaktorMgmt.getNature
        :param params : the params of above method
        :param request_id : id to identify the request

        :returns Response
        """
        raise NotImplementedError()

    @property
    def base_url(self):
        """
        Base URL to the json interface.
        """
        if not hasattr(self, "_base_url_cache"):
            self._base_url_cache = u"%s://%s:%i%s" % (u"https" if self.ssl else u"http", self.host, self.port, self.path)
        return self._base_url_cache

    @property
    def protocol(self):
        raise NotImplementedError()
