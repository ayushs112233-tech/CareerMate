from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.decorators import candidate_required
from apps.jobs.models import Application, Job
from apps.resume.models import Resume
from apps.candidates.models import Skill
from .forms import CandidateProfileForm, ResumeUploadForm

# AI Engine imports
from apps.ai_engine.resume_analyzer import extract_text, extract_skills
from apps.ai_engine.ats_scorer import calculate_ats_score
from apps.ai_engine.job_matching import calculate_job_matches
from apps.ai_engine.skill_gap import analyze_skill_gap
from apps.ai_engine.career_recommendation import generate_career_roadmap


def _layout_context(candidate, **extra):
    name = candidate.user.get_full_name() or candidate.user.username
    return {"candidate": candidate, "candidate_name": name, **extra}


@candidate_required
def candidate_dashboard(request):
    candidate = request.user.candidate_profile
    latest_resume = candidate.resumes.first()
    applications = candidate.applications.select_related("job__company")
    jobs = Job.objects.filter(status="active").select_related("company").prefetch_related("skills_required")
    
    # Use real job matching instead of ID intersection
    matched_jobs_data = calculate_job_matches(candidate, jobs)[:4]
    # We want to pass the Job objects along with their scores to the template
    recommended_jobs = [match['job'] for match in matched_jobs_data]
    # We can also attach the match score dynamically to the job object for the template to render
    for match in matched_jobs_data:
        match['job'].match_score = match['score']
    
    completion_fields = [candidate.headline, candidate.phone, candidate.location, candidate.bio, candidate.education]
    completion = round(
        (sum(bool(v) for v in completion_fields) + bool(candidate.skills.exists()) + bool(candidate.user.email))
        / 7 * 100
    )
    
    # Get actual ATS score
    ats_score, _ = calculate_ats_score(latest_resume, candidate) if latest_resume else (None, None)
    
    context = _layout_context(
        candidate,
        page_title="Candidate Dashboard",
        latest_resume=latest_resume,
        applications=applications[:5],
        recommended_jobs=recommended_jobs,
        completion=completion,
        application_count=applications.count(),
        active_application_count=applications.filter(
            status__in=["applied", "under_review", "shortlisted", "interview"]
        ).count(),
        ats_score=ats_score,
    )
    return render(request, "candidate/dashboard.html", context)


@candidate_required
def candidate_profile(request):
    candidate = request.user.candidate_profile
    form = CandidateProfileForm(request.POST or None, instance=candidate)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile has been updated.")
        return redirect("candidate_profile")
    return render(request, "candidate/profile.html", _layout_context(candidate, page_title="Your Profile", form=form))


@candidate_required
def candidate_resume(request):
    candidate = request.user.candidate_profile
    form = ResumeUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        resume = form.save(candidate, commit=False)
        
        # Real Resume Parsing
        try:
            parsed_text = extract_text(resume.file, resume.file_name)
            resume.parsed_text = parsed_text
            resume.status = "parsed"
            resume.save()
            
            # Extract skills and update candidate profile
            existing_skills = Skill.objects.all()
            extracted_skills = extract_skills(parsed_text, existing_skills)
            
            if extracted_skills:
                # Add new skills without removing old ones (using add(*items))
                candidate.skills.add(*extracted_skills)
                messages.success(request, f"Resume parsed! Added {len(extracted_skills)} new skills to your profile.")
            else:
                messages.success(request, "Resume uploaded and parsed successfully.")
                
        except Exception as e:
            resume.status = "error"
            resume.save()
            messages.error(request, f"Error parsing resume: {str(e)}. It has been saved, but AI matching may be limited.")
            
        return redirect("candidate_resume")
        
    return render(
        request,
        "candidate/resume.html",
        _layout_context(
            candidate,
            page_title="Resume Center",
            form=form,
            resumes=candidate.resumes.all(),
            latest_resume=candidate.resumes.first(),
        ),
    )


@candidate_required
def candidate_resume_download(request, pk):
    resume = get_object_or_404(Resume, pk=pk, candidate=request.user.candidate_profile)
    if not resume.file:
        raise Http404("Resume file is unavailable")
    return FileResponse(resume.file.open("rb"), as_attachment=True, filename=resume.file_name)


@candidate_required
def candidate_jobs(request):
    candidate = request.user.candidate_profile
    query = request.GET.get("q", "").strip()
    jobs = Job.objects.filter(status="active").select_related("company", "category").prefetch_related("skills_required")
    
    if query:
        jobs = jobs.filter(
            Q(title__icontains=query)
            | Q(company__name__icontains=query)
            | Q(location__icontains=query)
            | Q(description__icontains=query)
            | Q(requirements__icontains=query)
        ).distinct()
        
    # Apply TF-IDF matching to sort ALL jobs, query or not
    matched_jobs_data = calculate_job_matches(candidate, jobs)
    for match in matched_jobs_data:
        match['job'].match_score = match['score']
    
    sorted_jobs = [match['job'] for match in matched_jobs_data]
        
    applied_ids = set(candidate.applications.values_list("job_id", flat=True))
    return render(
        request,
        "candidate/jobs.html",
        _layout_context(candidate, page_title="Find Your Next Role", jobs=sorted_jobs, query=query, applied_ids=applied_ids),
    )


@candidate_required
def candidate_job_detail(request, pk):
    candidate = request.user.candidate_profile
    job = get_object_or_404(
        Job.objects.select_related("company", "category").prefetch_related("skills_required"),
        pk=pk,
        status="active",
    )
    application = candidate.applications.filter(job=job).first()
    
    # Analyze skill gap
    skill_gap = analyze_skill_gap(candidate, job)
    
    if request.method == "POST" and not application:
        resume = candidate.resumes.first()
        if not resume:
            messages.error(request, "Upload a resume before applying to a job.")
            return redirect("candidate_resume")
        Application.objects.create(job=job, candidate=candidate, resume=resume)
        messages.success(request, "Your application was submitted successfully.")
        return redirect("candidate_applications")
        
    return render(
        request,
        "candidate/job_detail.html",
        _layout_context(candidate, page_title=job.title, job=job, application=application, skill_gap=skill_gap),
    )


@candidate_required
def candidate_applications(request):
    candidate = request.user.candidate_profile
    applications = candidate.applications.select_related("job__company", "resume")
    return render(
        request,
        "candidate/applications.html",
        _layout_context(candidate, page_title="My Applications", applications=applications),
    )


@candidate_required
def candidate_application_detail(request, pk):
    candidate = request.user.candidate_profile
    application = get_object_or_404(
        candidate.applications.select_related("job__company", "resume"), pk=pk
    )
    return render(
        request,
        "candidate/application_detail.html",
        _layout_context(candidate, page_title="Application Details", application=application),
    )


@candidate_required
def candidate_ats_score(request):
    candidate = request.user.candidate_profile
    resume = candidate.resumes.first()
    
    # Real ATS calculation
    score, breakdown = calculate_ats_score(resume, candidate)
    if not resume:
        score = 0
        
    # We still keep some metric tracking for the UI display format, though it's now real data
    metrics = []
    if breakdown:
        for item in breakdown:
            metrics.append((
                item['category'],
                item['score'],
                item['message']
            ))
    else:
        # Fallback if no resume
        metrics = [
            ("Resume readiness", 0, "Upload and process a resume to calculate your score."),
        ]
        
    return render(
        request,
        "candidate/ats_score.html",
        _layout_context(candidate, page_title="AI Resume Insights", resume=resume, score=score, metrics=metrics),
    )


@candidate_required
def candidate_career_path(request):
    candidate = request.user.candidate_profile
    
    # Generate real career roadmap
    roadmap_data = generate_career_roadmap(candidate)
    
    # Convert dict list to tuple format expected by the template
    roadmap = [(item['title'], item['completed']) for item in roadmap_data]
    # To pass advice, we might need to modify the template, but we will pass it anyway
    
    return render(
        request,
        "candidate/career_path.html",
        _layout_context(candidate, page_title="Career Roadmap", roadmap=roadmap, roadmap_data=roadmap_data),
    )
