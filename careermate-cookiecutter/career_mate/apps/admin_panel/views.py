from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.candidates.models import Candidate, Skill
from apps.jobs.models import Application, Job, JobCategory
from apps.recruiters.models import Company, Recruiter
from apps.resume.models import Resume
from .forms import (
    ApplicationStatusForm,
    CompanyForm,
    JobCategoryForm,
    JobForm,
    SkillForm,
)


class StaffRequiredMixin(UserPassesTestMixin):
    """
    Mixin that ensures the user is logged in and is a staff or superuser.
    Redirects unauthenticated or non-staff users to the shared account login.
    """

    def test_func(self):
        user = self.request.user
        return user.is_authenticated and (user.is_staff or user.is_superuser)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect(f"{reverse_lazy('accounts:login')}?next={self.request.path}")
        messages.error(self.request, "Access denied. Administrator privileges are required.")
        return redirect("accounts:login")


# ==========================================
# Authentication Views
# ==========================================

class AdminLoginView(View):
    def get(self, request):
        return redirect(f"{reverse_lazy('accounts:login')}?next={reverse_lazy('admin_panel:dashboard')}")

    def post(self, request):
        return self.get(request)


class AdminLogoutView(View):
    def get(self, request):
        return redirect("accounts:login")

    def post(self, request):
        return redirect("accounts:login")


# ==========================================
# 1. Main Dashboard View
# ==========================================

class DashboardHomeView(StaffRequiredMixin, TemplateView):
    template_name = "admin_dashboard/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Aggregate metrics from real PostgreSQL models
        context["total_candidates"] = Candidate.objects.count()
        context["total_recruiters"] = Recruiter.objects.count()
        context["total_companies"] = Company.objects.count()
        context["total_jobs"] = Job.objects.count()
        context["total_applications"] = Application.objects.count()
        context["total_resumes"] = Resume.objects.count()
        context["total_skills"] = Skill.objects.count()
        context["total_categories"] = JobCategory.objects.count()

        # Specific status counts
        context["active_jobs_count"] = Job.objects.filter(status="active").count()
        context["pending_applications_count"] = Application.objects.filter(
            status__in=["applied", "under_review"]
        ).count()

        # Recent activity tables
        context["recent_applications"] = Application.objects.select_related(
            "candidate__user", "job__company"
        ).order_by("-applied_at")[:6]

        context["recent_jobs"] = Job.objects.select_related(
            "company", "category", "recruiter__user"
        ).order_by("-created_at")[:6]

        return context


# ==========================================
# 2. Candidates Management
# ==========================================

class CandidateListView(StaffRequiredMixin, ListView):
    model = Candidate
    template_name = "admin_dashboard/candidates.html"
    context_object_name = "candidates"
    paginate_by = 15

    def get_queryset(self):
        qs = Candidate.objects.select_related("user").prefetch_related("skills").order_by("-created_at")
        query = self.request.GET.get("q", "").strip()
        status_filter = self.request.GET.get("status", "")

        if query:
            qs = qs.filter(
                Q(user__username__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(headline__icontains=query)
                | Q(location__icontains=query)
                | Q(skills__name__icontains=query)
            ).distinct()

        if status_filter == "complete":
            qs = qs.filter(profile_complete=True)
        elif status_filter == "incomplete":
            qs = qs.filter(profile_complete=False)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["status_filter"] = self.request.GET.get("status", "")
        return context


class CandidateDetailView(StaffRequiredMixin, DetailView):
    model = Candidate
    template_name = "admin_dashboard/candidate_detail.html"
    context_object_name = "candidate"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["resumes"] = self.object.resumes.order_by("-uploaded_at")
        context["applications"] = self.object.applications.select_related(
            "job__company"
        ).order_by("-applied_at")
        return context


class CandidateDeleteView(StaffRequiredMixin, DeleteView):
    model = Candidate
    template_name = "admin_dashboard/confirm_delete.html"
    success_url = reverse_lazy("admin_panel:candidates")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item_type"] = "Candidate Profile"
        context["item_name"] = str(self.object)
        context["cancel_url"] = reverse_lazy("admin_panel:candidates")
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Candidate profile deleted successfully.")
        return super().delete(request, *args, **kwargs)


# ==========================================
# 3. Recruiters Management
# ==========================================

class RecruiterListView(StaffRequiredMixin, ListView):
    model = Recruiter
    template_name = "admin_dashboard/recruiters.html"
    context_object_name = "recruiters"
    paginate_by = 15

    def get_queryset(self):
        qs = Recruiter.objects.select_related("user", "company").order_by("-created_at")
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(user__username__icontains=query)
                | Q(user__first_name__icontains=query)
                | Q(user__last_name__icontains=query)
                | Q(user__email__icontains=query)
                | Q(company__name__icontains=query)
                | Q(designation__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        return context


class RecruiterDetailView(StaffRequiredMixin, DetailView):
    model = Recruiter
    template_name = "admin_dashboard/recruiter_detail.html"
    context_object_name = "recruiter"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["posted_jobs"] = self.object.jobs.select_related("category", "company").order_by("-created_at")
        return context


# ==========================================
# 4. Companies Management
# ==========================================

class CompanyListView(StaffRequiredMixin, ListView):
    model = Company
    template_name = "admin_dashboard/companies.html"
    context_object_name = "companies"
    paginate_by = 15

    def get_queryset(self):
        qs = Company.objects.annotate(
            recruiters_count=Count("recruiters", distinct=True),
            jobs_count=Count("jobs", distinct=True),
        ).order_by("name")
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(name__icontains=query)
                | Q(industry__icontains=query)
                | Q(location__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        return context


class CompanyCreateView(StaffRequiredMixin, CreateView):
    model = Company
    form_class = CompanyForm
    template_name = "admin_dashboard/company_form.html"
    success_url = reverse_lazy("admin_panel:companies")

    def form_valid(self, form):
        messages.success(self.request, f"Company '{form.instance.name}' created successfully.")
        return super().form_valid(form)


class CompanyUpdateView(StaffRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "admin_dashboard/company_form.html"
    success_url = reverse_lazy("admin_panel:companies")

    def form_valid(self, form):
        messages.success(self.request, f"Company '{form.instance.name}' updated successfully.")
        return super().form_valid(form)


class CompanyDeleteView(StaffRequiredMixin, DeleteView):
    model = Company
    template_name = "admin_dashboard/confirm_delete.html"
    success_url = reverse_lazy("admin_panel:companies")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item_type"] = "Company"
        context["item_name"] = self.object.name
        context["cancel_url"] = reverse_lazy("admin_panel:companies")
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, f"Company '{self.get_object().name}' deleted.")
        return super().delete(request, *args, **kwargs)


# ==========================================
# 5. Jobs Management
# ==========================================

class JobListView(StaffRequiredMixin, ListView):
    model = Job
    template_name = "admin_dashboard/jobs.html"
    context_object_name = "jobs"
    paginate_by = 15

    def get_queryset(self):
        qs = Job.objects.select_related("company", "category", "recruiter__user").annotate(
            app_count=Count("applications")
        ).order_by("-created_at")

        query = self.request.GET.get("q", "").strip()
        status_val = self.request.GET.get("status", "").strip()
        cat_val = self.request.GET.get("category", "").strip()

        if query:
            qs = qs.filter(
                Q(title__icontains=query)
                | Q(company__name__icontains=query)
                | Q(location__icontains=query)
            )
        if status_val:
            qs = qs.filter(status=status_val)
        if cat_val:
            qs = qs.filter(category_id=cat_val)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["selected_category"] = self.request.GET.get("category", "")
        context["categories"] = JobCategory.objects.all()
        return context


class JobDetailView(StaffRequiredMixin, DetailView):
    model = Job
    template_name = "admin_dashboard/job_detail.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["applications"] = self.object.applications.select_related("candidate__user").order_by("-applied_at")
        context["skills"] = self.object.skills_required.all()
        return context


class JobCreateView(StaffRequiredMixin, CreateView):
    model = Job
    form_class = JobForm
    template_name = "admin_dashboard/job_form.html"
    success_url = reverse_lazy("admin_panel:jobs")

    def form_valid(self, form):
        messages.success(self.request, f"Job '{form.instance.title}' created successfully.")
        return super().form_valid(form)


class JobUpdateView(StaffRequiredMixin, UpdateView):
    model = Job
    form_class = JobForm
    template_name = "admin_dashboard/job_form.html"
    success_url = reverse_lazy("admin_panel:jobs")

    def form_valid(self, form):
        messages.success(self.request, f"Job '{form.instance.title}' updated successfully.")
        return super().form_valid(form)


class JobDeleteView(StaffRequiredMixin, DeleteView):
    model = Job
    template_name = "admin_dashboard/confirm_delete.html"
    success_url = reverse_lazy("admin_panel:jobs")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item_type"] = "Job Posting"
        context["item_name"] = self.object.title
        context["cancel_url"] = reverse_lazy("admin_panel:jobs")
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, f"Job '{self.get_object().title}' deleted.")
        return super().delete(request, *args, **kwargs)


# ==========================================
# 6. Applications Management
# ==========================================

class ApplicationListView(StaffRequiredMixin, ListView):
    model = Application
    template_name = "admin_dashboard/applications.html"
    context_object_name = "applications"
    paginate_by = 15

    def get_queryset(self):
        qs = Application.objects.select_related(
            "candidate__user", "job__company", "resume"
        ).order_by("-applied_at")

        query = self.request.GET.get("q", "").strip()
        status_val = self.request.GET.get("status", "").strip()

        if query:
            qs = qs.filter(
                Q(candidate__user__username__icontains=query)
                | Q(candidate__user__first_name__icontains=query)
                | Q(candidate__user__last_name__icontains=query)
                | Q(job__title__icontains=query)
                | Q(job__company__name__icontains=query)
            )
        if status_val:
            qs = qs.filter(status=status_val)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["status_choices"] = Application.STATUS_CHOICES
        return context


class ApplicationDetailView(StaffRequiredMixin, DetailView):
    model = Application
    template_name = "admin_dashboard/application_detail.html"
    context_object_name = "application"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["form"] = ApplicationStatusForm(instance=self.object)
        return context


class ApplicationStatusUpdateView(StaffRequiredMixin, View):
    def post(self, request, pk):
        app = get_object_or_404(Application, pk=pk)
        form = ApplicationStatusForm(request.POST, instance=app)
        if form.is_valid():
            form.save()
            messages.success(request, f"Application status updated to '{app.get_status_display()}'.")
        else:
            messages.error(request, "Failed to update status.")
        return redirect("admin_panel:application_detail", pk=app.pk)


# ==========================================
# 7. Resumes Management
# ==========================================

class ResumeListView(StaffRequiredMixin, ListView):
    model = Resume
    template_name = "admin_dashboard/resumes.html"
    context_object_name = "resumes"
    paginate_by = 15

    def get_queryset(self):
        qs = Resume.objects.select_related("candidate__user").order_by("-uploaded_at")
        query = self.request.GET.get("q", "").strip()
        status_val = self.request.GET.get("status", "").strip()

        if query:
            qs = qs.filter(
                Q(file_name__icontains=query)
                | Q(candidate__user__username__icontains=query)
                | Q(candidate__user__first_name__icontains=query)
                | Q(candidate__user__last_name__icontains=query)
                | Q(parsed_text__icontains=query)
            )
        if status_val:
            qs = qs.filter(status=status_val)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["status_choices"] = Resume.STATUS_CHOICES
        return context


class ResumeDetailView(StaffRequiredMixin, DetailView):
    model = Resume
    template_name = "admin_dashboard/resume_detail.html"
    context_object_name = "resume"


# ==========================================
# 8. Skills Management
# ==========================================

class SkillListView(StaffRequiredMixin, ListView):
    model = Skill
    template_name = "admin_dashboard/skills.html"
    context_object_name = "skills"
    paginate_by = 20

    def get_queryset(self):
        qs = Skill.objects.annotate(
            candidate_count=Count("candidates", distinct=True),
            job_count=Count("jobs", distinct=True),
        ).order_by("name")

        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(category__icontains=query))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        return context


class SkillCreateView(StaffRequiredMixin, CreateView):
    model = Skill
    form_class = SkillForm
    template_name = "admin_dashboard/skill_form.html"
    success_url = reverse_lazy("admin_panel:skills")

    def form_valid(self, form):
        messages.success(self.request, f"Skill '{form.instance.name}' added successfully.")
        return super().form_valid(form)


class SkillUpdateView(StaffRequiredMixin, UpdateView):
    model = Skill
    form_class = SkillForm
    template_name = "admin_dashboard/skill_form.html"
    success_url = reverse_lazy("admin_panel:skills")

    def form_valid(self, form):
        messages.success(self.request, f"Skill '{form.instance.name}' updated.")
        return super().form_valid(form)


class SkillDeleteView(StaffRequiredMixin, DeleteView):
    model = Skill
    template_name = "admin_dashboard/confirm_delete.html"
    success_url = reverse_lazy("admin_panel:skills")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item_type"] = "Skill"
        context["item_name"] = self.object.name
        context["cancel_url"] = reverse_lazy("admin_panel:skills")
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, f"Skill '{self.get_object().name}' deleted.")
        return super().delete(request, *args, **kwargs)


# ==========================================
# 9. Job Categories Management
# ==========================================

class JobCategoryListView(StaffRequiredMixin, ListView):
    model = JobCategory
    template_name = "admin_dashboard/job_categories.html"
    context_object_name = "categories"
    paginate_by = 20

    def get_queryset(self):
        qs = JobCategory.objects.annotate(job_count=Count("jobs")).order_by("name")
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(Q(name__icontains=query) | Q(description__icontains=query))
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_query"] = self.request.GET.get("q", "")
        return context


class JobCategoryCreateView(StaffRequiredMixin, CreateView):
    model = JobCategory
    form_class = JobCategoryForm
    template_name = "admin_dashboard/category_form.html"
    success_url = reverse_lazy("admin_panel:job_categories")

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' created.")
        return super().form_valid(form)


class JobCategoryUpdateView(StaffRequiredMixin, UpdateView):
    model = JobCategory
    form_class = JobCategoryForm
    template_name = "admin_dashboard/category_form.html"
    success_url = reverse_lazy("admin_panel:job_categories")

    def form_valid(self, form):
        messages.success(self.request, f"Category '{form.instance.name}' updated.")
        return super().form_valid(form)


class JobCategoryDeleteView(StaffRequiredMixin, DeleteView):
    model = JobCategory
    template_name = "admin_dashboard/confirm_delete.html"
    success_url = reverse_lazy("admin_panel:job_categories")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["item_type"] = "Job Category"
        context["item_name"] = self.object.name
        context["cancel_url"] = reverse_lazy("admin_panel:job_categories")
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, f"Category '{self.get_object().name}' deleted.")
        return super().delete(request, *args, **kwargs)


# ==========================================
# 10. Reports & Analytics View
# ==========================================

class ReportsView(StaffRequiredMixin, TemplateView):
    template_name = "admin_dashboard/reports.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Overview Counts
        context["total_candidates"] = Candidate.objects.count()
        context["total_recruiters"] = Recruiter.objects.count()
        context["total_jobs"] = Job.objects.count()
        context["total_applications"] = Application.objects.count()
        context["total_resumes"] = Resume.objects.count()
        context["total_companies"] = Company.objects.count()

        # Applications by Status Breakdown
        status_counts = Application.objects.values("status").annotate(count=Count("status"))
        status_dict = {item["status"]: item["count"] for item in status_counts}
        context["app_status_breakdown"] = [
            {"status": choice[0], "label": choice[1], "count": status_dict.get(choice[0], 0)}
            for choice in Application.STATUS_CHOICES
        ]

        # Jobs by Category Breakdown
        context["jobs_by_category"] = JobCategory.objects.annotate(
            job_count=Count("jobs")
        ).order_by("-job_count")

        # Jobs by Employment Type
        emp_counts = Job.objects.values("employment_type").annotate(count=Count("employment_type"))
        emp_dict = {item["employment_type"]: item["count"] for item in emp_counts}
        context["jobs_by_emp_type"] = [
            {"type": choice[0], "label": choice[1], "count": emp_dict.get(choice[0], 0)}
            for choice in Job.EMPLOYMENT_TYPES
        ]

        # Top In-Demand Skills
        context["top_skills"] = Skill.objects.annotate(
            job_demand=Count("jobs")
        ).order_by("-job_demand")[:10]

        return context
