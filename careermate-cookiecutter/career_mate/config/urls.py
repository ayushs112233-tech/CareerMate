from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

# Django Low-Level Admin Site Customization
admin.site.site_header = "CareerMate AI — Low Level DB Administration"
admin.site.site_title = "CareerMate AI DB Admin"
admin.site.index_title = "Database Administration"

urlpatterns = [
    path("recruiter/", include("apps.recruiters.urls")),
    path("jobs/", include("apps.jobs.urls")),
    # Root URL redirects to Custom Admin Dashboard
    path("", lambda request: redirect("admin_panel:dashboard"), name="root_redirect"),

    # Custom Admin Management Dashboard (Main Admin Interface)
    path("admin-dashboard/", include("apps.admin_panel.urls")),

    # Low-level Django Admin
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)