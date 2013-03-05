"""
HttpService interface plus two implementations of it.
A HttpService is supposed to be injected into an API object
upon its construction.
"""


from StringIO import StringIO
from collections import namedtuple
from httplib import HTTPConnection, HTTPSConnection, HTTPException
import time


Response = namedtuple('Response', ('status', 'data', 'time'))


class HttpService(object):
    """
    Base class defining what a HttpService is in holon
    """

    def __init__(self, host="txtr.com", port=443, path=u"/json/rpc", ssl=True, user_agent="hreaktor", connect_timeout=20, run_timeout=40, communication_error_class=None):
        self.host = host
        self.port = port
        self.path = path
        self.ssl = ssl
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



class HttplibHttpService(HttpService):
    """
    HttpService using python batteries' httplib.
    """

    def __init__(self, *args, **kwargs):
        super(HttplibHttpService, self).__init__(*args, **kwargs)
        if self.ssl:
            self.connection_class = HTTPSConnection
        else:
            self.connection_class = HTTPConnection


    def call(self, body):

        try:
            connection = self.connection_class(self.host, self.port, timeout=self.connect_timeout)

            start_time = time.time()
            connection.request("POST", self.path, body)
            response = connection.getresponse()
        except HTTPException, e:
            # raise common error class
            raise self.communication_error_class(message=u"%s failed with %s when attempting to make a call to %s with body %s" % (self.__class__.__name__, e.__class__.__name__, self.base_url, body))
        else:
            data = unicode(response.read(), "utf-8")
        finally:
            connection.close()

        end_time = time.time()

        return Response(response.status, data, (end_time - start_time)*1000)



# only creating PyCurlHttpService, if pycurl is also available
try:
    import pycurl
except ImportError:
    pass
else:
    pycurl.global_init(pycurl.GLOBAL_ALL)


    class PyCurlHttpService(HttpService):
        """
        HttpService using extra-fast pycurl.
        """

        def call(self, body):

            data = StringIO() # to collect response data

            # construct curl object
            curl = pycurl.Curl()
            curl.setopt(pycurl.USERAGENT,      self.user_agent.encode("utf-8"))
            curl.setopt(pycurl.TIMEOUT,        self.run_timeout)
            curl.setopt(pycurl.CONNECTTIMEOUT, self.connect_timeout)
            curl.setopt(pycurl.SSL_VERIFYPEER, False)
            curl.setopt(pycurl.URL,            self.base_url.encode("utf-8"))
            curl.setopt(pycurl.POSTFIELDS,     body.encode("utf8"))
            curl.setopt(pycurl.WRITEFUNCTION,  data.write)
            curl.setopt(pycurl.ENCODING,       "")
            curl.setopt(pycurl.HTTPHEADER,     [
                "Content-type: application/octet-stream",
                "Content-Length: %i" % len(body)])

            start_time = time.time()

            # the actual call
            try:
                curl.perform()
                code = curl.getinfo(pycurl.HTTP_CODE)
                curl.close()
            except pycurl.error, err:
                # raise common error class
                raise self.communication_error_class(err[0], err[1])

            end_time = time.time()

            data = data.getvalue()
            data = unicode(data, "utf-8")

            return Response(code, data, (end_time-start_time)*1000)


