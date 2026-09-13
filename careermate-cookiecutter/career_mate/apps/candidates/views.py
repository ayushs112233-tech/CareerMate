from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.jobs.models import Application, Job
from apps.resume.models import Resume
from .forms import CandidateProfileForm, ResumeUploadForm
from .models import Candidate


def _candidate(request):
    user = request.user
    if not user.is_authenticated:
        user_model = get_user_model()
        user, _ = user_model.objects.get_or_create(
            username="candidate-demo",
            defaults={
                "first_name": "Demo",
                "last_name": "Candidate",
                "email": "candidate@example.com",
            },
        )
    candidate, _ = Candidate.objects.get_or_create(user=user)
    return candidate


def _layout_context(candidate, **extra):
    name = candidate.user.get_full_name() or candidate.user.username
    return {"candidate": candidate, "candidate_name": name, **extra}


def candidate_login(request):
    return redirect("candidate_dashboard")


def candidate_logout(request):
    logout(request)
    return redirect("candidate_login")


def candidate_dashboard(request):
    candidate = _candidate(request)
    latest_resume = candidate.resumes.first()
    applications = candidate.applications.select_related("job__company")
    jobs = Job.objects.filter(status="active").select_related("company").prefetch_related("skills_required")
    candidate_skills = set(candidate.skills.values_list("id", flat=True))
    recommended_jobs = sorted(jobs, key=lambda job: len(candidate_skills.intersection(set(job.skills_required.values_list("id", flat=True)))), reverse=True)[:4]
    completion_fields = [candidate.headline, candidate.phone, candidate.location, candidate.bio, candidate.education]
    completion = round((sum(bool(value) for value in completion_fields) + bool(candidate.skills.exists()) + bool(candidate.user.email)) / 7 * 100)
    context = _layout_context(candidate, page_title="Candidate Dashboard", latest_resume=latest_resume, applications=applications[:5], recommended_jobs=recommended_jobs, completion=completion, application_count=applications.count(), active_application_count=applications.filter(status__in=["applied", "under_review", "shortlisted", "interview"]).count(), ats_score=87 if latest_resume and latest_resume.parsed_text else None)
    return render(request, "candidate/dashboard.html", context)


def candidate_profile(request):
    candidate = _candidate(request)
    form = CandidateProfileForm(request.POST or None, instance=candidate)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("candidate_profile")
    return render(request, "candidate/profile.html", _layout_context(candidate, page_title="Your Profile", form=form))


def candidate_resume(request):
    candidate = _candidate(request)
    form = ResumeUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save(candidate)
        messages.success(request, "Resume uploaded. Analysis will be available after processing.")
        return redirect("candidate_resume")
    return render(request, "candidate/resume.html", _layout_context(candidate, page_title="Resume Center", form=form, resumes=candidate.resumes.all(), latest_resume=candidate.resumes.first()))


def candidate_resume_download(request, pk):
    resume = get_object_or_404(Resume, pk=pk, candidate=_candidate(request))
    if not resume.file:
        raise Http404("Resume file is unavailable")
    return FileResponse(resume.file.open("rb"), as_attachment=True, filename=resume.file_name)


def candidate_jobs(request):
    candidate = _candidate(request)
    query = request.GET.get("q", "").strip()
    jobs = Job.objects.filter(status="active").select_related("company", "category").prefetch_related("skills_required")
    if query:
        jobs = jobs.filter(Q(title__icontains=query) | Q(company__name__icontains=query) | Q(location__icontains=query) | Q(description__icontains=query) | Q(requirements__icontains=query)).distinct()
    applied_ids = set(candidate.applications.values_list("job_id", flat=True))
    return render(request, "candidate/jobs.html", _layout_context(candidate, page_title="Find Your Next Role", jobs=jobs, query=query, applied_ids=applied_ids))


def candidate_job_detail(request, pk):
    candidate = _candidate(request)
    job = get_object_or_404(Job.objects.select_related("company", "category").prefetch_related("skills_required"), pk=pk, status="active")
    application = candidate.applications.filter(job=job).first()
    if request.method == "POST" and not application:
        resume = candidate.resumes.first()
        if not resume:
            messages.error(request, "Upload a resume before applying to a job.")
            return redirect("candidate_resume")
        Application.objects.create(job=job, candidate=candidate, resume=resume)
        messages.success(request, "Your application was submitted successfully.")
        return redirect("candidate_applications")
    return render(request, "candidate/job_detail.html", _layout_context(candidate, page_title=job.title, job=job, application=application))


def candidate_applications(request):
    candidate = _candidate(request)
    applications = candidate.applications.select_related("job__company", "resume")
    return render(request, "candidate/applications.html", _layout_context(candidate, page_title="My Applications", applications=applications))


def candidate_application_detail(request, pk):
    candidate = _candidate(request)
    application = get_object_or_404(candidate.applications.select_related("job__company", "resume"), pk=pk)
    return render(request, "candidate/application_detail.html", _layout_context(candidate, page_title="Application Details", application=application))


def candidate_ats_score(request):
    candidate = _candidate(request)
    resume = candidate.resumes.first()
    score = 87 if resume and resume.parsed_text else 0
    metrics = [("Resume readiness", score, "Upload and process a resume to calculate your score." if not resume else "Your latest resume is ready for review."), ("Profile completeness", min(100, len([candidate.headline, candidate.bio, candidate.education, candidate.location]) * 25), "Complete your profile to improve matching."), ("Skills coverage", min(100, candidate.skills.count() * 15), "Add the skills you want recruiters to find."), ("Application momentum", min(100, candidate.applications.count() * 20), "Apply to relevant roles to build momentum.")]
    return render(request, "candidate/ats_score.html", _layout_context(candidate, page_title="AI Resume Insights", resume=resume, score=score, metrics=metrics))


def candidate_career_path(request):
    candidate = _candidate(request)
    roadmap = [("Build your profile", bool(candidate.profile_complete)), ("Prepare your resume", bool(candidate.resumes.exists())), ("Explore matched roles", Job.objects.filter(status="active").exists()), ("Apply and track progress", candidate.applications.exists())]
    return render(request, "candidate/career_path.html", _layout_context(candidate, page_title="Career Roadmap", roadmap=roadmap))