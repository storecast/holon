"""A python/json-interface to the txtr-reaktor
compatible with its jython/corba-interfaces.
For txtr-reaktor API see http://txtr.com/reaktor/api/
"""

from setuptools import setup, find_packages
from holon import __version__

setup(
    name='holon',
    version=__version__,
    description='python interface to reaktor API',
    long_description=__doc__,
    license='BSD',
    author='txtr web team',
    author_email='web-dev@txtr.com',
    url='https://github.com/txtr/holon/',
    packages=find_packages(exclude=['examples',]),
    platforms='any',
    install_requires=['pycurl>=7.19.3.1'],
)
