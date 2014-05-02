from __future__ import absolute_import
from . import HttpService
from . import Response
from StringIO import StringIO
import pycurl
# import time


assert pycurl.version_info()[1] >= "7.19"


class PyCurlHttpService(HttpService):
    """HttpService using extra-fast pycurl."""

    def __init__(self, *args, **kwargs):
        super(PyCurlHttpService, self).__init__(*args, **kwargs)
        pycurl.global_init(pycurl.GLOBAL_ALL)

    def call(self, body):
         # to collect response data
        data = StringIO()
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
            "Content-Length: %i" % len(body),
            "Accept: application/json",
        ])

        # start_time = time.time()

        # the actual call
        try:
            curl.perform()
            code = curl.getinfo(pycurl.HTTP_CODE)
            # start_transfer_time = curl.getinfo(pycurl.STARTTRANSFER_TIME)
            total_time = curl.getinfo(pycurl.TOTAL_TIME)
            curl.close()
        except pycurl.error, err:
            # raise common error class
            raise self.communication_error_class(err[0], err[1])

        # total_time = time.time() - start_time

        data = data.getvalue()
        data = unicode(data, "utf-8")

        return Response(code, data, total_time*1000)

    @property
    def protocol(self):
        return self.base_url.split('://')[0].upper()
