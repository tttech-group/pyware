import unittest
import pprint
from tttech.pyware.client_builder import ClientBuilder
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
        self.client = ClientBuilder(
            wadl_file=self.WADL_FILE,
            api_prefix='api/2',
            rest_handler=RestHandler(base_url = "https://www.example.com/rest")
        )

    def test_basic_info_loading(self):
        """ select a random stuff to check """
        self.assertEqual(self.client.project.get_all._resource_path, 'api/2/project')
        self.assertEqual(self.client.project.avatar.post._resource_path, 'api/2/project/{projectIdOrKey}/avatar')
        self.assertEqual(self.client.issue.get._resource_path, 'api/2/issue/{issueIdOrKey}')
        self.assertEqual(self.client.issue.worklog.get._resource_path, 'api/2/issue/{issueIdOrKey}/worklog/{id}')
        self.assertEqual([param.name for param in self.client.projectCategory.get._path_params], ['id'])

    def test_list_of_methods(self):
        """ test the client._func """
        for method in self.client._func.__dict__:
            print(method)
        with open('sample_data/flat-naming.txt', 'r') as f:
            lines = filter(None, (line.strip() for line in f))
            for func_name in lines:
                self.logger.info('Checking function name: %s' % func_name)
                self.assertTrue(hasattr(self.client._func, func_name))
                    

if __name__ == '__main__':
    unittest.main()