from django.contrib import admin

from .models import CandidateApplication, CompanyProfile, JobPosting


@admin.register(CompanyProfile)
class CompanyProfileAdmin(admin.ModelAdmin):
	list_display = ["name", "owner", "industry", "location"]


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
	list_display = ["title", "company", "work_mode", "is_active", "created_at"]
	list_filter = ["is_active", "work_mode"]


@admin.register(CandidateApplication)
class CandidateApplicationAdmin(admin.ModelAdmin):
	list_display = ["candidate_name", "job", "compatibility_score", "status", "applied_at"]
	list_filter = ["status"]
	search_fields = ["candidate_name", "candidate_email"]
