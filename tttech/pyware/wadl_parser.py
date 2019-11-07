#!/usr/bin/env python3
""" PyWaRe - Python WADL for RESTful API

    wadl_processor.py: The wrapper class for parsing and process WADL
"""

import os
import re
import logging
import json
import types
from . import wadl
from .core import RestHandler


class WadlParser():
    """ Load all the resources and methods from WADL files and save to `self._resources` list.
    """
    ns = {"ns": "http://wadl.dev.java.net/2009/02"}

    def __init__(
            self,
            wadl_file=None,
            rest_handler=None,
    ):
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
        self.logger = logging.getLogger(__name__)
        wadl_files = [] if not wadl_file else [wadl_file] if not isinstance(wadl_file, list) else wadl_file
        self._resources = []  # a list of resources by their REST URL
        self.method_count = 0

        for wadl_f in wadl_files:
            self.logger.info('Loading WADL: %s', wadl_f)
            self._parse_wadl(wadl_file=wadl_f)
        self.logger.info("WADL OBJECT IS CREATED!")

        self.rest_handler = rest_handler

    def _parse_wadl(self, wadl_file=None):
        """ Load all the resources """
        app = wadl.parse(wadl_file, silence=True)
        for resources in app.get_resources():
            for resource in resources.get_resource():
                self._parse_resource(resource)
        self.logger.info("ALL WADL IS DONE")

    def _parse_resource(self, resource, resource_parent=None, level=1):
        """ Load a single resource and recursive for child resource """
        self.logger.info("%s Resource: %s " % ("  " * level, resource.get_path()))
        resource_path = resource.get_path()

        # because resources are recursive, we take the parent path_param first
        if resource_parent and resource_parent._path_param:
            resource_path_param = resource_parent._path_param
        else:
            resource_path_param = []

        # then, get the current path_param. It is good if the WADL contains <param>, otherwise we take from the resource_path
        path_param_list = re.findall("{(.*?)}", resource_path)
        available_params = {}
        for par in resource.get_param():
            available_params[par.get_name()] = par
        for param_name in path_param_list:
            if param_name in available_params:
                resource_path_param.append(available_params[param_name])
            else:
                resource_path_param.append(wadl.param(name=param_name, style='template'))

        resource_cls = types.SimpleNamespace()
        resource_cls._path = resource_path
        resource_cls._path_full = http_normalize_slashes('/'.join([resource_parent._path_full, resource_path]) if resource_parent else resource_path)
        resource_cls._category = 'resource'
        resource_cls._path_param = resource_path_param
        resource_cls._children = []
        resource_cls._methods = []

        self._resources.append(resource_cls)

        # build the method. The method does not know
        for method in resource.get_method():
            method_cls = self._parse_method(method, resource_cls, level=level + 1)
            resource_cls._methods.append(method_cls)

        # child resources
        if resource.get_resource():
            for resource_child in resource.get_resource():
                resource_child_cls = self._parse_resource(resource_child, resource_parent=resource_cls, level=level + 1)
                resource_cls._children.append(resource_child_cls)
        self.logger.info("%s Resource done: %s " % ("  " * level, resource.get_path()))
        return resource_cls

    def _parse_method(self, method, resource_cls, level=1):
        """ Load methods from a single resource and add as attributes """
        self.logger.info("%s + Method: %s" % ("  " * level, method.get_id()))

        method_query_param = []
        method_path_param = resource_cls._path_param[:] if resource_cls._path_param else []
        if method.get_request():
            for param in method.get_request().get_param():
                if param.get_style() == 'template':
                    method_path_param.append(param)
                elif param.get_style() == 'query':
                    method_query_param.append(param)

        # get content type for the header
        if method.get_request() and method.get_request().get_representation():
            request_content_type = method.get_request().get_representation()[0].get_mediaType()
            request_headers = {'Content-Type': request_content_type}
        else:
            request_headers = {}

        # Build the method
        tmethod = self._method_creator(
            resource_cls._path_full,  # REST URL to invoke
            method.get_name(),  # method_type: GET/POST/PUT/DELETE
            tuple(p.get_name() for p in method_path_param),  # parameters in {} in URL
            tuple(p.get_name() for p in method_query_param),
            headers=request_headers,
        )  # parameters after ? in URL
        tmethod.__name__ = method.get_id()
        tmethod.__doc__ = method.get_doc()
        tmethod._category = "method"
        tmethod._resttype = method.get_name().lower()
        tmethod._resource_path = resource_cls._path_full
        tmethod._path_params = [p for p in method_path_param if p]
        tmethod._query_params = [p for p in method_query_param if p]
        tmethod.__wadl__ = method

        self.method_count += 1
        return tmethod

    def _method_creator(self, url, mtype, tparams, qparams, headers=None, timeout=None):
        """ Create method, actually to return a _do_request function """
        self.logger.debug("  --> Creating method: %s, %s, %s, %s", url, mtype, tparams, qparams)

        def method_template(*args, **kwds):
            """ A closure to capture REST arguments and return a REST method wrapper.
                
                The arguments can be overwritten during the method call. E.g. add custom `headers` into the call.
            """
            # data_dict is a special parameter, to store the REST payload
            data_dict = kwds.pop("data_dict", None)

            # cookies is a special parameter, to store the custom cookies
            cookies = kwds.pop("cookie", None)

            # upload a files, user can pass: files = {'upload_file': open('file.txt', 'rb')}
            files = kwds.pop("files", None)

            # return_full_response: to return the whole "requests" response object, don't manipulate the JSON
            requests_response = kwds.pop("requests_response", False)

            # custom headers to be update to the default headers
            headers.update(kwds.pop("headers", {}))

            # here we append optional parameters to the mandatory param list if param name matches
            mandatory_param_list = list(args)
            optional_param_dict = dict(kwds)
            for tparam in tparams:
                if tparam in kwds:
                    mandatory_param_list.append(kwds[tparam])
                    del optional_param_dict[tparam]

            self.logger.debug("Template params: %s", str(tparams))
            self.logger.debug("Template args  : %s", str(mandatory_param_list))
            self.logger.debug("Query params   : %s", str(qparams))
            self.logger.debug("Query args     : %s", str(optional_param_dict))
            self.logger.debug("URL            : %s", url)
            self.logger.debug("DATADICT       : %s", data_dict)
            self.logger.debug("Files          : %s", len(files) if files else 0)

            path_param_list = re.findall("{(.*?)}", url)
            # args is for path parameter, is mandatory
            if len(mandatory_param_list) < len(path_param_list):
                self.logger.error("Requires %s argument(s) for path parameters: %s", path_param_list, tparams)
                self.logger.error("Provided args: %s", str(args))
                raise ValueError('Not enough arguments')

            do_url = url

            for idx, val in enumerate(path_param_list):
                # First replace REST positional arguments in { }
                if idx < len(mandatory_param_list):
                    do_url = do_url.replace("{%s}" % val, str(mandatory_param_list[idx]))
            # then make the REST query arguments, using kwargs
            url_args = '&'.join(["%s=%s" % (k, v) for k, v in optional_param_dict.items()])

            do_url = do_url.replace("//", "/")
            if url_args:
                do_url = "%s?%s" % (do_url, url_args)

            response = self.rest_handler.do_request(do_url, mtype, headers=headers, data_dict=data_dict, cookies=cookies, files=files, timeout=None)

            self.logger.debug(response.text)

            # the option requests_response = True, the function return the whole object
            if requests_response == True:
                return response

            # otherwise, the response is processed. Exception upon failure.
            if not response.ok:
                raise Exception('Error %d: %s' % (response.status_code, response.text))

            # extract Payload if possible.
            if response and "application/json" in response.headers['Content-Type'] and response.text:
                return create_payload(json.loads(response.text))

            # if the response cannot be processed (e.g. XML, plaintext), return it the content or failed
            if response:
                return response.content
            else:
                return '<No response message>'

        return method_template


def http_normalize_slashes(url):
    return '/'.join(filter(None, url.split('/')))

def create_payload(d):
    if isinstance(d, list):
        ret = []
        for item in d:
            ret.append(create_payload(item))
        return ret
    return DictPayLoad(d)


class DictPayLoad():
    """ The class keeps JSON fields of the return """

    def __init__(self, d):
        self.__dict__ = {}
        for key, value in d.items():
            if type(value) is dict:
                value = DictPayLoad(value)
            elif type(value) is list:
                value = create_payload(value)
            self.__dict__[key] = value

    def to_dict(self):
        d = {}
        for key, value in self.__dict__.items():
            if type(value) is DictPayLoad:
                value = value.to_dict()
            d[key] = value
        return d

    def __repr__(self):
        return str(self.to_dict())

    def __setitem__(self, key, value):
        self.__dict__[key] = value

    def __getitem__(self, key):
        return self.__dict__[key]
