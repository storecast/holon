from __future__ import absolute_import
from . import HttpService
from . import Response
from httplib import HTTPConnection
from httplib import HTTPException
from httplib import HTTPSConnection
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

    def call(self, body, request=None):
        try:
            headers = {}
            # this check is only here because we use barrel and ye olde mapper atm
            # remove this once everything comes through barrel
            if request is None:
                from apps.global_request.middleware import GlobalRequest
                request = GlobalRequest.get_request()
            connection = self.connection_class(self.host, self.port, timeout=self.connect_timeout)
            start_time = time.time()
            headers['User-Agent'] = self.user_agent.encode("utf-8")
            headers['Device-Info'] = request.META.get("HTTP_USER_AGENT", "")
            headers['X-Forwarded-For'] = request.META.get("REMOTE_ADDR")
            connection.request("POST", self.path, body, headers)
            response = connection.getresponse()
        except (HTTPException, timeout, error), e:
            raise self.communication_error_class(u"%s failed with %s when attempting to make a call to %s with body %s" % (self.__class__.__name__, e.__class__.__name__, self.base_url, body))
        else:
            data = unicode(response.read(), "utf-8")
        finally:
            connection.close()

        end_time = time.time()
        return Response(response.status, data, (end_time - start_time)*1000)

    @property
    def protocol(self):
        return self.connection_class._http_vsn_str
