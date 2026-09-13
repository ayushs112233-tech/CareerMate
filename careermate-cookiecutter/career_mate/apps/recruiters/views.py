from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, TemplateView, UpdateView

from apps.jobs.models import Application, Job
from apps.jobs.forms import JobForm
from .forms import CompanyForm, RecruiterProfileForm
from .models import Company, Recruiter


class RecruiterLoginView(View):
	def get(self, request):
		return render(request, "recruiters/login.html", {"form": AuthenticationForm()})

	def post(self, request):
		form = AuthenticationForm(request, data=request.POST)
		if form.is_valid():
			login(request, form.get_user())
			return redirect("recruiters:dashboard")
		return render(request, "recruiters/login.html", {"form": form})


class RecruiterLogoutView(View):
	def post(self, request):
		logout(request)
		return redirect("recruiters:login")


class RecruiterRequiredMixin(LoginRequiredMixin):
	login_url = reverse_lazy("recruiters:login")

	def dispatch(self, request, *args, **kwargs):
		if not request.user.is_authenticated:
			return self.handle_no_permission()
		self.recruiter, _ = Recruiter.objects.get_or_create(user=request.user)
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
	model = Job; template_name = "recruiters/job_detail.html"; context_object_name = "job"


class ApplicationListView(RecruiterRequiredMixin, ListView):
	model = Application; template_name = "recruiters/applications.html"; context_object_name = "applications"; paginate_by = 15
	def get_queryset(self):
		queryset = Application.objects.filter(job__recruiter=self.recruiter).select_related("job", "candidate__user", "resume"); query = self.request.GET.get("q", ""); status = self.request.GET.get("status", "")
		if query: queryset = queryset.filter(Q(job__title__icontains=query) | Q(candidate__user__username__icontains=query) | Q(candidate__user__first_name__icontains=query) | Q(candidate__user__last_name__icontains=query))
		return queryset.filter(status=status) if status else queryset
	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs); context["status_choices"] = Application.STATUS_CHOICES; return context


class ApplicationStatusView(RecruiterRequiredMixin, UpdateView):
	model = Application; fields = ("status",); http_method_names = ["post"]
	def get_queryset(self): return Application.objects.filter(job__recruiter=self.recruiter)
	def post(self, request, *args, **kwargs):
		application = self.get_object(); status = request.POST.get("status")
		if status in dict(Application.STATUS_CHOICES): application.status = status; application.save(update_fields=["status", "updated_at"])
		return redirect("jobs:recruiter_applications")
