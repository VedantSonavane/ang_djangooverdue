import hmac
import json
from functools import wraps

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from . import services
from .models import Task


def ok(data=None, message="OK", status=200):
    return JsonResponse(
        {"success": True, "message": message, "data": data}, status=status
    )


def err(message, status=400, errors=None):
    return JsonResponse(
        {"success": False, "message": message, "errors": errors}, status=status
    )


def service_key_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        sent = request.headers.get("X-Service-Key", "")
        if not settings.SERVICE_KEY or not hmac.compare_digest(
            sent, settings.SERVICE_KEY
        ):
            return err("Forbidden", 403)
        return view(request, *args, **kwargs)

    return wrapper


@require_GET
def health(request):
    return ok({"service": "overdue"}, "healthy")


@csrf_exempt
@require_POST
@service_key_required
def sync(request):
    ids = services.sync_overdue()
    return ok({"updated": len(ids), "task_ids": ids}, "Overdue sync complete")


@csrf_exempt
@require_POST
@service_key_required
def validate_transition(request):
    try:
        body = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return err("Invalid JSON", 400)

    task_id = body.get("task_id")
    new_status = body.get("new_status")
    role = body.get("role")

    if not task_id or not new_status or role not in ("admin", "user"):
        return err("task_id, new_status and role (admin|user) are required", 422)

    try:
        task = Task.objects.get(pk=task_id)
    except Task.DoesNotExist:
        return err("Task not found", 404)

    allowed, reason = services.check_transition(task, new_status, role)
    return ok(
        {
            "allowed": allowed,
            "reason": reason,
            "stored_status": task.status,
            "current_status": services.effective_status(task),
        }
    )
