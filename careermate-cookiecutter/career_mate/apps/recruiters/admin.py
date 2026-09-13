from django.contrib import admin
from .models import Company, Recruiter


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "industry",
        "location",
        "website",
        "recruiter_count",
        "job_count",
        "created_at",
    )
    list_filter = ("industry", "created_at")
    search_fields = ("name", "industry", "location", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("name",)

    @admin.display(description="Recruiters")
    def recruiter_count(self, obj):
        return obj.recruiters.count()

    @admin.display(description="Posted Jobs")
    def job_count(self, obj):
        return obj.jobs.count()


@admin.register(Recruiter)
class RecruiterAdmin(admin.ModelAdmin):
    list_display = (
        "get_username",
        "get_full_name",
        "company",
        "designation",
        "phone",
        "created_at",
    )
    list_filter = ("company", "created_at")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "company__name",
        "designation",
    )
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    @admin.display(description="Username")
    def get_username(self, obj):
        return obj.user.username

    @admin.display(description="Full Name")
    def get_full_name(self, obj):
        user_fn = getattr(obj.user, "get_full_name", None)
        return user_fn() if callable(user_fn) else ""
