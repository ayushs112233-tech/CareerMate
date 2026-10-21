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
from apps.ai_engine.ats_scorer import calculate_ats_score, generate_resume_suggestions
from apps.ai_engine.resume_comparison import compare_resume_versions, get_candidate_version_history
from apps.ai_engine.job_matching import (
    calculate_job_matches,
    calculate_hybrid_match_score,
    get_active_analyzed_resume,
    get_candidate_matching_status,
    invalidate_candidate_match_cache,
)
from apps.ai_engine.skill_gap import analyze_skill_gap
from apps.ai_engine.career_recommendation import generate_career_roadmap


def _layout_context(candidate, **extra):
    name = candidate.user.get_full_name() or candidate.user.username
    return {"candidate": candidate, "candidate_name": name, **extra}


@candidate_required
def candidate_dashboard(request):
    candidate = request.user.candidate_profile
    latest_resume = candidate.resumes.first()
    active_resume = candidate.active_resume
    applications = candidate.applications.select_related("job__company")
    jobs = Job.objects.filter(status="active").select_related("company").prefetch_related("skills_required")
    
    # Use real job matching powered by the active analyzed resume
    matched_jobs_data = calculate_job_matches(candidate, jobs)[:4]
    recommended_jobs = [match['job'] for match in matched_jobs_data]
    for match in matched_jobs_data:
        match['job'].match_score = match['score']
    
    completion_fields = [candidate.headline, candidate.phone, candidate.location, candidate.bio, candidate.education]
    completion = round(
        (sum(bool(v) for v in completion_fields) + bool(candidate.skills.exists()) + bool(candidate.user.email))
        / 7 * 100
    )
    
    # Use active analyzed resume score if available, else latest
    ats_score = None
    if active_resume and active_resume.ats_score is not None:
        ats_score = active_resume.ats_score
    elif latest_resume and latest_resume.ats_score is not None:
        ats_score = latest_resume.ats_score
    elif latest_resume:
        ats_score, _ = calculate_ats_score(latest_resume, candidate)
    
    matching_status = get_candidate_matching_status(candidate)
    
    context = _layout_context(
        candidate,
        page_title="Candidate Dashboard",
        latest_resume=latest_resume,
        active_resume=active_resume,
        matching_status=matching_status,
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
        last_resume = candidate.resumes.order_by("-version_number").first()
        next_version = (last_resume.version_number + 1) if last_resume and last_resume.version_number else 1

        resume = form.save(candidate, commit=False)
        resume.version_number = next_version
        resume.status = "uploaded"
        resume.save()
        
        # Real Resume Parsing and Snapshot Analysis
        try:
            parsed_text = extract_text(resume.file, resume.file_name)
            resume.parsed_text = parsed_text
            
            # Extract skills from this resume
            existing_skills = Skill.objects.all()
            extracted_skills = extract_skills(parsed_text, existing_skills)
            extracted_skill_names = [s.name for s in extracted_skills]

            # Calculate ATS score, breakdown, and suggestions
            score, breakdown = calculate_ats_score(resume, candidate, extracted_skills=extracted_skills)
            suggestions = generate_resume_suggestions(resume, candidate, breakdown=breakdown, extracted_skills=extracted_skills)

            resume.ats_score = score
            resume.analysis_data = {
                "score": score,
                "breakdown": breakdown,
                "suggestions": suggestions,
                "extracted_skills": extracted_skill_names,
                "word_count": len(parsed_text.split()) if parsed_text else 0,
                "scoring_version": "v1.0",
            }
            resume.status = "parsed"
            resume.save(update_fields=["parsed_text", "status", "ats_score", "analysis_data"])
            
            # Add new skills to candidate profile
            if extracted_skills:
                candidate.skills.add(*extracted_skills)
            
            # Invalidate cached match results when a new analyzed resume is added
            invalidate_candidate_match_cache(candidate)

            if extracted_skills:
                messages.success(
                    request,
                    f"Resume Version {resume.version_number} uploaded & analyzed! ATS Score: {score}/100 with {len(extracted_skills)} skills detected."
                )
            else:
                messages.success(
                    request,
                    f"Resume Version {resume.version_number} uploaded & analyzed! ATS Score: {score}/100."
                )
                
        except Exception as e:
            resume.status = "error"
            resume.save(update_fields=["status"])
            messages.error(
                request,
                f"Error analyzing Resume Version {resume.version_number}: {str(e)}. The document has been saved, but ATS scoring could not complete."
            )
            
        return redirect("candidate_resume")
        
    matching_status = get_candidate_matching_status(candidate)
    return render(
        request,
        "candidate/resume.html",
        _layout_context(
            candidate,
            page_title="Resume Center",
            form=form,
            resumes=candidate.resumes.all().prefetch_related("applications"),
            latest_resume=candidate.resumes.first(),
            active_resume=candidate.active_resume,
            matching_status=matching_status,
        ),
    )


@candidate_required
def candidate_resume_download(request, pk):
    resume = get_object_or_404(Resume, pk=pk, candidate=request.user.candidate_profile)
    if not resume.file or not resume.file_exists:
        raise Http404("Resume file is unavailable or missing from storage")
    try:
        f = resume.file.open("rb")
    except Exception:
        raise Http404("Unable to read resume file")
    return FileResponse(f, as_attachment=True, filename=resume.file_name)


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
        
    # Apply TF-IDF matching using active analyzed resume
    matched_jobs_data = calculate_job_matches(candidate, jobs)
    for match in matched_jobs_data:
        match['job'].match_score = match['score']
    
    sorted_jobs = [match['job'] for match in matched_jobs_data]
    applied_ids = set(candidate.applications.values_list("job_id", flat=True))
    matching_status = get_candidate_matching_status(candidate)

    return render(
        request,
        "candidate/jobs.html",
        _layout_context(
            candidate,
            page_title="Find Your Next Role",
            jobs=sorted_jobs,
            query=query,
            applied_ids=applied_ids,
            matching_status=matching_status,
        ),
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
        # Default to latest successfully analyzed resume version
        resume = candidate.active_resume or candidate.resumes.first()
        if not resume:
            messages.error(request, "Upload a resume before applying to a job.")
            return redirect("candidate_resume")
            
        match_score = calculate_hybrid_match_score(candidate, job, resume=resume)
        Application.objects.create(job=job, candidate=candidate, resume=resume, match_score=match_score)
        messages.success(request, f"Your application was submitted successfully with Resume Version {resume.version_number}.")
        return redirect("candidate_applications")
        
    matching_status = get_candidate_matching_status(candidate)
    return render(
        request,
        "candidate/job_detail.html",
        _layout_context(
            candidate,
            page_title=job.title,
            job=job,
            application=application,
            skill_gap=skill_gap,
            matching_status=matching_status,
        ),
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
    resume = candidate.active_resume or candidate.resumes.first()
    
    score = None
    breakdown = []
    suggestions = []
    extracted_skills = []
    
    if resume and resume.analysis_data:
        score = resume.ats_score if resume.ats_score is not None else resume.analysis_data.get("score", 0)
        breakdown = resume.analysis_data.get("breakdown", [])
        suggestions = resume.analysis_data.get("suggestions", [])
        extracted_skills = resume.analysis_data.get("extracted_skills", [])
    elif resume:
        score, breakdown = calculate_ats_score(resume, candidate)
        suggestions = generate_resume_suggestions(resume, candidate, breakdown=breakdown)
        extracted_skills = resume.extracted_skills_list
        resume.ats_score = score
        resume.analysis_data = {
            "score": score,
            "breakdown": breakdown,
            "suggestions": suggestions,
            "extracted_skills": extracted_skills,
            "word_count": len(resume.parsed_text.split()) if resume.parsed_text else 0,
            "scoring_version": resume.scoring_version or "v1.0",
        }
        resume.save(update_fields=["ats_score", "analysis_data"])
    else:
        score = 0
        breakdown = []
        suggestions = []
        extracted_skills = []
        
    metrics = []
    if breakdown:
        for item in breakdown:
            metrics.append((
                item.get('category', ''),
                item.get('score', 0),
                item.get('message', '')
            ))
    else:
        metrics = [
            ("Resume readiness", 0, "Upload and process a resume to calculate your score."),
        ]
        
    all_resumes = candidate.resumes.all().order_by("-version_number")
    previous_resume = all_resumes[1] if all_resumes.count() > 1 else None
    score_change = None
    if previous_resume and previous_resume.ats_score is not None and score is not None:
        score_change = score - previous_resume.ats_score

    matching_status = get_candidate_matching_status(candidate)

    return render(
        request,
        "candidate/ats_score.html",
        _layout_context(
            candidate,
            page_title="AI Resume Insights",
            resume=resume,
            previous_resume=previous_resume,
            score=score,
            score_change=score_change,
            metrics=metrics,
            suggestions=suggestions,
            extracted_skills=extracted_skills,
            total_versions=all_resumes.count(),
            matching_status=matching_status,
        ),
    )


@candidate_required
def candidate_resume_progress(request):
    candidate = request.user.candidate_profile
    resumes = candidate.resumes.all().prefetch_related("applications").order_by("-version_number")
    analyzed_resumes = [r for r in resumes if r.ats_score is not None or r.status == "parsed"]
    
    # Custom pair comparison support (optional GET params v1, v2)
    v1_id = request.GET.get("v1")
    v2_id = request.GET.get("v2")
    
    prev_resume = None
    curr_resume = None
    
    if v1_id and v2_id:
        try:
            r1 = resumes.get(pk=int(v1_id))
            r2 = resumes.get(pk=int(v2_id))
            if r1.version_number <= r2.version_number:
                prev_resume, curr_resume = r1, r2
            else:
                prev_resume, curr_resume = r2, r1
        except (ValueError, Resume.DoesNotExist):
            prev_resume = None
            curr_resume = None
            
    if not curr_resume and len(analyzed_resumes) >= 2:
        curr_resume = analyzed_resumes[0]
        prev_resume = analyzed_resumes[1]
    elif not curr_resume and len(analyzed_resumes) == 1:
        curr_resume = analyzed_resumes[0]
        prev_resume = None

    comparison = None
    if curr_resume and prev_resume:
        comparison = compare_resume_versions(prev_resume, curr_resume)
        
    history = get_candidate_version_history(candidate)
    matching_status = get_candidate_matching_status(candidate)
    
    return render(
        request,
        "candidate/resume_progress.html",
        _layout_context(
            candidate,
            page_title="Resume Progress & Version Comparison",
            resumes=resumes,
            analyzed_resumes=analyzed_resumes,
            curr_resume=curr_resume,
            prev_resume=prev_resume,
            comparison=comparison,
            history=history,
            total_versions=resumes.count(),
            active_resume=candidate.active_resume,
            matching_status=matching_status,
        ),
    )


@candidate_required
def candidate_resume_version_detail(request, pk):
    candidate = request.user.candidate_profile
    resume = get_object_or_404(Resume, pk=pk, candidate=candidate)
    
    if not resume.analysis_data and resume.parsed_text:
        existing_skills = Skill.objects.all()
        extracted_skills = extract_skills(resume.parsed_text, existing_skills)
        score, breakdown = calculate_ats_score(resume, candidate, extracted_skills=extracted_skills)
        suggestions = generate_resume_suggestions(resume, candidate, breakdown=breakdown, extracted_skills=extracted_skills)
        resume.ats_score = score
        resume.analysis_data = {
            "score": score,
            "breakdown": breakdown,
            "suggestions": suggestions,
            "extracted_skills": [s.name for s in extracted_skills],
            "word_count": len(resume.parsed_text.split()),
            "scoring_version": resume.scoring_version or "v1.0",
        }
        resume.save(update_fields=["ats_score", "analysis_data"])
        
    analysis = resume.analysis_data or {}
    breakdown = analysis.get("breakdown") or []
    suggestions = analysis.get("suggestions") or []
    extracted_skills = analysis.get("extracted_skills") or []
    score = resume.ats_score if resume.ats_score is not None else analysis.get("score", 0)
    
    return render(
        request,
        "candidate/resume_version_detail.html",
        _layout_context(
            candidate,
            page_title=f"Resume Version {resume.version_number} Analysis",
            resume=resume,
            score=score,
            breakdown=breakdown,
            suggestions=suggestions,
            extracted_skills=extracted_skills,
            word_count=analysis.get("word_count", 0),
            scoring_version=analysis.get("scoring_version", resume.scoring_version),
            has_applications=resume.applications.exists(),
        ),
    )


@candidate_required
def candidate_resume_delete(request, pk):
    candidate = request.user.candidate_profile
    resume = get_object_or_404(Resume, pk=pk, candidate=candidate)

    # Protection: Do not break recruiter access if resume is linked to an application
    if resume.applications.exists():
        app_count = resume.applications.count()
        messages.error(
            request,
            f"Resume Version {resume.version_number} ({resume.file_name}) cannot be deleted because it is "
            f"linked to {app_count} job application(s). Recruiters require this document to review your application."
        )
        return redirect("candidate_resume_progress")

    if request.method == "POST":
        version_num = resume.version_number
        file_name = resume.file_name

        # Clean up storage file safely
        if resume.file and resume.file.name:
            try:
                storage = resume.file.storage
                if storage.exists(resume.file.name):
                    storage.delete(resume.file.name)
            except Exception:
                pass

        resume.delete()
        invalidate_candidate_match_cache(candidate)

        remaining_resumes = candidate.resumes.all()
        new_active = candidate.active_resume

        if remaining_resumes.exists():
            if new_active:
                messages.success(
                    request,
                    f"Resume Version {version_num} ({file_name}) has been deleted. "
                    f"Version {new_active.version_number} is now your active resume for job recommendations."
                )
            else:
                messages.success(
                    request,
                    f"Resume Version {version_num} ({file_name}) has been deleted. "
                    f"Version {remaining_resumes.first().version_number} is your newest resume."
                )
        else:
            messages.success(
                request,
                f"Resume Version {version_num} ({file_name}) has been deleted. "
                f"You currently have no resumes uploaded."
            )

        return redirect("candidate_resume_progress")

    # GET confirmation view
    remaining_resumes = candidate.resumes.exclude(pk=resume.pk)
    return render(
        request,
        "candidate/resume_confirm_delete.html",
        _layout_context(
            candidate,
            page_title=f"Delete Resume Version {resume.version_number}",
            resume=resume,
            remaining_resumes=remaining_resumes,
            remaining_count=remaining_resumes.count(),
        ),
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
