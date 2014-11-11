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

    def _call(self, body, headers):
        raise NotImplementedError()

    def call(self, body, headers=None):
        """
        :param body : the json-rpc payload
        :param headers : the params of above method

        :returns Response
        """
        if not headers:
            headers = {}
        if self.user_agent and 'User-Agent' not in headers:
            headers['User-Agent'] = self.user_agent.encode("utf-8")
        return Response(*self._call(body, headers))

    def get_transport(self):
        """Helper method to improve testability."""
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
