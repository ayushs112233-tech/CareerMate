from django.urls import path
from . import views

app_name = "recruiters"

urlpatterns = [
	path("login/", views.RecruiterLoginView.as_view(), name="login"),
	path("logout/", views.RecruiterLogoutView.as_view(), name="logout"),
	path("", views.RecruiterDashboardView.as_view(), name="dashboard"),
	path("profile/", views.ProfileUpdateView.as_view(), name="profile"),
	path("company/", views.CompanyUpdateView.as_view(), name="company"),
]
