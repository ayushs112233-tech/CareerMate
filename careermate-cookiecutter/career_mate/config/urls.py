from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.candidates.views import candidate_dashboard

# Django Low-Level Admin Site Customization
admin.site.site_header = "CareerMate AI — Low Level DB Administration"
admin.site.site_title = "CareerMate AI DB Admin"
admin.site.index_title = "Database Administration"

urlpatterns = [
    path("", candidate_dashboard, name="root_redirect"),

    path("candidate/", include("apps.candidates.urls")),

    # Custom Admin Management Dashboard (Main Admin Interface)
    path("admin-dashboard/", include("apps.admin_panel.urls")),

    # Low-level Django Admin
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)