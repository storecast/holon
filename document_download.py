import pycurl
import re
from holon import ReaktorIOError, ReaktorHttpError
from holon.reaktor import REAKTOR_HOST, REAKTOR_PORT, USERAGENT, CONNECTTIMEOUT, REAKTOR_SSL

# control character regex
CONTROL_CHAR_PATTERN = re.compile(
    u"[%s]" % re.escape(
        u"".join([unichr(cchar) for cchar in (
            range(0, 32) + range(127, 160))])))


def download_document(token, doc_id, path,
                      progress_func = None, options = None):
    """Downloads a document.
    Returns 'filename'-part from 'Content-disposition'-header.

    A callable 'progress-function' can be passed. It will be called in
    intervals with the download-ratio as argument:
    0.0 to 1.0 - total bytes downloaded divided by total bytes to download.
    To cancel the download let the progress-function return something
    evaluating to 'True'.

    A dictionary 'options' can be passed. It may contain entries
    - 'accesstype': 'ADEPT_DRM' to fetch documents with drm
    - 'version':    <int> for the document-version (starting with 1,
                           default is last version)

    A canceled download raises a ReaktorIOError.
    A local write-error raises a ReaktorIOError.

    token:         string, a txtr session-id
    doc_id:        string, a txtr document-id
    path:          string, path to local file
    progress_func: callable, defaults to None
    options:       dict, defaults to None

    Return: string, the filename as suggested by server
    """
    curl = pycurl.Curl()
    curl.setopt(pycurl.USERAGENT, USERAGENT.encode("utf-8"))
    curl.setopt(pycurl.CONNECTTIMEOUT, CONNECTTIMEOUT)
    curl.setopt(pycurl.SSL_VERIFYPEER, False)


    proto = u"http"
    if REAKTOR_SSL:
        proto += u"s"

    accesstype = u""
    if options and not options.get("accesstype") == None:
        if options["accesstype"] == "ADEPT_DRM":
            accesstype = u"/metadata/com.bookpac.exporter.fulfillmenttoken"
        else:
            raise RuntimeError(
                "unknown 'accesstype' in options:" +
                options["accesstype"])

    preview = u""
    if options and not options.get("preview") == None:
        preview = u"&deliverable=PREVIEW&format=" + options["preview"]

    version = u""
    if options and not options.get("version") == None:
        try:
            version = int(options["version"])
        except ValueError:
            raise RuntimeError(
                "bad 'version' in options:" +
                options["version"])
        version = u"&v=%i" % version

    url = u"%s://%s:%i/delivery/document/%s%s?token=%s%s%s" % (
        proto, REAKTOR_HOST, REAKTOR_PORT,
        doc_id, accesstype, token, preview, version)
    curl.setopt(pycurl.URL, url.encode("utf-8"))


    headers = [None]
    filename_pattern = re.compile(
        'Content-disposition: attachment;filename="(.*?)"')
    def header_func(line, headers = headers):
        """callback for curl for response-headers.
        """
        line = unicode(line, "latin1")
        if headers[0] == None:
            match = filename_pattern.search(line)
            if match:
                headers[0] = match.group(1)
    curl.setopt(pycurl.HEADERFUNCTION, header_func)


    if progress_func:
        def cb_curl_progress_func(down_total, down_now, up_total, up_now):
            """Call the actual progress-function.
            To be passed to curl.
            """
            # passed values are in bytes, specify the actual
            # gzipped stream, not the state of the downloaded
            # data, so lets propagate it as ratio:

            if down_total > 0:
                ratio = (1.0 * down_now / down_total)
            else:
                ratio = 0.0
            return progress_func(ratio) # return True to cancel download

        curl.setopt(pycurl.NOPROGRESS, 0)
        curl.setopt(pycurl.PROGRESSFUNCTION, cb_curl_progress_func)


    fhl = open(path, "wb")
    curl.setopt(pycurl.WRITEDATA, fhl)
    curl.setopt(pycurl.ENCODING, "gzip")

    try:
        curl.perform()
        fhl.close()
        code = curl.getinfo(pycurl.HTTP_CODE)
        curl.close()

    except pycurl.error, err:
        fhl.close()
        curl.close()
        # err[0] == 23: # write error. no space left on device?
        # err[0] == 42: # aborted by progress function
        raise ReaktorIOError(err[0], err[1])

    except Exception:
        fhl.close()
        curl.close()
        raise

    if not code == 200:
        # raise ReaktorError for http response status <> 200
        raise ReaktorHttpError(
            code, u"server returned status %i" % code)

    filename = headers[0]
    if filename:
        filename = CONTROL_CHAR_PATTERN.sub(u"_", filename)
    return filename

