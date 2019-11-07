import unittest
import pprint
from tttech.pyware.wadl_parser import WadlParser
from tttech.pyware.core import RestHandler
import json
import logging.handlers
import sys


class TestWaldParser(unittest.TestCase):
    def setUp(self):
        logging.basicConfig(level=logging.ERROR, format='%(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        self.WADL_FILE = 'jira-rest-plugin-7.6.9.wadl'
        self.wadl = WadlParser(
            wadl_file=self.WADL_FILE
        )

    def test_if_number_of_resource_is_correct(self):
        with open(self.WADL_FILE, 'r') as f:
            data = f.read()
            resource_num = data.count('<ns2:resource') - data.count('<ns2:resources')
            self.wadl.logger.info('Test resource number:\n Resources by reading text: %d\n Resources loaded: %d' % (resource_num, len(self.wadl._resources)))
            self.assertEqual(len(self.wadl._resources), resource_num)


    def test_number_of_methods(self):
        """ Is there any missing method ? """
        # count all the method in the wadl
        method_count = sum(len(resource._methods) for resource in self.wadl._resources)

        with open(self.WADL_FILE, 'r') as f:
            data = f.read()
            methods_read = data.count('<ns2:method')
            self.wadl.logger.info('Test method number:\n Method num in WADL: %d\n Method count: %d' % (methods_read, method_count))
            self.assertEqual(method_count, methods_read)


if __name__ == '__main__':
    unittest.main()
