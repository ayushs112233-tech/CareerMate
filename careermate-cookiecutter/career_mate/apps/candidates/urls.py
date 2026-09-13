from django.urls import path

from .views import (
    candidate_application_detail,
    candidate_applications,
    candidate_ats_score,
    candidate_career_path,
    candidate_dashboard,
    candidate_job_detail,
    candidate_jobs,
    candidate_login,
    candidate_logout,
    candidate_profile,
    candidate_resume,
    candidate_resume_download,
)

urlpatterns = [
    path("", candidate_dashboard, name="candidate_dashboard"),
    path("login/", candidate_login, name="candidate_login"),
    path("logout/", candidate_logout, name="candidate_logout"),
    path("profile/", candidate_profile, name="candidate_profile"),
    path("resume/", candidate_resume, name="candidate_resume"),
    path("resume/<int:pk>/download/", candidate_resume_download, name="candidate_resume_download"),
    path("jobs/", candidate_jobs, name="candidate_jobs"),
    path("jobs/<int:pk>/", candidate_job_detail, name="candidate_job_detail"),
    path("applications/", candidate_applications, name="candidate_applications"),
    path("applications/<int:pk>/", candidate_application_detail, name="candidate_application_detail"),
    path("ats-score/", candidate_ats_score, name="candidate_ats_score"),
    path("career-path/", candidate_career_path, name="candidate_career_path"),
]
