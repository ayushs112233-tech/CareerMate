from django.urls import path

from .views import (
    CompanyUpdateView,
    ProfileUpdateView,
    RecruiterDashboardView,
)

app_name = "recruiters"

urlpatterns = [
    path("", RecruiterDashboardView.as_view(), name="dashboard"),
    path("profile/", ProfileUpdateView.as_view(), name="profile"),
    path("company/", CompanyUpdateView.as_view(), name="company"),
]
