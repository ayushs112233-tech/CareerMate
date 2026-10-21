import mimetypes
import os

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from apps.jobs.models import Application, Job
from apps.jobs.forms import JobForm
from .forms import CompanyForm, RecruiterProfileForm
from .models import Company, Recruiter


class RecruiterRequiredMixin(LoginRequiredMixin):
    login_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not hasattr(request.user, 'recruiter_profile'):
            raise PermissionDenied("You must be a recruiter to access this page.")
        self.recruiter = request.user.recruiter_profile
        return super().dispatch(request, *args, **kwargs)


class RecruiterDashboardView(RecruiterRequiredMixin, TemplateView):
    template_name = "recruiters/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        jobs = Job.objects.filter(recruiter=self.recruiter)
        applications = Application.objects.filter(job__recruiter=self.recruiter)
        context.update({"total_jobs": jobs.count(), "active_jobs": jobs.filter(status="active").count(), "total_applications": applications.count(), "pending_applications": applications.filter(status__in=("applied", "under_review")).count(), "recent_jobs": jobs.annotate(application_count=Count("applications"))[:6], "recent_applications": applications.select_related("candidate__user", "job")[:6]})
        return context


class ProfileUpdateView(RecruiterRequiredMixin, UpdateView):
    model = Recruiter
    form_class = RecruiterProfileForm
    template_name = "recruiters/profile_form.html"
    success_url = reverse_lazy("recruiters:profile")

    def get_object(self, queryset=None): return self.recruiter
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs(); kwargs["user"] = self.request.user; return kwargs


class CompanyUpdateView(RecruiterRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "recruiters/company_form.html"
    success_url = reverse_lazy("recruiters:company")

    def get_object(self, queryset=None):
        if not self.recruiter.company_id:
            self.recruiter.company = Company.objects.create(name=f"{self.request.user.username}'s Company")
            self.recruiter.save(update_fields=["company"])
        return self.recruiter.company


class RecruiterJobQueryMixin(RecruiterRequiredMixin):
    def get_queryset(self): return Job.objects.filter(recruiter=self.recruiter).select_related("company", "category").prefetch_related("skills_required")


class JobListView(RecruiterJobQueryMixin, ListView):
    model = Job; template_name = "recruiters/jobs.html"; context_object_name = "jobs"; paginate_by = 12
    def get_queryset(self):
        queryset = super().get_queryset().annotate(application_count=Count("applications")); query = self.request.GET.get("q", "").strip(); status = self.request.GET.get("status", "")
        if query: queryset = queryset.filter(Q(title__icontains=query) | Q(location__icontains=query) | Q(description__icontains=query))
        if status in {"draft", "active", "closed"}: queryset = queryset.filter(status=status)
        return queryset


class JobCreateView(RecruiterRequiredMixin, CreateView):
    model = Job; form_class = JobForm; template_name = "recruiters/job_form.html"; success_url = reverse_lazy("jobs:recruiter_list")
    def form_valid(self, form):
        if not self.recruiter.company_id:
            form.add_error(None, "Complete your company profile before posting a job."); return self.form_invalid(form)
        form.instance.recruiter = self.recruiter; form.instance.company = self.recruiter.company
        messages.success(self.request, "Job posting created."); return super().form_valid(form)


class JobUpdateView(RecruiterJobQueryMixin, UpdateView):
    model = Job; form_class = JobForm; template_name = "recruiters/job_form.html"; success_url = reverse_lazy("jobs:recruiter_list")


class JobDeleteView(RecruiterJobQueryMixin, DeleteView):
    model = Job; template_name = "recruiters/job_confirm_delete.html"; success_url = reverse_lazy("jobs:recruiter_list")


class JobDetailView(RecruiterJobQueryMixin, DetailView):
    model = Job
    template_name = "recruiters/job_detail.html"
    context_object_name = "job"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["applications"] = self.object.applications.select_related(
            "candidate__user", "resume"
        ).order_by("-applied_at")
        context["status_choices"] = Application.STATUS_CHOICES
        return context


class ApplicationListView(RecruiterRequiredMixin, ListView):
    model = Application
    template_name = "recruiters/applications.html"
    context_object_name = "applications"
    paginate_by = 15

    def get_queryset(self):
        queryset = Application.objects.filter(job__recruiter=self.recruiter).select_related(
            "job", "candidate__user", "resume"
        )
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "").strip()
        job_id = self.request.GET.get("job", "").strip()

        if job_id:
            queryset = queryset.filter(job_id=job_id)
        if query:
            queryset = queryset.filter(
                Q(job__title__icontains=query)
                | Q(candidate__user__username__icontains=query)
                | Q(candidate__user__first_name__icontains=query)
                | Q(candidate__user__last_name__icontains=query)
            )
        if status:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = Application.STATUS_CHOICES
        context["recruiter_jobs"] = Job.objects.filter(recruiter=self.recruiter).order_by("title")
        context["selected_job_id"] = self.request.GET.get("job", "")
        context["selected_status"] = self.request.GET.get("status", "")
        context["query"] = self.request.GET.get("q", "")
        return context


class ApplicationStatusView(RecruiterRequiredMixin, UpdateView):
    model = Application
    fields = ("status",)
    http_method_names = ["post"]

    def get_queryset(self):
        return Application.objects.filter(job__recruiter=self.recruiter)

    def post(self, request, *args, **kwargs):
        application = self.get_object()
        status = request.POST.get("status")
        if status in dict(Application.STATUS_CHOICES):
            application.status = status
            application.save(update_fields=["status", "updated_at"])
            messages.success(request, f"Application status updated to {application.get_status_display()}.")
        return redirect("jobs:recruiter_applications")


class ApplicationResumeBaseView(RecruiterRequiredMixin, View):
    """
    Base view to securely serve a candidate's submitted resume for a job application.
    Enforces authorization: only the recruiter who owns the job can access the applicant's resume.
    Gracefully handles missing resume records and missing physical files.
    """
    as_attachment = False

    def get(self, request, pk, *args, **kwargs):
        application = get_object_or_404(
            Application.objects.select_related("job", "resume", "candidate__user"),
            pk=pk,
            job__recruiter=self.recruiter,
        )

        if not application.resume or not application.resume.file:
            raise Http404("No resume was submitted with this application.")

        resume = application.resume

        try:
            if not resume.file.storage.exists(resume.file.name):
                raise Http404("The requested resume file could not be found on storage.")
        except Http404:
            raise
        except Exception:
            raise Http404("Error verifying resume file existence.")

        try:
            file_handle = resume.file.open("rb")
        except Exception:
            raise Http404("Unable to read resume file.")

        download_name = resume.file_name or os.path.basename(resume.file.name) or f"resume_{application.id}.pdf"
        content_type, _ = mimetypes.guess_type(download_name)
        if not content_type:
            ext = os.path.splitext(download_name)[1].lower()
            if ext == ".pdf":
                content_type = "application/pdf"
            elif ext in (".docx", ".doc"):
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                content_type = "application/octet-stream"

        return FileResponse(
            file_handle,
            as_attachment=self.as_attachment,
            filename=download_name,
            content_type=content_type,
        )


class ApplicationResumeView(ApplicationResumeBaseView):
    """View candidate resume inline in the browser."""
    as_attachment = False


class ApplicationResumeDownloadView(ApplicationResumeBaseView):
    """Download candidate resume as attachment."""
    as_attachment = True
