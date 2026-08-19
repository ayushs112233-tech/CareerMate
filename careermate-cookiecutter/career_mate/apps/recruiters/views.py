from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CandidateStatusForm, CompanyProfileForm, JobPostingForm
from .models import CandidateApplication, CompanyProfile, JobPosting


def _company_for(user):
	if not user.is_authenticated:
		user, _ = User.objects.get_or_create(username="recruiter_demo")
	company, _ = CompanyProfile.objects.get_or_create(owner=user, defaults={"name": f"{user.username}'s company"})
	return company


def dashboard(request):
	company = _company_for(request.user)
	jobs = company.jobs.annotate(candidate_count=Count("applications"))
	applications = CandidateApplication.objects.filter(job__company=company).select_related("job")
	context = {
		"company": company,
		"jobs": jobs[:5],
		"applications": applications[:5],
		"active_jobs": jobs.filter(is_active=True).count(),
		"candidate_count": applications.count(),
		"shortlisted_count": applications.filter(status=CandidateApplication.Status.SHORTLISTED).count(),
		"high_match_count": applications.filter(compatibility_score__gte=80).count(),
	}
	return render(request, "recruiters/dashboard.html", {**context, "recruiter_name": company.owner.username})


def company_profile(request):
	company = _company_for(request.user)
	if request.method == "POST":
		form = CompanyProfileForm(request.POST, instance=company)
		if form.is_valid():
			form.save()
			return redirect("recruiters:company_profile")
	else:
		form = CompanyProfileForm(instance=company)
	return render(request, "recruiters/company_profile.html", {"form": form, "company": company})


def job_list(request):
	company = _company_for(request.user)
	jobs = company.jobs.annotate(candidate_count=Count("applications"))
	return render(request, "recruiters/job_list.html", {"company": company, "jobs": jobs})


def job_create(request):
	company = _company_for(request.user)
	form = JobPostingForm(request.POST or None)
	if form.is_valid():
		job = form.save(commit=False)
		job.company = company
		job.save()
		return redirect("recruiters:job_detail", pk=job.pk)
	return render(request, "recruiters/job_form.html", {"form": form, "page_title": "Create a job"})


def job_detail(request, pk):
	company = _company_for(request.user)
	job = get_object_or_404(JobPosting.objects.annotate(candidate_count=Count("applications")), pk=pk, company=company)
	applications = job.applications.all()
	return render(request, "recruiters/job_detail.html", {"job": job, "applications": applications})


def job_edit(request, pk):
	company = _company_for(request.user)
	job = get_object_or_404(JobPosting, pk=pk, company=company)
	form = JobPostingForm(request.POST or None, instance=job)
	if form.is_valid():
		form.save()
		return redirect("recruiters:job_detail", pk=job.pk)
	return render(request, "recruiters/job_form.html", {"form": form, "job": job, "page_title": "Edit job"})


def candidate_list(request):
	company = _company_for(request.user)
	applications = CandidateApplication.objects.filter(job__company=company).select_related("job")
	query = request.GET.get("q", "").strip()
	if query:
		applications = applications.filter(Q(candidate_name__icontains=query) | Q(job__title__icontains=query))
	status = request.GET.get("status", "")
	if status:
		applications = applications.filter(status=status)
	return render(request, "recruiters/candidate_list.html", {"applications": applications, "query": query, "status": status, "status_choices": CandidateApplication.Status.choices})


def candidate_detail(request, pk):
	company = _company_for(request.user)
	application = get_object_or_404(CandidateApplication, pk=pk, job__company=company)
	if request.method == "POST":
		form = CandidateStatusForm(request.POST, instance=application)
		if form.is_valid():
			form.save()
			return redirect("recruiters:candidate_detail", pk=pk)
	else:
		form = CandidateStatusForm(instance=application)
	return render(request, "recruiters/candidate_detail.html", {"application": application, "form": form})
