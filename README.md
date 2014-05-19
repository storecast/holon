# [txtr](http://txtr.com/) library for communicating with txtr reaktor [API](http://txtr.com/reaktor/api/).

This library provides an interface to reaktor API.

## Installation

Nothing to fancy - clone the repo and run
```
python setup.py install
```

##### Requirements:
`pycurl`. If using python < 2.6, then `simplejson` is also required.

## Usage

```
from reaktor import reaktor
token = reaktor.WSAuth.authenticateAnonymous().token
document = reaktor.WSDocMgmt.getDocument(token, document_id)
```

## License

BSD, see `LICENSE` for more details.

## Contributors

txtr web team - [web-dev@txtr.com](mailto:web-dev@txtr.com).
