from django.contrib import admin
from .models import Resume


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ("file_name", "candidate", "status", "uploaded_at")
    list_filter = ("status", "uploaded_at")
    search_fields = (
        "file_name",
        "candidate__user__username",
        "candidate__user__first_name",
        "candidate__user__last_name",
        "parsed_text",
    )
    readonly_fields = ("uploaded_at",)
    date_hierarchy = "uploaded_at"
    ordering = ("-uploaded_at",)
