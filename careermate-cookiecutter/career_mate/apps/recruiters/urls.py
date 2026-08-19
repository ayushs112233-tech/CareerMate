from django.urls import path

from . import views

app_name = "recruiters"

urlpatterns = [
	path("", views.dashboard, name="dashboard"),
	path("company/", views.company_profile, name="company_profile"),
	path("jobs/", views.job_list, name="job_list"),
	path("jobs/new/", views.job_create, name="job_create"),
	path("jobs/<int:pk>/", views.job_detail, name="job_detail"),
	path("jobs/<int:pk>/edit/", views.job_edit, name="job_edit"),
	path("candidates/", views.candidate_list, name="candidate_list"),
	path("candidates/<int:pk>/", views.candidate_detail, name="candidate_detail"),
]
