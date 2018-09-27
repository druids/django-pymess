def generate_session(slug=None, related_objects=None):
    try:
        from security.transport.security_requests import SecuritySession

        return SecuritySession(slug=slug, related_objects=related_objects)
    except ImportError:
        from requests import Session

        return Session()
