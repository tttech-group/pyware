# PyWaRe - Python WADL-based Client for RESTful API

## Introduction

Pyware can transform the [WADL](https://en.wikipedia.org/wiki/Web_Application_Description_Language) file into a list of Pythonic callable methods. Pyware allows you to call [REST API](https://en.wikipedia.org/wiki/Representational_state_transfer) with the Python syntax without worrying about the complexity of the HTTP layer.

Pyware is built on top of [requests](http://docs.python-requests.org), requests is depending on [urllib3](https://urllib3.readthedocs.io/)

## Features

*Pyware, a Python WADL API Helper* is ready for contemporary web applications

 - Provide a pure Python object to interact with remote REST API by parsing WADL files.
 - Map REST API parameters (path, query, payload) into Python parameters `*args` and `**kwargs`.
 - Include an intuitive command line, helper, and web-based documentation.
 - Extendable and managementable API description by adding more WADL files.

Benefit for developers: Pyware might increase the coding speed slightly (or not), but will significantly improve the code simplicity and reduce maintenance efforts.

## How to use

Here is a sample example to use Pyware to connect to [JIRA Server 7.6.9](https://docs.atlassian.com/software/jira/docs/api/REST/7.6.9/).
The WADL file for it [can be download here](https://docs.atlassian.com/software/jira/docs/api/REST/7.6.9/jira-rest-plugin.wadl).

```python
from tttech.pyware.client_builder import ClientBuilder
from tttech.pyware.core import RestHandler

jira = ClientBuilder(
    wadl_file='jira-rest-plugin-7.6.9.wadl',
    api_prefix='api/2',
    rest_handler=RestHandler(base_url = "https://your.jira.server.url/rest")
)
projects = jira.project.get_all()
print(projects[0].key)

project = jira.project.get('YOUR_PROJECT_ID')
print(project.key)
```

## API Documentation helper

The utility `docs_handler.py` supports read the WADL file content and show the API to console or web representation.

Usage example:

```sh
> python docs_handler.py --help
usage: docs_handler.py [-h] [-u USER] [-p PASSWORD] [-f WADL_LOCATION]
                       {interact,list,find,tree,help,web} ...

Convert WADL of REST API to Python functions

positional arguments:
  {interact,list,find,tree,help,web}
                        Command to execute
  others                Parameters for command

optional arguments:
  -h, --help            show this help message and exit
  -u USER               Username for API - Keep empty to use Kerberos
  -p PASSWORD           Password for API - Keep empty to use Kerberos
  -f WADL_LOCATION      WADL file or URL of the service

> python docs_handler.py -f ..\..\tests\jira-rest-plugin-7.6.9.wadl list
> python docs_handler.py -f ..\..\tests\jira-rest-plugin-7.6.9.wadl web
```

The interact command enable you to interact directly with the REST API from the commandline.


