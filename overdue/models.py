from django.db import models


class Task(models.Model):
    """Maps to the table Laravel created. Django never changes the schema."""

    id = models.BigAutoField(primary_key=True)
    title = models.CharField(max_length=255)
    status = models.CharField(max_length=255)
    due_date = models.DateField()
    updated_at = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = "tasks"
