#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Example for howto patch ugly UUID's in results of txtr-reaktor.
"""

if __name__ == "__main__":

    import os, sys
    sys.path.insert(0,
        os.path.join(os.path.dirname(__file__), os.pardir)) # pythonpath

    import reaktor, patch

    reaktor.REAKTOR_HOST = u"staging.txtr.com"
    reaktor.REAKTOR_PORT = 80
    reaktor.REAKTOR_SSL  = False
    reaktor.REAKTOR_PATH = u"/json/rpc?v=2"

    reaktor = reaktor.Reaktor()
    token, docId = "txtr.de", "bfzs289"
    keepIds = False

    doc = reaktor.WSDocMgmt.getDocument(token, docId)
    # access author via keys of dicts
    print doc["attributes"]["20514d7d-7591-49a4-a62d-f5c02a8f5edd"]
    # the same with attributes
    # sadly python doesn't accept attributes with "-" in its names
    print doc.attributes["20514d7d-7591-49a4-a62d-f5c02a8f5edd"]

    patch.patch(doc, keepIds)
    # access author via keys of dicts
    print doc["attributes"]["author"]
    # the same with attributes
    print doc.attributes.author

    # You should now have seen for times the author 'Hart, Maarten &apos;t'

