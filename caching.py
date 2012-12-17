# -*- coding: utf-8 -*-
import logging, threading
import reaktor


logger = logging.getLogger(__name__)


class CachingReaktor(reaktor.Reaktor):
    ""

    def __init__(self, *args):
        """Overwritten __init__.
        """
        reaktor.Reaktor.__init__(self, *args)
        self.calls, self.docs, self.presentations = {}, {}, {}


    def clear(self):
        """Overwritten clear.
        """
        reaktor.Reaktor.clear(self) # clear call history
        self.calls, self.docs, self.presentations = {}, {}, {} # clear cache


    def call(self, method, args):
        """Overwritten call.
        """
        if method == "WSDocMgmt.getDocument":
            return self._getDocs(args[0], [args[1]])[0]
        if method == "WSDocMgmt.getDocuments":
            return self._getDocs(args[0], args[1])
        if method == "WSFeaturedContentMgmt.getContentPresentationByID":
            return self.getContentPresentation(args)

        key = u"%s %s" % (method, unicode(args))
        try:
            result = self.calls[key]
            logger.debug("reaktor got result for %s from cache for thread %s"
                    % (method, threading.currentThread()))
        except KeyError:
            result = reaktor.Reaktor.call(self, method, args)
            self.calls[key] = result
        return result


    def _getDocs(self, token, docIds):
        """Internal only.
        Cache document calls.
        """
        docIds2get = [docId  for docId in docIds if not docId in self.docs]
        if docIds2get:
            docs = reaktor.Reaktor.call(
                    self, "WSDocMgmt.getDocuments", [token, docIds2get])
            for doc in docs:
                self.docs[doc.documentID] = doc

        docs = [self.docs[docId] for docId in docIds]
        return docs


    def getContentPresentation(self, args):
        """Internal only.
        Cache WSFeaturedContentMgmt.getContentPresentationByID.
        """
        args = list(args)
        offs, count = args[3:5]

        args[3], args[4] = 0, -1
        args[5] = None
        key = "%s %s %s %i %i %s %s" % tuple(args)

        pres = self.presentations.get(key)
        if pres == None:
            pres = reaktor.Reaktor.call(self,
                "WSFeaturedContentMgmt.getContentPresentationByID", args)
            self.presentations[key] = pres

        return pres
        if count < 1:
            return pres[offs:]
        return pres[offs:offs + count]

