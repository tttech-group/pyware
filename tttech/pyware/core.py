import logging
import requests
from requests_kerberos import HTTPKerberosAuth, DISABLED
import socket
from pkg_resources import get_distribution, parse_version
from urllib.parse import urlparse
import warnings
import functools
import json
import re

class RestHandler():
    """ Initiate the requests client that supports basic and Kerberos authentication
    """

    def __init__(
            self,
            base_url,
            user='',
            password='',
            default_request_headers={},
    ):
        self.logger = logging.getLogger(__name__)
        self.base_url = base_url.strip('/')
        if not re.match(r"https?://", self.base_url):
            self.base_url='https://' + self.base_url.strip('/')
        # create a request session with proper authentication
        if user and password:
            self.logger.info(type(self).__name__ + ' authenticates via username and password for: %s' % user)
            self.auth = user, password
        else:
            self.logger.info(type(self).__name__ + ' authenticates via Kerberos')
            if parse_version(get_distribution('requests_kerberos').version) < parse_version('0.9.0'):
                hostname_override = None
            else:
                hostname_override = self._get_hostname(base_url)
            self.auth = HTTPKerberosAuth(
                mutual_authentication=DISABLED,
                sanitize_mutual_error_response=False,
                force_preemptive=True,
                hostname_override=hostname_override,
            )
           
        # HTTP specific settings
        if isinstance(default_request_headers, dict):
            self._default_request_headers = default_request_headers
        else:
            raise TypeError('default_request_headers must be a dict')
        self._requests_session = requests.Session()
        self._requests_session.auth = self.auth        
        self.stats = {'requests': 0, 'requests_ok': 0, 'requests_failed': 0}

    def _get_hostname(self, url):
        hostname = urlparse(url).hostname if url.startswith("http://") or url.startswith("https://") else url
        try:
            ai = socket.getaddrinfo(hostname, None, 0, 0, 0, socket.AI_CANONNAME)
        except socket.gaierror as e:
            self.logger.error('Local hostname "%s" does not resolve: %s.' % (hostname, e[1]))
        (family, socktype, proto, canonname, sockaddr) = ai[0]
        try:
            name = socket.getnameinfo(sockaddr, socket.NI_NAMEREQD)
        except socket.gaierror:
            return canonname.lower()
        return name[0].lower()
    

    def requester(self, headers=None):
        """ Support custom header for the REST request """
        self._requests_session.headers = self._default_request_headers
        if headers:
            if not isinstance(headers, dict):
                raise TypeError('Request header must be a dict')
            self._requests_session.headers.update(headers)
            # after update, remove all the empty header value
            self._requests_session.headers = {k: v for k, v in self._requests_session.headers.items() if v is not None}
        self.logger.debug("Header will be used: %s " % self._requests_session.headers)
        return self._requests_session


    def do_request(self, url, mtype="GET", headers=None, data_dict=None, cookies=None, files=None, timeout=None):
        """ Send request to the API """
        myurl = "/".join(x.strip('/') for x in [self.base_url, url]).lstrip("/")
        self.stats['requests'] += 1

        self.logger.info("\nDoing request  : %s %s", mtype, myurl)

        # convert data into JSON if it is a dictionary, otherwise binary.
        # Note: header can be incorrect. User must set the header manually
        if data_dict and isinstance(data_dict, dict):
            post_data = json.dumps(data_dict)
        else:
            post_data = data_dict

        # send request
        requester = self.requester(headers)
        if mtype == 'GET':
            response = requester.get(myurl, cookies=cookies, timeout=timeout)
        elif mtype == 'POST':
            response = requester.post(myurl, data=post_data, cookies=cookies, files=files, timeout=timeout)
        elif mtype == 'PUT':
            response = requester.put(myurl, data=post_data, cookies=cookies, files=files, timeout=timeout)
        elif mtype == 'DELETE':
            response = requester.delete(myurl, cookies=cookies, timeout=timeout)
        else:
            raise Exception("Method %s is not supported yet." % mtype)
        self.logger.info('HTTP Code: %d', response.status_code)
        # log error message in case of failed
        if not response.ok:
            self.logger.error(response.text)
            self.stats['requests_failed'] += 1
        else:
            self.stats['requests_ok'] += 1
        # return data for the callee
        return response


