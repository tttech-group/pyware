import re
import logging
import types
from tttech.pyware.wadl_parser import WadlParser
from pprint import pprint
from operator import attrgetter
from collections import defaultdict, deque


class ClientBuilder():
    ''' This class custommize the output of the wald_parser.py

        Methods have 2 representations:
        - resource based. E.g. resource.resource_child.get(id) 
        - method name based. E.g. getResourceContent(id)
    '''

    def __init__(self, wadl_file, rest_handler=None, api_prefix=''):
        logging.basicConfig(level=logging.DEBUG, format='%(message)s')
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        self.logger.debug("\n\n Initiate client ----------")

        self._wadl = WadlParser(wadl_file=wadl_file, rest_handler=rest_handler)
        self._PREFIX = api_prefix
        self._func = types.SimpleNamespace()

        for resource_cls in self._wadl._resources:
            self._parse_resource(resource_cls, level=1)
        self._build_flat_naming_scheme()

    def _create_resource(self, resource_names):
        """ Add resource into the object """
        if not resource_names:
            self.logger.debug('Create resource but there is no name in list')
            return None, None
        current = self
        full_name = '.'.join(resource_names)
        for resource_name in resource_names:
            #self.logger.debug('travel to resource: %s' % resource_name)
            if not hasattr(current, resource_name):
                self.logger.debug("create new node: %s" % resource_name)
                new_rs_node = types.SimpleNamespace()
                setattr(current, resource_name, new_rs_node)
                current = new_rs_node
                full_name += '.' + resource_name
            else:
                #self.logger.debug("travel old node: %s" % resource_name)
                current = getattr(current, resource_name)
        return current, full_name

    def _create_method(self, resource, method, level=1):
        """ Add method into the object """
        if hasattr(resource, method._resttype):
            # already has a method with the same name, e.g. GET, compare number of path parameter, keep the one which has more
            existed_method = getattr(resource, method._resttype)
            if len(method._path_params) > len(existed_method._path_params):
                delattr(resource, method._resttype)
                setattr(resource, method._resttype + "_all", existed_method)
                setattr(resource, method._resttype, method)
        else:
            setattr(resource, method._resttype, method)

    def _parse_resource(self, resource_cls, level=1):
        """ Build the structure of resources and methods and assign as attributes of this object """
        self.logger.debug("%sResource: %s - type: %s" % ("  " * level, resource_cls._path_full, str(type(resource_cls))))
        if not resource_cls._path_full.startswith(self._PREFIX):
            return None
        # remove prefix
        tmp = resource_cls._path_full[len(self._PREFIX):]
        # remove path parameter
        tmp2 = re.sub(r'{.+?}', '', tmp)
        # list of component
        list_component = list(filter(None, tmp2.split('/')))
        # create or travel to the resource node
        current_rs, full_rs_name = self._create_resource(list_component)
        if not current_rs:
            return
        self.logger.debug("%s current rs: %s" % ("  " * level, full_rs_name))

        for method in resource_cls._methods:
            self._create_method(current_rs, method)

    def _build_flat_naming_scheme(self, counter=0):
        ''' Build the list of methods by name and save to `self._func`
            The names can be conflict, so this function resolves the conflict

            Example of how conflicts to be resolved:
            - (api/2/user)getUser and (api/2/myself)getUser --> getUser_user and getUser_myself
            - (api/2/user/avatar)getAvatar and (api/2/project/{projectid}/avatar)getAvatar --> getAvatar_user and getAvatar_project

            This function will be recursive several time
        '''
        counter += 1
        self.logger.debug('Resolving naming conflict round %s...', counter)

        # step1: group methods with the same name
        group_by_name = defaultdict(list)
        for resource in self._wadl._resources:
            for method in resource._methods:
                group_by_name[method.__name__].append(method)

        recheck_required = False
        # step 2: check all the methods with name conflicts
        for name, methods in group_by_name.items():
            if len(methods) > 1:  # a name belongs to more than one method
                recheck_required = True
                namedict = {method: deque(method.split('/')) for method in map(attrgetter('_resource_path'), methods)}
                while True:
                    # take the first segment in each of resource_URL
                    first_url_segments = [split_name[0] if split_name else '' for split_name in namedict.values()]
                    # if the first segments are different, we found the identification
                    if len(set(first_url_segments)) != 1:
                        break
                    # else remove the first segment and check the next segments by the while loop
                    for split_name in namedict.values():
                        split_name.popleft()
                # rename all the method as per the identifications found
                for method in methods:
                    if namedict[method._resource_path]:
                        method.__name__ = '_'.join([method.__name__, namedict[method._resource_path][0]]).replace('{', '').replace('}', '').replace('-', '_')
                    self.logger.debug('  --> {} --> {}'.format(method._resource_path, method.__name__))
        ''' however, the conflict still remain, e.g. with JIRA, after the first round, we still have 2 "delete_version"
        original name: delete
          --> api/2/component/{id}             --> delete_component
          --> api/2/version/{id}               --> delete_version
          --> api/2/version/{id}/removeAndSwap --> delete_version
            The next round will fix it
        original name: delete_version
          --> api/2/version/{id}               --> delete_version
          --> api/2/version/{id}/removeAndSwap --> delete_version_removeAndSwap
        '''
        if recheck_required:
            self._build_flat_naming_scheme(counter)
        else:
            # if there is no conflict, populate them
            for resource in self._wadl._resources:
                for method in resource._methods:
                    setattr(self._func, method.__name__, method)
            self.logger.debug('Naming conflict resolving done. Round: %s', counter)
