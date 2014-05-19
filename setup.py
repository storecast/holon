"""A python/json-interface to the txtr-reaktor
compatible with its jython/corba-interfaces.
For txtr-reaktor API see http://txtr.com/reaktor/api/
"""

from distutils.core import setup

setup(
    name='holon',
    version='0.0.2',
    description='python interface to reaktor API',
    long_description=__doc__,
    license='BSD',
    author='txtr web team',
    author_email='web-dev@txtr.com',
    url='https://github.com/txtr/holon/',
    packages=['holon'],
    platforms='any',
    install_requires=['pycurl>=7.19.3.1'],
)
