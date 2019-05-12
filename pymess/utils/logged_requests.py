class DefaultTimeoutSessionMixin:

    def __init__(self, timeout=None, **kwargs):
        super().__init__(**kwargs)
        self.timeout = timeout

    def request(self, method, url, **kwargs):
        timeout = kwargs.pop('timeout', self.timeout)
        return super().request(method, url, timeout=timeout, **kwargs)


try:
    from security.transport.security_requests import SecuritySession

    class DefaultTimeoutSecuritySession(DefaultTimeoutSessionMixin, SecuritySession):
        pass

except ImportError:
    from requests import Session

    class DefaultTimeoutSecuritySession(DefaultTimeoutSessionMixin, Session):

        def __init__(self, timeout, slug, related_objects):
            super().__init__(timeout)


def generate_session(slug=None, related_objects=None, timeout=None):
    return DefaultTimeoutSecuritySession(timeout=timeout, slug=slug, related_objects=related_objects)
