from mock import Mock
from reaktor import Reaktor
from services import HttpService
import unittest


class HttpServiceMock(HttpService):
    pass


class ServiceMock(HttpService):
    __init__ = Mock(return_value=None)


reaktor_config = {
    'host': 'skins-staging-reaktor.intern.txtr.com',
    'port': 8080,
    'path': '/api/1.50.32/rpc',
    'ssl': False,
    'connect_timeout': 5,
    'run_timeout': 15,
    'communication_error_class': 'reaktor.ReaktorIOError',
    'keep_history': True,
    # 'http_service': 'services.httplib.HttpLibHttpService',
    'http_service': 'tests.HttpServiceMock',
    'user_agent': 'agent 212',
}


class ReaktorMetaTestCase(unittest.TestCase):
    def test_does_not_modify_passed_config(self):
        """Passed in dict remains intact."""
        backup_config = dict(**reaktor_config)
        Reaktor(**reaktor_config)
        self.assertDictEqual(reaktor_config, backup_config)

    def test_splits_kwargs_for_http_service(self):
        """Keyword args targeted at the underlying http service are sliced out."""
        from reaktor import ReaktorIOError
        service_args = {
            'host': 'skins-staging-reaktor.intern.txtr.com',
            'port': 8080,
            'path': '/api/1.50.32/rpc',
            'ssl': False,
            'connect_timeout': 5,
            'run_timeout': 15,
            'communication_error_class': ReaktorIOError,
            'user_agent': 'agent 212',
        }
        r = Reaktor(**dict(reaktor_config.items()+[('http_service', 'tests.ServiceMock')]))
        r.http_service.__init__.assert_called_with(**service_args)

    def test_injects_default_user_agent(self):
        """A default user agent is provided to the http service."""
        from reaktor import USERAGENT as user_agent
        r_config = dict(**reaktor_config)
        r_config.pop('user_agent')
        r = Reaktor(**r_config)
        self.assertEqual(r.http_service.user_agent, user_agent)


class ReaktorInterfaceTestCase(unittest.TestCase):
    def setUp(self):
        self.reaktor = Reaktor(**reaktor_config)

    def test_reaktor_call_curry(self):
        """Cached reaktor interfaces work fine with curried `reaktor.call()`."""
        rpc_interface = self.reaktor.RpcInterface
        self.assertEqual(rpc_interface.endpoint, self.reaktor)
        call_mock = Mock()
        from functools import partial
        self.reaktor.call = partial(call_mock, headers={'head': 'bang'})
        self.reaktor.RpcInterface.RpcFunction('java?')
        call_mock.assert_called_with('RpcInterface.RpcFunction', 'java?', headers={'head': 'bang'})
