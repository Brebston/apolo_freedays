from django.urls import path

from api import views

urlpatterns = [
    path("me/", views.me),
    path("me/language/", views.set_language),
    path("regions/", views.regions),
    path("coordinators/", views.coordinators),
    path("projects/<int:project_id>/calendar/", views.project_calendar),
    path("absence-requests/", views.create_absence_request),
    path(
        "absence-requests/<int:request_id>/documents/",
        views.upload_sick_leave_documents,
    ),
    path("service-requests/", views.create_service_request),
    path("my-requests/", views.my_requests),
    path("my-requests/<str:kind>/<int:request_id>/cancel/", views.cancel_my_request),
    path("balance/", views.balance),
    path("coordinator/requests/", views.coordinator_requests),
    path("coordinator/requests/<int:request_id>/decide/", views.coordinator_decide),
]
