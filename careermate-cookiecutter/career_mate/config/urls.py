from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import TemplateView

# Django Low-Level Admin Site Customization
admin.site.site_header = "CareerMate AI — Low Level DB Administration"
admin.site.site_title = "CareerMate AI DB Admin"
admin.site.index_title = "Database Administration"

urlpatterns = [
    # Root: redirect to accounts login (shared auth entry point)
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),

    # Shared accounts (register / login / logout)
    path("accounts/", include("apps.accounts.urls")),

    # Candidate portal
    path("candidate/", include("apps.candidates.urls")),

    # Recruiter portal
    path("recruiter/", include("apps.recruiters.urls")),

    # Jobs API / recruiter job management
    path("jobs/", include("apps.jobs.urls")),

    # Custom Admin Management Dashboard
    path("admin-dashboard/", include("apps.admin_panel.urls")),

    # Low-level Django Admin
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

