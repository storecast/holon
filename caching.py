# -*- coding: utf-8 -*-
"""CachingReaktor is a caching descendant from holon.reaktor.Reaktor.
"""
import logging, threading
import reaktor


LOG = logging.getLogger(__name__)


class CachingReaktor(reaktor.Reaktor):
    """A caching descendant from holon.reaktor.Reaktor.
    """

    def __init__(self, *args):
        """Overwritten __init__.
        """
        super(CachingReaktor, self).__init__(*args)
        self.calls, self.docs, self.presentations = {}, {}, {}


    def clear(self):
        """Overwritten clear.
        """
        super(CachingReaktor, self).clear() # clear call history
        self.calls, self.docs, self.presentations = {}, {}, {} # clear cache


    def call(self, method, args):
        """Overwritten call.
        """
        if method == "WSDocMgmt.getDocument":
            return self.get_docs(args[0], [args[1]])[0]
        if method == "WSDocMgmt.getDocuments":
            return self.get_docs(args[0], args[1])

        key = u"%s %s" % (method, unicode(args))
        try:
            result = self.calls[key]
            LOG.debug("reaktor got result for %s from cache for thread %s"
                    % (method, threading.currentThread()))
        except KeyError:
            result = super(CachingReaktor, self).call(method, args)
            self.calls[key] = result
        return result


    def get_docs(self, token, docids):
        """Internal only.
        Cache document calls.
        """
        docids2get = [docId  for docId in docids if not docId in self.docs]
        if docids2get:
            docs = super(CachingReaktor, self).call(
                    self, "WSDocMgmt.getDocuments", [token, docids2get])
            for doc in docs:
                self.docs[doc.documentID] = doc

        docs = [self.docs[docId] for docId in docids]
        return docs
