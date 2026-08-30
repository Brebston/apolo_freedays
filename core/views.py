from django.http import HttpResponseNotFound
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

ACTION_LABEL_PL = {
    "approve": "Zaakceptuj zgłoszenie",
    "reject": "Odrzuć zgłoszenie",
}


@csrf_exempt
def decide_service_request(request, token, action):
    from core.models import RequestStatus, ServiceRequest
    from core.tasks import notify_service_request_decision

    action_status_map = {
        "approve": RequestStatus.APPROVED,
        "reject": RequestStatus.REJECTED,
    }
    if action not in action_status_map:
        return HttpResponseNotFound()

    service_request = get_object_or_404(ServiceRequest, decision_token=token)
    already_decided = service_request.status != RequestStatus.PENDING
    just_decided = False

    if request.method == "POST" and not already_decided:
        service_request.status = action_status_map[action]
        service_request.decided_at = timezone.now()
        service_request.save(update_fields=["status", "decided_at"])
        notify_service_request_decision.delay(service_request.id)
        already_decided = True
        just_decided = True

    return render(
        request,
        "core/service_request_decision.html",
        {
            "service_request": service_request,
            "action_label": ACTION_LABEL_PL.get(action, ""),
            "already_decided": already_decided,
            "just_decided": just_decided,
        },
    )
