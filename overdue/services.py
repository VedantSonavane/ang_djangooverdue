from django.utils import timezone

from .models import Task

ALLOWED_TARGETS = {"TODO", "IN_PROGRESS", "DONE"}


def effective_status(task: Task) -> str:
    """A task past its due date that is not DONE is OVERDUE, even if sync hasn't run yet."""
    if task.status != "DONE" and task.due_date < timezone.localdate():
        return "OVERDUE"
    return task.status


def sync_overdue() -> list[int]:
    """Rule 1: due_date in the past and status not DONE -> OVERDUE."""
    today = timezone.localdate()
    ids = list(
        Task.objects.filter(due_date__lt=today)
        .exclude(status__in=["DONE", "OVERDUE"])
        .values_list("id", flat=True)
    )
    if ids:
        Task.objects.filter(id__in=ids).update(
            status="OVERDUE", updated_at=timezone.now()
        )
    return ids


def check_transition(task: Task, new_status: str, role: str) -> tuple[bool, str]:
    """Rules 2 and 3. Returns (allowed, reason)."""
    if new_status not in ALLOWED_TARGETS:
        return False, "Invalid status"

    if effective_status(task) == "OVERDUE":
        # Rule 2: overdue tasks cannot move back to IN_PROGRESS
        if new_status == "IN_PROGRESS":
            return False, "Overdue tasks cannot move back to IN_PROGRESS"
        # Rule 3: only an admin can close an overdue task
        if new_status == "DONE":
            if role != "admin":
                return False, "Only an admin can close an overdue task"
            return True, "Admin closed the overdue task"
        return False, "Overdue tasks can only be closed by an admin"

    return True, "Transition allowed"
