from __future__ import absolute_import
from . import HttpService
from httplib import HTTPConnection, HTTPException, HTTPSConnection
from socket import timeout, error
import time


class HttpLibHttpService(HttpService):
    """
    HttpService using python batteries' httplib.
    """

    def __init__(self, *args, **kwargs):
        super(HttpLibHttpService, self).__init__(*args, **kwargs)
        if self.ssl:
            self.connection_class = HTTPSConnection
        else:
            self.connection_class = HTTPConnection

    def get_transport(self):
        """Helper method to improve testability."""
        return self.connection_class(self.host, self.port,
                                     timeout=self.connect_timeout)

    def _call(self, body, headers):
        start_time = time.time()
        try:
            connection = self.get_transport()
            response = connection.getresponse()
        except (HTTPException, timeout, error), e:
            raise self.communication_error_class(u"%s failed with %s when attempting to make a call to %s with body %s" % (self.__class__.__name__, e.__class__.__name__, self.base_url, body))
        else:
            data = unicode(response.read(), "utf-8")
        finally:
            connection.close()
        end_time = time.time()
        return response.status, data, (end_time - start_time)*1000

    @property
    def protocol(self):
        return self.connection_class._http_vsn_str
