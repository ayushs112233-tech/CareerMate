from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

# Django Admin Site Customization
admin.site.site_header = "CareerMate AI — Administration"
admin.site.site_title = "CareerMate AI Admin"
admin.site.index_title = "CareerMate AI Management Dashboard"

urlpatterns = [
    path("admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)