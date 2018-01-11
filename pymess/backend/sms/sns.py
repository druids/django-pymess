import boto3

from django.conf import settings
from django.utils import timezone
from django.utils.encoding import force_text

from chamber.shortcuts import change_and_save

from pymess.config import settings
from pymess.backend.sms import SMSBackend
from pymess.models import AbstractOutputSMSMessage


class SNSSMSBackend(SMSBackend):
    """
    SMS backend implementing AWS SNS service via boto3 library https://aws.amazon.com/sns/
    """

    name = 'sns'
    sns_client = None

    def _get_sns_client(self):
        """
        Connect to the SNS service
        """
        if not self.sns_client:
            boto3.client(
                service_name='sns',
                aws_access_key_id=settings.SNS.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.SNS.AWS_SECRET_ACCESS_KEY,
                region_name=settings.SNS.AWS_SMS_REGION,
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
            'PhoneNumber': force_text(message.recipient),
            'Message': message.content,
        }
        if settings.SNS.SENDER_ID:
            publish_kwargs.update({
                'MessageAttributes': {
                    'AWS.SNS.SMS.SenderID': {
                        'DataType': 'String',
                        'StringValue': settings.SNS.SENDER_ID,
                    }
                }
            })
        try:
            sns_client.publish(**publish_kwargs)
            change_and_save(message, state=AbstractOutputSMSMessage.STATE.SENT, sent_at=timezone.now())
        except Exception as ex:
            change_and_save(message, state=AbstractOutputSMSMessage.STATE.ERROR, error=force_text(ex))
