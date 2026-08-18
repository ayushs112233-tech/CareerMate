from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    # Authentication
    path("login/", views.AdminLoginView.as_view(), name="login"),
    path("logout/", views.AdminLogoutView.as_view(), name="logout"),

    # 1. Main Dashboard
    path("", views.DashboardHomeView.as_view(), name="dashboard"),

    # 2. Candidates Management
    path("candidates/", views.CandidateListView.as_view(), name="candidates"),
    path("candidates/<int:pk>/", views.CandidateDetailView.as_view(), name="candidate_detail"),
    path("candidates/<int:pk>/delete/", views.CandidateDeleteView.as_view(), name="candidate_delete"),

    # 3. Recruiters Management
    path("recruiters/", views.RecruiterListView.as_view(), name="recruiters"),
    path("recruiters/<int:pk>/", views.RecruiterDetailView.as_view(), name="recruiter_detail"),

    # 4. Companies Management
    path("companies/", views.CompanyListView.as_view(), name="companies"),
    path("companies/create/", views.CompanyCreateView.as_view(), name="company_create"),
    path("companies/<int:pk>/edit/", views.CompanyUpdateView.as_view(), name="company_edit"),
    path("companies/<int:pk>/delete/", views.CompanyDeleteView.as_view(), name="company_delete"),

    # 5. Jobs Management
    path("jobs/", views.JobListView.as_view(), name="jobs"),
    path("jobs/create/", views.JobCreateView.as_view(), name="job_create"),
    path("jobs/<int:pk>/", views.JobDetailView.as_view(), name="job_detail"),
    path("jobs/<int:pk>/edit/", views.JobUpdateView.as_view(), name="job_edit"),
    path("jobs/<int:pk>/delete/", views.JobDeleteView.as_view(), name="job_delete"),

    # 6. Applications Management
    path("applications/", views.ApplicationListView.as_view(), name="applications"),
    path("applications/<int:pk>/", views.ApplicationDetailView.as_view(), name="application_detail"),
    path("applications/<int:pk>/status/", views.ApplicationStatusUpdateView.as_view(), name="application_status_update"),

    # 7. Resumes Management
    path("resumes/", views.ResumeListView.as_view(), name="resumes"),
    path("resumes/<int:pk>/", views.ResumeDetailView.as_view(), name="resume_detail"),

    # 8. Skills Management
    path("skills/", views.SkillListView.as_view(), name="skills"),
    path("skills/create/", views.SkillCreateView.as_view(), name="skill_create"),
    path("skills/<int:pk>/edit/", views.SkillUpdateView.as_view(), name="skill_edit"),
    path("skills/<int:pk>/delete/", views.SkillDeleteView.as_view(), name="skill_delete"),

    # 9. Job Categories Management
    path("job-categories/", views.JobCategoryListView.as_view(), name="job_categories"),
    path("job-categories/create/", views.JobCategoryCreateView.as_view(), name="job_category_create"),
    path("job-categories/<int:pk>/edit/", views.JobCategoryUpdateView.as_view(), name="job_category_edit"),
    path("job-categories/<int:pk>/delete/", views.JobCategoryDeleteView.as_view(), name="job_category_delete"),

    # 10. Reports & Analytics
    path("reports/", views.ReportsView.as_view(), name="reports"),
]
