from django.urls import path

from overdue import views

urlpatterns = [
    path("health", views.health),
    path("api/overdue/sync", views.sync),
    path("api/tasks/validate-transition", views.validate_transition),
]
