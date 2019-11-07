#!/usr/bin/env python3
""" PyWaRe - Python WADL for RESTful API

    pyware.py: Command-line for pyware
"""

import sys
import os
import argparse
import logging.handlers
import datetime
from textwrap import wrap
from tttech.pyware.client_builder import ClientBuilder
import webbrowser
import http.server as BaseHTTPServer


class MethodInfoExtractor():
    """ Abstract class for different kind of WADL to extract method information 
        At the moment, only the method get_response is need to be abstracted
    """

    def __init__(self, tmethod):
        self.method = tmethod

    def get_signature(self):
        return 'def %s(%s)' % (
            self.method.__name__,
            ', '.join([p.get_name() for p in self.method._path_params] + [p.get_name() + '=None' for p in self.method._query_params]),
        )

    def get_rest_url(self):
        return '%s %s' % (self.method.__name__, self.method._path_full)

    def get_mandatory(self):
        return {
            param.get_name(): Helper.get_doc_str(param.get_doc())
            for param in self.method._path_params
        }

    def get_optional(self):
        return {
            param.get_name(): Helper.get_doc_str(param.get_doc())
            for param in self.method._query_params
        }

    def get_response(self):
        responses_dict = {}  # map: response code and description
        for response in (self.method.__wadl__.get_response() or []):
            for representation in response.get_representation():
                if response.get_status() not in responses_dict:
                    responses_dict[response.get_status()] = Helper.get_doc_str(representation.get_doc()).strip()
        return responses_dict


class CommandLineHelp():
    """ Format the help message of with print """

    def __init__(self, method_info_extractor_cls):
        self.extractor_cls = method_info_extractor_cls

    def print_help(self, method):
        extractor = self.extractor_cls(method)
        print(extractor.get_signature())
        print('\n   '.join(['    '] + wrap(Helper.get_doc_str(extractor.method.__wadl__.get_doc()))))
        self._print_mandatory(extractor)
        self._print_optional(extractor)
        self._print_response(extractor)
        self._print_rest_url(extractor)

    def _print_mandatory(self, extractor):
        params = extractor.get_mandatory()
        print('\nMandatory arguments:')
        if params:
            for name, description in params.items():
                print('    %s\t %s' % (name, description))
        else:
            print('    None')

    def _print_optional(self, extractor):
        print('\nOptional arguments:')
        params = extractor.get_optional()
        if params:
            for name, description in params.items():
                print('    %s\t %s' % (name, description))
        else:
            print('    None')

    def _print_response(self, extractor):
        responses_dict = extractor.get_response()
        print('\nResponses:')
        if responses_dict:
            for response_code, description in responses_dict.items():
                print('   %s\t %s' % (response_code, description))
        else:
            print('This method has no return')

    def _print_rest_url(self, extractor):
        print('\nOriginal REST endpoint:')
        print('    %s %s' % (extractor.method.__wadl__.get_name(), extractor.method._resource_path))


class HtmlHelp():
    """ Format the help message of ONE METHOD with HTML """

    def __init__(self, method_info_extractor_cls):
        self.extractor_cls = method_info_extractor_cls

    def print_html(self, method):
        extractor = self.extractor_cls(method)
        md = []
        md.append('<hr /><span id="%s"><h3> %s </h3></span> ' % (method.__name__, extractor.get_signature()))
        md.append('\n   '.join(['    '] + self._print_main_doc(extractor)))
        md += self._print_mandatory(extractor) + self._print_optional(extractor) + self._print_response(extractor)
        md.append('<h4>Original REST: </h4> %s %s' % (extractor.method._resttype, extractor.method._resource_path))
        return md

    def _print_main_doc(self, extractor):
        return [Helper.get_doc_str(extractor.method.__doc__)]

    def _print_arguments(self, extractor, method_type):
        params = getattr(extractor, "get_" + method_type)()
        md = []
        md.append('\n<h4> %s arguments:</h4>\n' % method_type.title())
        if params:
            md.append('<table><tr><th> Argument </th><th> Description </th></tr>')
            for param_name, description in params.items():
                md.append('<tr><td> %s </td><td> %s </td></tr>' % (param_name, description))
            md.append('</table>')
        else:
            md.append('This method has no mandatory argument')
        return md

    def _print_mandatory(self, extractor):
        return self._print_arguments(extractor, "mandatory")

    def _print_optional(self, extractor):
        return self._print_arguments(extractor, "optional")

    def _print_response(self, extractor):
        md = []
        md.append('\n<br/><h4> Responses:</h4>\n')
        md.append('<table><tr><th> Return code </th><th> Description </th></tr>')
        for status, description in extractor.get_response().items():
            md.append('<tr><td> %s </td><td> %s </td></tr>' % (status, description))
        md.append('</table>')
        return md


class Helper():
    @staticmethod
    def get_doc_str(wadl_docs_obj):
        docs = []
        for doc in wadl_docs_obj:
            docs.append(' '.join(doc.get_valueOf_().split()))
        return '\n'.join(docs)

    @staticmethod
    def load_in_default_browser(html):
        """Display html in the default web browser without creating a temp file.

        Instantiates a trivial http server and calls webbrowser.open with a URL
        to retrieve html from that server.
        """

        class RequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                bufferSize = 1024 * 1024
                for i in range(0, len(html), bufferSize):
                    self.wfile.write(html[i:i + bufferSize])

        server = BaseHTTPServer.HTTPServer(('127.0.0.1', 0), RequestHandler)
        webbrowser.open('http://127.0.0.1:%s' % server.server_port, new=2)
        server.handle_request()


def cmd_parsing(extractor_cls=MethodInfoExtractor, wadl=None, service_name='Service', default_based_url='http://www.example.com'):
    parser = argparse.ArgumentParser(description="Convert WADL of REST API to Python functions")
    parser.add_argument('-u', metavar='USER', action='store', type=str, help='Username for API - Keep empty to use Kerberos')
    parser.add_argument('-p', metavar='PASSWORD', action='store', type=str, help='Password for API - Keep empty to use Kerberos')
    parser.add_argument('-f', metavar='WADL_LOCATION', help="WADL file or URL of the service", action='store')

    parser.add_argument("command", help="Command to execute", action='store', choices=['interact', 'list', 'find', 'tree', 'help', 'web'])
    parser.add_argument('others', help="Parameters for command", nargs=argparse.REMAINDER)

    args = parser.parse_args()

    # Load the WADL at first if the object (wadl argument) is not provided.
    if wadl is None:
        if not args.f:
            raise Exception('At least WADL object or a WADL file must be provided')
        logging.basicConfig(level=logging.ERROR, format='%(message)s')
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)
        wadl = ClientBuilder(wadl_file=args.f)

    method_list = wadl._func.__dict__.values()

    # Commandline mode
    if args.command == 'list':
        for method in method_list:
            print("%s" % method.__name__)

    elif args.command == 'find' and  args.others:
        for method in method_list:
            if args.others[0].lower() in method.__name__.lower():
                print("%s" % method.__name__)

    elif args.command == 'tree':
        wadl.print_tree()
    elif args.command == 'help':
        if not args.others:
            print('Please give a method name you want to check')
        else:
            CommandLineHelp(extractor_cls).print_help(getattr(wadl._func, args.others[0]))
            #cmd_adaptor_cls().print_help(wadl._methods_by_name[args.others[0]])

    elif args.command == 'web':
        with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'html/helppage.template.html'), 'r') as template_f:
            html = template_f.read()
            html = html.replace('PYWARE_SERVICE_NAME', service_name)
            table_of_content = ['\n<h2> Table of content </h2>']

            main_html = ['<h2>%s Python API</h2>' % service_name]
            main_html.append('<table><tr><td>Generated at</td> <td> %s </td></tr>' % datetime.datetime.now().strftime("%Y-%m-%d %H:%M"))
            main_html.append('<tr><td>Base URL (example) </td> <td> %s </td></tr>' % default_based_url)
            main_html.append('</table>')

            table_of_content.append('<ul>')
            html_printer = HtmlHelp(extractor_cls)
            for method in method_list:
                main_html += html_printer.print_html(method)
                table_of_content.append('<li><a href="#%s">%s</a></li>' % (method.__name__, method.__name__))
            table_of_content.append('</ul>')
            html = html.replace('PYWARE_MAIN_HTML_CONTENT', '\n'.join(main_html)).replace('PYWARE_TABLE_OF_CONTENT', '\n'.join(table_of_content))
            Helper.load_in_default_browser(html.encode('utf-8'))

    # Interactive mode
    if args.command == 'interact':
        import rlcompleter  # for auto-complete
        import readline
        import code
        readline.parse_and_bind('tab: complete')
        sys.ps1 = "W) "
        sys.ps2 = ". "
        vars = globals().copy()
        vars.update(locals())
        shell = code.InteractiveConsole(vars)
        shell.interact(banner="\n\n-----------------------------\n\nWelcome to PyWaRe - Python WADL for RESTful API!.\n'wadl' object has been created.\n")
        sys.exit(0)


# end class main

if __name__ == "__main__":
    cmd_parsing()
