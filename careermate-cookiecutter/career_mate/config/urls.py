from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("candidate/", include("apps.candidates.urls")),
    path("", lambda request: redirect("/candidate/")),
]