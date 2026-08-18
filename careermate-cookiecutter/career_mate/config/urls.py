from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

# Django Low-Level Admin Site Customization
admin.site.site_header = "CareerMate AI — Low Level DB Administration"
admin.site.site_title = "CareerMate AI DB Admin"
admin.site.index_title = "Database Administration"

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="accounts:login", permanent=False), name="home"),
    path("", include("apps.accounts.urls")),
    path("candidate/", include("apps.candidates.urls")),
    path("admin-dashboard/", include("apps.admin_panel.urls")),
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
