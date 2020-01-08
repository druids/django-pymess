import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View
from django.utils.decorators import method_decorator
from django.utils.timezone import now

from is_core.auth.permissions import AllowAny

from pymess.models import EmailMessage


logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class MandrillWebhookView(View):

    permission = AllowAny()

    def head(self, *args, **kwargs):
        return HttpResponse()

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.POST.get('mandrill_events'))
        except TypeError:
            return HttpResponse(status=400)

        for event in data:
            try:
                self.process_event(event)
            except Exception as ex:  # pylint: disable=W0703
                logger.exception(ex)

        return HttpResponse()

    def process_event(self, event_dict):
        message_id = event_dict.get('_id', None)
        if message_id:
            message = EmailMessage.objects.filter(external_id=message_id).first()
            if message:
                message.change_and_save(last_webhook_received_at=now())
