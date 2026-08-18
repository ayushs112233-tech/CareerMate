from django.contrib import admin
from .models import Candidate, Skill


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "candidate_count", "created_at")
    list_filter = ("category",)
    search_fields = ("name", "category")
    ordering = ("name",)

    @admin.display(description="Candidates Count")
    def candidate_count(self, obj):
        return obj.candidates.count()


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = (
        "get_username",
        "get_full_name",
        "headline",
        "experience_years",
        "location",
        "profile_complete",
        "created_at",
    )
    list_filter = ("profile_complete", "experience_years", "created_at")
    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "headline",
        "location",
        "skills__name",
    )
    filter_horizontal = ("skills",)
    readonly_fields = ("created_at", "updated_at")
    ordering = ("-created_at",)

    @admin.display(description="Username")
    def get_username(self, obj):
        return obj.user.username

    @admin.display(description="Full Name")
    def get_full_name(self, obj):
        user_fn = getattr(obj.user, "get_full_name", None)
        return user_fn() if callable(user_fn) else ""
