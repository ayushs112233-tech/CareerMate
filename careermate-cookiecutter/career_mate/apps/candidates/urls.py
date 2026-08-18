from django.urls import path

from . import views

app_name = "candidate"

urlpatterns = [
    path("", views.candidate_dashboard, name="candidate_dashboard"),
    path("profile/", views.candidate_profile, name="candidate_profile"),
    path("resume/", views.candidate_resume, name="candidate_resume"),
    path("jobs/", views.candidate_jobs, name="candidate_jobs"),
    path("ats-score/", views.candidate_ats_score, name="candidate_ats_score"),
    path("career-path/", views.candidate_career_path, name="candidate_career_path"),
]
