from datetime import timedelta

from django.test import SimpleTestCase
from django.utils import timezone

from .models import Task
from .services import check_transition, effective_status


def make_task(status: str, days_from_today: int) -> Task:
    return Task(
        id=1,
        title="Sample",
        status=status,
        due_date=timezone.localdate() + timedelta(days=days_from_today),
    )


class OverdueRulesTests(SimpleTestCase):
    def test_past_due_and_not_done_is_overdue(self):
        self.assertEqual(effective_status(make_task("TODO", -1)), "OVERDUE")
        self.assertEqual(effective_status(make_task("IN_PROGRESS", -5)), "OVERDUE")

    def test_done_task_is_never_overdue(self):
        self.assertEqual(effective_status(make_task("DONE", -30)), "DONE")

    def test_task_due_today_is_not_overdue(self):
        self.assertEqual(effective_status(make_task("TODO", 0)), "TODO")

    def test_overdue_cannot_move_back_to_in_progress(self):
        for role in ("user", "admin"):
            allowed, _ = check_transition(
                make_task("IN_PROGRESS", -2), "IN_PROGRESS", role
            )
            self.assertFalse(allowed, role)

    def test_user_cannot_close_overdue_task(self):
        allowed, reason = check_transition(make_task("OVERDUE", -2), "DONE", "user")
        self.assertFalse(allowed)
        self.assertIn("admin", reason.lower())

    def test_admin_can_close_overdue_task(self):
        allowed, _ = check_transition(make_task("OVERDUE", -2), "DONE", "admin")
        self.assertTrue(allowed)

    def test_normal_task_transitions_are_allowed(self):
        allowed, _ = check_transition(make_task("TODO", 5), "IN_PROGRESS", "user")
        self.assertTrue(allowed)

    def test_invalid_status_is_rejected(self):
        allowed, _ = check_transition(make_task("TODO", 5), "OVERDUE", "admin")
        self.assertFalse(allowed)
