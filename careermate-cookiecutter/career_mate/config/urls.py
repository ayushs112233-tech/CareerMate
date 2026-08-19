from django.contrib import admin
from django.urls import include, path

from apps.recruiters.views import dashboard

urlpatterns = [
    path("", dashboard, name="home"),
    path("admin/", admin.site.urls),
    path("recruiter/", include("apps.recruiters.urls")),
]