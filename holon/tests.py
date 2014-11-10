from contextlib import contextmanager
from mock import Mock, patch
from reaktor import Reaktor, ReaktorObject
from services import HttpService
import unittest


class HttpServiceMock(HttpService):
    """This one is useful to test the base service methods."""
    pass
    protocol = 'HTTP/1.1'


class ServiceMock(HttpService):
    """This one is useful to check the service is contructed as expected."""
    __init__ = Mock(return_value=None)
    protocol = 'HTTP/1.1'


@contextmanager
def patch_json(reaktor, res='null', err='null'):
    from services import Response
    resp = u"""{{"error":{error},"result":{result}}}"""
    resp = resp.format(error=err, result=res)
    call_orig = reaktor.http_service.call
    try:
        reaktor.http_service.call = Mock(return_value=Response(200, resp, 0))
        yield reaktor.http_service.call
    finally:
        reaktor.http_service.call = call_orig


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
        call_mock.assert_called_with('RpcInterface.RpcFunction', ('java?', ),
                                     headers={'head': 'bang'})


class ReaktorTestCase(unittest.TestCase):
    def setUp(self):
        self.reaktor = Reaktor(**reaktor_config)

    @patch('holon.reaktor.id_generator', return_value='')
    def test_reaktor_call_default_converter(self, _):
        """Default reaktor data converter is `ReaktorObject.to_reaktorobject`."""
        with patch_json(self.reaktor, '{"prop":"value"}'):
            r = self.reaktor.call('Interface.Method', [])
            self.assertIsInstance(r, ReaktorObject)
            self.assertTrue(hasattr(r, 'prop'))
            self.assertEqual(r.prop, 'value')

    @patch('holon.reaktor.id_generator', return_value='')
    def test_reaktor_call_custom_converter(self, _):
        """Custom reaktor data converter."""
        custom_converter = Mock()
        with patch_json(self.reaktor, '{"prop":"value"}'):
            self.reaktor.call('Interface.Method', [],
                                  data_converter=custom_converter)
            custom_converter.assert_called_with({u'prop': u'value'})

    @patch('holon.reaktor.id_generator', return_value='')
    def test_reaktor_call_multiple_results(self, _):
        """Multiple results are converted to a list of objects."""
        with patch_json(self.reaktor, '[{"o":1}, {"o":2}, {"o":3}]'):
            r = self.reaktor.call('Interface.Method', [])
            self.assertIsInstance(r, list)
            self.assertTrue(len(r), 3)

    def test_name(self):
        """Reaktor instances have specific names."""
        self.assertEqual(self.reaktor.__name__, 'Reaktor.%s' % abs(hash(self.reaktor)))

    @patch('holon.reaktor.id_generator', return_value='')
    def test_history(self, _):
        """Reaktor history keep tracks of calls and is resetable."""
        with patch_json(self.reaktor, '[]'):
            self.reaktor.call('Interface.Method', [])
        self.assertEqual(len(self.reaktor.history), 1)
        self.reaktor.clear()
        self.assertEqual(self.reaktor.history, [])


class ReaktorObjectTestCase(unittest.TestCase):
    def setUp(self):
        self.reaktor = Reaktor(**reaktor_config)

    @patch('holon.reaktor.id_generator', return_value='')
    def test_getter(self, _):
        """Reaktor object implements automatic getters."""
        with patch_json(self.reaktor, '{"something":42}'):
            r = self.reaktor.call('Interface.Method', [])
            self.assertTrue(callable(r.getSomething))
            self.assertEqual(r.getSomething(), 42)

    @patch('holon.reaktor.id_generator', return_value='')
    def test_enum(self, _):
        """Reaktor object implements automatic enum getters (specific to the java backend)."""
        with patch_json(self.reaktor, '{"name":["e1", "e2", "e3"]}'):
            r = self.reaktor.call('Interface.getMeAJavaEnum', [])
            self.assertTrue(callable(r.name))
            self.assertEqual(r.name(), ["e1", "e2", "e3"])

    @patch('holon.reaktor.id_generator', return_value='')
    def test_attribute_error(self, _):
        """Reaktor object raises attribute error for element that do not exist in the JSON payload."""
        with patch_json(self.reaktor, '{"prop":"value"}'):
            r = self.reaktor.call('Interface.Whatever', [])
            self.assertRaises(AttributeError, lambda: r.wrong_prop)

    def test_readonly(self):
        """Reaktor object are readonly."""
        o = ReaktorObject({'prop': 'val'})
        with self.assertRaises(RuntimeError):
            o.attr = 'val'
        with self.assertRaises(RuntimeError):
            del o.prop
