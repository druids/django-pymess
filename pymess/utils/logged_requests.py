"""
If the django-security library is present in the system, we want to log HTTP requests
using its modified get(), post() etc. functions instead of standard the requests library.
"""

try:
    from security.transport.security_requests import *
except ImportError:
    from requests import *
    from requests import (get as _get, options as _options, head as _head, post as _post, put as _put, patch as _patch,
                          delete as _delete)

    def get(url, slug=None, related_objects=None, **kwargs):
        return _get(url, **kwargs)

    def options(url, slug=None, related_objects=None, **kwargs):
        return _options(url, **kwargs)

    def head(url, slug=None, related_objects=None, **kwargs):
        return _head(url, **kwargs)

    def post(url, slug=None, related_objects=None, **kwargs):
        return _post(url, **kwargs)

    def put(url, slug=None, related_objects=None, **kwargs):
        return _put(url, **kwargs)

    def patch(url, slug=None, related_objects=None, **kwargs):
        return _patch(url, **kwargs)

    def delete(url, slug=None, related_objects=None, **kwargs):
        return _delete(url, **kwargs)
