#!/usr/bin/env python3

import unittest
import unittest.mock as mock
import xml.etree.ElementTree as ET
import sys

sys.path.append('..')


from check_monit import main
from check_monit import commandline
from check_monit import print_output
from check_monit import get_service_output


class MockRequest():
    def __init__(self, status_code, content):
        self.status_code = status_code
        self.content = content
    def content(self):
        return self.content


class CLITesting(unittest.TestCase):

    def test_commandline(self):
        actual = commandline(['-H', 'localhost', '-P', 'password', '-U', 'user'])
        self.assertEqual(actual.host, 'localhost')
        self.assertEqual(actual.port, 2812)
        self.assertEqual(actual.user, 'user')
        self.assertEqual(actual.password, 'password')

    def test_service_output(self):
        input_element = ET.Element('foobar')
        actual = get_service_output(-1, input_element)
        self.assertEqual(actual, 'Service (type=-1) not implemented')

        input_element = ET.ElementTree(ET.fromstring("""<doc><status>unittest</status></doc>"""))
        actual = get_service_output(3, input_element)
        self.assertEqual(actual, 'unittest')

        input_element = ET.ElementTree(ET.fromstring("""<doc><program><output></output></program></doc>"""))
        actual = get_service_output(7, input_element)
        self.assertEqual(actual, 'no command output available')

        input_element = ET.ElementTree(ET.fromstring("""<doc><program><output>foobar</output></program></doc>"""))
        actual = get_service_output(7, input_element)
        self.assertEqual(actual, 'foobar')

        input_element = ET.ElementTree(ET.fromstring("""<doc><program><output>foot</output><output>bath</output></program></doc>"""))
        actual = get_service_output(7, input_element)
        self.assertEqual(actual, 'foot; bath')

class UtilTesting(unittest.TestCase):

    @mock.patch('builtins.print')
    def test_return_plugin(self, mock_print):
        actual = print_output(1, 2, 3, [{'name': 'foo', 'output': 'bar', 'status': 1}])

        calls = [mock.call('[WARNING]: Monit Service Status 2/3'),
                 mock.call(' \\_ [CRITICAL]: foo'),
                 mock.call('  bar')]

        mock_print.assert_has_calls(calls)

class MainTesting(unittest.TestCase):

    @mock.patch('builtins.print')
    @mock.patch('requests.get')
    def test_main_request_error(self, mock_get, mock_print):
        args = commandline(['-H', 'localhost', '-P', 'password', '-U', 'user'])

        mock_get.side_effect = Exception("Boom!")

        actual = main(args)

        self.assertEqual(actual, 3)

        calls = [mock.call('[UNKNOWN]: Could not connect to Monit. error=Boom!')]

        mock_print.assert_has_calls(calls)

    @mock.patch('builtins.print')
    @mock.patch('requests.get')
    def test_main_http_error(self, mock_get, mock_print):
        args = commandline(['-H', 'localhost', '-P', 'password', '-U', 'user'])

        mock_get.return_value = MockRequest(400, '')

        actual = main(args)

        self.assertEqual(actual, 3)

        calls = [mock.call('[UNKNOWN]: No valid response from Monit HTTP Server. error=400')]

        mock_print.assert_has_calls(calls)

    @mock.patch('builtins.print')
    @mock.patch('requests.get')
    def test_main_xml_error(self, mock_get, mock_print):
        args = commandline(['-H', 'localhost', '-P', 'password', '-U', 'user'])

        mock_get.return_value = MockRequest(200, 'not XML')

        actual = main(args)

        self.assertEqual(actual, 3)

        calls = [mock.call('[UNKNOWN]: Unable to parse XML response from Monit HTTP Server. error=syntax error: line 1, column 0')]

        mock_print.assert_has_calls(calls)

    @mock.patch('builtins.print')
    @mock.patch('requests.get')
    def test_main_ok(self, mock_get, mock_print):
        args = commandline(['-H', 'localhost', '-P', 'password', '-U', 'user'])

        d = """<?xml version="1.0" encoding="ISO-8859-1"?><monit><server><id>e4a88a4293441301bf72d6ee07dd4af2</id><incarnation>1692607015</incarnation><version>5.33.0</version><uptime>304</uptime><poll>5</poll><startdelay>0</startdelay><localhostname>scratch</localhostname><controlfile>/root/.monitrc</controlfile><httpd><address>::1</address><port>8080</port><ssl>0</ssl></httpd></server><platform><name>Linux</name><release>5.10</release><version>#1 SMP Debian</version><machine>x86_64</machine><cpu>2</cpu><memory>2030520</memory><swap>0</swap></platform><service type="5"><name>scratch</name><collected_sec>1692607316</collected_sec><collected_usec>642649</collected_usec><status>0</status><status_hint>0</status_hint><monitor>1</monitor><monitormode>0</monitormode><onreboot>0</onreboot><pendingaction>0</pendingaction><filedescriptors><allocated>672</allocated><unused>0</unused><maximum>9223372036854775807</maximum></filedescriptors><system><load><avg01>0.00</avg01><avg05>0.00</avg05><avg15>0.00</avg15></load><cpu><user>0.1</user><system>0.1</system><nice>0.0</nice><wait>0.0</wait><hardirq>0.0</hardirq><softirq>0.4</softirq><steal>0.0</steal><guest>0.0</guest><guestnice>0.0</guestnice></cpu><memory><percent>10.6</percent><kilobyte>214704</kilobyte></memory><swap><percent>0.0</percent><kilobyte>0</kilobyte></swap></system></service></monit>"""

        mock_get.return_value = MockRequest(200, d)

        actual = main(args)

        self.assertEqual(actual, 0)

        calls = [mock.call('[OK]: Monit Service Status 1/1'),
                 mock.call(' \\_ [OK]: scratch'),
                 mock.call('  load=0.0,0.0,0.0;user=0.1%;system=0.1%;nice=0.0%;hardirq=0.0%;memory=10.6%')]

        mock_print.assert_has_calls(calls)

    @mock.patch('builtins.print')
    @mock.patch('requests.get')
    def test_main_critical(self, mock_get, mock_print):
        args = commandline(['-H', 'localhost', '-P', 'password', '-U', 'user'])

        d = """<?xml version="1.0" encoding="ISO-8859-1"?><monit><server><id>e4a88a4293441301bf72d6ee07dd4af2</id><incarnation>1692607015</incarnation><version>5.33.0</version><uptime>304</uptime><poll>5</poll><startdelay>0</startdelay><localhostname>scratch</localhostname><controlfile>/root/.monitrc</controlfile><httpd><address>::1</address><port>8080</port><ssl>0</ssl></httpd></server><platform><name>Linux</name><release>5.10</release><version>#1 SMP Debian</version><machine>x86_64</machine><cpu>2</cpu><memory>2030520</memory><swap>0</swap></platform><service type="5"><name>scratch</name><collected_sec>1692607316</collected_sec><collected_usec>642649</collected_usec><status>1</status><status_hint>0</status_hint><monitor>1</monitor><monitormode>0</monitormode><onreboot>0</onreboot><pendingaction>0</pendingaction><filedescriptors><allocated>672</allocated><unused>0</unused><maximum>9223372036854775807</maximum></filedescriptors><system><load><avg01>0.00</avg01><avg05>0.00</avg05><avg15>0.00</avg15></load><cpu><user>0.1</user><system>0.1</system><nice>0.0</nice><wait>0.0</wait><hardirq>0.0</hardirq><softirq>0.4</softirq><steal>0.0</steal><guest>0.0</guest><guestnice>0.0</guestnice></cpu><memory><percent>10.6</percent><kilobyte>214704</kilobyte></memory><swap><percent>0.0</percent><kilobyte>0</kilobyte></swap></system></service></monit>"""

        mock_get.return_value = MockRequest(200, d)

        actual = main(args)

        self.assertEqual(actual, 2)

        calls = [mock.call('[CRITICAL]: Monit Service Status 0/1'),
                 mock.call(' \\_ [CRITICAL]: scratch'),
                 mock.call('  load=0.0,0.0,0.0;user=0.1%;system=0.1%;nice=0.0%;hardirq=0.0%;memory=10.6%')]

        mock_print.assert_has_calls(calls)
