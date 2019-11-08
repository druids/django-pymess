from pymess.backend.emails import EmailBackend
from pymess.models import EmailMessage


class DummyEmailBackend(EmailBackend):
    """
    Dummy e-mail backend used for testing environments. Backend only logs messages to the database.
    """

    def publish_message(self, message):
        self.update_message(message, state=EmailMessage.STATE.DEBUG)

    def pull_message_info(self, message):
        message.change_and_save(
            extra_sender_data={**message.extra_sender_data, 'info': {'debug': True}},
            require_pull_info=False
        )
