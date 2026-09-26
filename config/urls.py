from django.contrib import admin
from django.urls import include, path

from api.webapp_views import healthz, webapp_index
from core import views as core_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("api.urls")),
    path("app/", webapp_index),
    path("healthz", healthz),
    path(
        "requests/<str:token>/<str:action>/",
        core_views.decide_service_request,
        name="decide_service_request",
    ),
]
