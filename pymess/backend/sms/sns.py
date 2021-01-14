import boto3
from attrdict import AttrDict

from django.conf import settings
from django.utils import timezone

from pymess.config import settings
from pymess.backend.sms import SMSBackend
from pymess.models import OutputSMSMessage


class SNSSMSBackend(SMSBackend):
    """
    SMS backend implementing AWS SNS service via boto3 library https://aws.amazon.com/sns/
    """

    sns_client = None
    config = AttrDict({
        'AWS_ACCESS_KEY_ID': None,
        'AWS_SECRET_ACCESS_KEY': None,
        'AWS_REGION': None,
        'SENDER_ID': None,
    })

    def _get_sns_client(self):
        """
        Connect to the SNS service
        """
        if not self.sns_client:
            self.sns_client = boto3.client(
                service_name='sns',
                aws_access_key_id=self.config.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.config.AWS_SECRET_ACCESS_KEY,
                region_name=self.config.AWS_REGION,
                use_ssl=True
            )
        return self.sns_client

    def publish_message(self, message):
        """
        Method uses boto3 client via witch SMS message is send
        :param message: SMS message
        """
        sns_client = self._get_sns_client()
        publish_kwargs = {
            'PhoneNumber': str(message.recipient),
            'Message': message.content,
        }
        if self.config.SENDER_ID:
            publish_kwargs.update({
                'MessageAttributes': {
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': self.config.SENDER_ID,
                    }
                }
            })
        try:
            sns_client.publish(**publish_kwargs)
            self._update_message_after_sending(message, state=OutputSMSMessage.STATE.SENT, sent_at=timezone.now())
        except Exception as ex:
            self._update_message_after_sending_error(
                message, error=str(ex)
            )
            # Do not re-raise caught exception. We do not know exact exception to catch so we catch them all
            # and log them into database. Re-raise exception causes transaction rollback (lost of information about
            # exception).
