from django.urls import path

from .views import (
    candidate_ats_score,
    candidate_career_path,
    candidate_dashboard,
    candidate_jobs,
    candidate_profile,
    candidate_resume,
)

urlpatterns = [
    path("", candidate_dashboard, name="candidate_dashboard"),
    path("profile/", candidate_profile, name="candidate_profile"),
    path("resume/", candidate_resume, name="candidate_resume"),
    path("jobs/", candidate_jobs, name="candidate_jobs"),
    path("ats-score/", candidate_ats_score, name="candidate_ats_score"),
    path("career-path/", candidate_career_path, name="candidate_career_path"),
]
