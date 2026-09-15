from django.urls import path
from apps.recruiters import views

app_name = "jobs"

urlpatterns = [
	path("", views.JobListView.as_view(), name="recruiter_list"),
	path("new/", views.JobCreateView.as_view(), name="create"),
	path("<int:pk>/", views.JobDetailView.as_view(), name="recruiter_detail"),
	path("<int:pk>/edit/", views.JobUpdateView.as_view(), name="edit"),
	path("<int:pk>/delete/", views.JobDeleteView.as_view(), name="delete"),
	path("applications/", views.ApplicationListView.as_view(), name="recruiter_applications"),
	path("applications/<int:pk>/status/", views.ApplicationStatusView.as_view(), name="application_status"),
]
