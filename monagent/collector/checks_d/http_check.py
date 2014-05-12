import socket
import time
import json
import re

from httplib2 import Http, HttpLib2Error

from monagent.collector.checks import AgentCheck


class HTTPCheck(AgentCheck):

    @staticmethod
    def _load_conf(instance):
        # Fetches the conf
        dimensions = instance.get('dimensions', {})
        username = instance.get('username', None)
        password = instance.get('password', None)
        timeout = int(instance.get('timeout', 10))
        headers = instance.get('headers', {})
        url = instance.get('url', None)
        response_time = instance.get('collect_response_time', False)
        pattern = instance.get('match_pattern', None)
        if url is None:
            raise Exception("Bad configuration. You must specify a url")
        include_content = instance.get('include_content', False)
        ssl = instance.get('disable_ssl_validation', True)
        return url, username, password, timeout, include_content, headers, response_time, dimensions, ssl, pattern

    def check(self, instance):
        addr, username, password, timeout, include_content, headers, response_time, dimensions, disable_ssl_validation, pattern = self._load_conf(instance)
        content = ''

        new_dimensions = dimensions.copy()
        new_dimensions['url'] = addr

        start = time.time()
        try:
            self.log.debug("Connecting to %s" % addr)
            if disable_ssl_validation:
                self.warning("Skipping SSL certificate validation for %s based on configuration" % addr)
            h = Http(timeout=timeout, disable_ssl_certificate_validation=disable_ssl_validation)
            if username is not None and password is not None:
                h.add_credentials(username, password)
            resp, content = h.request(addr, "GET", headers=headers)

        except socket.timeout, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, str(e), length))
            self.gauge('mon_http_status', 1, dimensions=new_dimensions)
            return

        except HttpLib2Error, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, str(e), length))
            self.gauge('mon_http_status', 1, dimensions=new_dimensions)
            return

        except socket.error, e:
            length = int((time.time() - start) * 1000)
            self.log.info("%s is DOWN, error: %s. Connection failed after %s ms" % (addr, repr(e), length))
            self.gauge('mon_http_status', 1, dimensions=new_dimensions)
            return

        except Exception, e:
            length = int((time.time() - start) * 1000)
            self.log.error("Unhandled exception %s. Connection failed after %s ms" % (str(e), length))
            self.gauge('mon_http_status', 1, dimensions=new_dimensions)
            raise

        if response_time:
            # Stop the timer as early as possible
            running_time = time.time() - start
            self.gauge('mon_http_response_time', running_time, dimensions=new_dimensions)

        # Add a 'detail' tag if requested
        if include_content:
            new_dimensions['detail'] = json.dumps(content)

        if int(resp.status) >= 400:
            self.log.info("%s is DOWN, error code: %s" % (addr, str(resp.status)))
            self.gauge('mon_http_status', 1, dimensions=new_dimensions)

        if pattern is not None:
            if re.search(pattern, content, re.DOTALL):
                self.log.debug("Pattern match successful")
            else:
                self.log.info("Pattern match failed! '%s' not in '%s'" % (pattern, content))
                self.gauge('mon_http_status', 1, dimensions=new_dimensions)
                return

        self.log.debug("%s is UP" % addr)
        self.gauge('mon_http_status', 0, dimensions=new_dimensions)
