[![Build Status](https://travis-ci.org/txtr/holon.svg?branch=master)](https://travis-ci.org/txtr/holon)
[![Coverage Status](https://coveralls.io/repos/txtr/holon/badge.png?branch=master)](https://coveralls.io/r/txtr/holon?branch=master)

# [txtr](http://txtr.com/) library for communicating with txtr reaktor [API](http://txtr.com/reaktor/api/).

This library provides an interface to reaktor API.

## Installation

Nothing fancy - clone the repo and run
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

## Tests
`mock` is needed in order to run the tests. After installing it:
```
python -m unittest holon.tests
```

## License

BSD, see `LICENSE` for more details.

## Contributors

txtr web team - [web-dev@txtr.com](mailto:web-dev@txtr.com).
