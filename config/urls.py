from django.contrib import admin
from django.urls import path

from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "requests/<str:token>/<str:action>/",
        core_views.decide_service_request,
        name="decide_service_request",
    ),
]
