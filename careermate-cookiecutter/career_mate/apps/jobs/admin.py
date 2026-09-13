from django.contrib import admin
from .models import Application, Job, JobCategory


@admin.register(JobCategory)
class JobCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "job_count", "created_at")
    search_fields = ("name", "description")
    ordering = ("name",)

    @admin.display(description="Jobs Count")
    def job_count(self, obj):
        return obj.jobs.count()


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "recruiter",
        "category",
        "employment_type",
        "min_experience",
        "status",
        "application_count",
        "created_at",
    )
    list_filter = ("status", "employment_type", "category", "created_at")
    search_fields = (
        "title",
        "company__name",
        "location",
        "description",
        "requirements",
    )
    filter_horizontal = ("skills_required",)
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    @admin.display(description="Applications")
    def application_count(self, obj):
        return obj.applications.count()


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = (
        "candidate",
        "job",
        "get_company",
        "status",
        "has_resume",
        "applied_at",
    )
    list_filter = ("status", "applied_at", "job__company")
    search_fields = (
        "candidate__user__username",
        "candidate__user__first_name",
        "candidate__user__last_name",
        "job__title",
        "job__company__name",
    )
    readonly_fields = ("applied_at", "updated_at")
    date_hierarchy = "applied_at"
    ordering = ("-applied_at",)

    @admin.display(description="Company")
    def get_company(self, obj):
        return obj.job.company.name

    @admin.display(boolean=True, description="Resume Attached")
    def has_resume(self, obj):
        return bool(obj.resume)
