from django.core.cache import cache
from django.utils import timezone
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np


def get_active_analyzed_resume(candidate):
    """
    Returns the latest successfully analyzed resume version for the candidate.
    Only resumes with 'parsed' (or legacy SCORED/PARSED) status, non-empty parsed_text,
    and a valid ats_score are considered.
    If a newer resume was uploaded but failed or is still processing, this returns
    the most recent version that actually succeeded.
    """
    if not candidate:
        return None
    return (
        candidate.resumes.filter(
            status__in=["parsed", "SCORED", "PARSED"],
            ats_score__isnull=False,
        )
        .exclude(parsed_text="")
        .order_by("-version_number", "-uploaded_at")
        .first()
    )


def get_candidate_matching_status(candidate):
    """
    Returns diagnostic information about the resume version currently used for matching.
    Identifies whether matching is using a fallback version because the newest upload
    is unanalyzed or failed.
    """
    if not candidate:
        return {"active_resume": None, "is_fallback": False, "status": "no_candidate"}

    latest_upload = candidate.resumes.first()
    active_resume = get_active_analyzed_resume(candidate)

    is_fallback = bool(latest_upload and active_resume and latest_upload.pk != active_resume.pk)
    fallback_reason = ""
    if is_fallback:
        fallback_reason = (
            f"Resume Version {latest_upload.version_number} has pending or incomplete analysis. "
            f"Job matching is currently powered by Version {active_resume.version_number}."
        )

    return {
        "active_resume": active_resume,
        "active_version": active_resume.version_number if active_resume else None,
        "latest_upload": latest_upload,
        "latest_version": latest_upload.version_number if latest_upload else None,
        "latest_status": latest_upload.get_status_display() if latest_upload else "",
        "is_fallback": is_fallback,
        "fallback_reason": fallback_reason,
    }


def _create_candidate_document(candidate, resume=None):
    """
    Combines candidate resume text, bio, and skills into a single document.
    Defaults to the candidate's latest successfully analyzed resume version.
    """
    doc_parts = []

    target_resume = resume or get_active_analyzed_resume(candidate)
    if target_resume and target_resume.parsed_text:
        doc_parts.append(target_resume.parsed_text)

    # Add profile information
    if candidate.headline:
        doc_parts.append(candidate.headline)
    if candidate.bio:
        doc_parts.append(candidate.bio)

    # Add candidate profile skills + extracted resume skills
    skills = set(candidate.skills.values_list("name", flat=True))
    if target_resume and target_resume.analysis_data:
        skills.update(target_resume.analysis_data.get("extracted_skills", []))

    if skills:
        doc_parts.append(" ".join(skills))

    return " ".join(doc_parts).lower()


def _create_job_document(job):
    """Combines job description, requirements, and skills into a single document."""
    doc_parts = [job.title]
    if job.description:
        doc_parts.append(job.description)
    if job.requirements:
        doc_parts.append(job.requirements)

    skills = job.skills_required.values_list("name", flat=True)
    if skills:
        doc_parts.append(" ".join(skills))

    return " ".join(doc_parts).lower()


def calculate_hybrid_match_score(candidate, job, resume=None):
    """
    Calculates a hybrid match score between a candidate and a job (0-100).
    Uses the latest successfully analyzed resume version (or the specified resume).
    Components:
    - 40%: Text Similarity (TF-IDF + Cosine Similarity)
    - 40%: Required Skill Coverage (What % of job's required skills the candidate has)
    - 20%: Candidate Skill Overlap (How many of candidate's skills match the job)
    """
    target_resume = resume or get_active_analyzed_resume(candidate)
    candidate_doc = _create_candidate_document(candidate, resume=target_resume)
    job_doc = _create_job_document(job)

    # 1. Text Similarity (TF-IDF) - 40% weight
    text_score = 0
    if candidate_doc.strip() and job_doc.strip():
        try:
            vectorizer = TfidfVectorizer(stop_words="english")
            tfidf_matrix = vectorizer.fit_transform([candidate_doc, job_doc])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            text_score = similarity * 100
        except Exception:
            text_score = 0

    # 2. Required Skill Coverage - 40% weight
    job_skills = {s.lower() for s in job.skills_required.values_list("name", flat=True)}
    candidate_skills = {s.lower() for s in candidate.skills.values_list("name", flat=True)}
    if target_resume and target_resume.analysis_data:
        candidate_skills.update(s.lower() for s in target_resume.analysis_data.get("extracted_skills", []))

    coverage_score = 0
    if job_skills:
        intersection = job_skills.intersection(candidate_skills)
        coverage_score = (len(intersection) / len(job_skills)) * 100
    else:
        coverage_score = text_score

    # 3. Relevance Precision (20% weight)
    precision_score = 0
    if candidate_skills and job_skills:
        precision_score = (len(job_skills.intersection(candidate_skills)) / len(candidate_skills)) * 100
    else:
        precision_score = text_score

    final_score = (0.40 * text_score) + (0.40 * coverage_score) + (0.20 * precision_score)
    return round(final_score)


# Caching and Staleness Invalidation

def _get_cache_key(candidate_id, job_id):
    return f"cm_job_match:{candidate_id}:{job_id}"


def get_cached_job_match(candidate, job, resume=None):
    """
    Retrieves cached match score with staleness detection.
    Returns (score, is_stale, version_number).
    """
    target_resume = resume or get_active_analyzed_resume(candidate)
    active_version = target_resume.version_number if target_resume else None

    key = _get_cache_key(candidate.id, job.id)
    cached_data = cache.get(key)

    if cached_data is not None and isinstance(cached_data, dict):
        cached_version = cached_data.get("resume_version")
        score = cached_data.get("score", 0)
        is_stale = (cached_version != active_version)
        return score, is_stale, cached_version

    # Not cached
    score = calculate_hybrid_match_score(candidate, job, resume=target_resume)
    cache.set(key, {
        "score": score,
        "resume_version": active_version,
        "calculated_at": timezone.now().isoformat(),
    }, timeout=3600)
    return score, False, active_version


def invalidate_candidate_match_cache(candidate, job_ids=None):
    """
    Refreshes/invalidates cached match results when the active analyzed resume changes.
    """
    if not candidate:
        return
    if job_ids:
        for jid in job_ids:
            cache.delete(_get_cache_key(candidate.id, jid))
    else:
        # If no specific job_ids provided, delete keys for all active jobs
        try:
            from apps.jobs.models import Job
            all_job_ids = Job.objects.filter(status="active").values_list("id", flat=True)
            for jid in all_job_ids:
                cache.delete(_get_cache_key(candidate.id, jid))
        except Exception:
            pass


def calculate_job_matches(candidate, jobs_queryset, force_refresh=False):
    """
    Calculates job match compatibility for a candidate across a queryset of jobs.
    Uses the latest successfully analyzed resume version.
    Supports caching, staleness detection, and immediate refreshing.
    """
    active_resume = get_active_analyzed_resume(candidate)
    active_version = active_resume.version_number if active_resume else None

    matches = []
    for job in jobs_queryset:
        if force_refresh:
            score = calculate_hybrid_match_score(candidate, job, resume=active_resume)
            cache.set(_get_cache_key(candidate.id, job.id), {
                "score": score,
                "resume_version": active_version,
                "calculated_at": timezone.now().isoformat(),
            }, timeout=3600)
            is_stale = False
            version_used = active_version
        else:
            score, is_stale, version_used = get_cached_job_match(candidate, job, resume=active_resume)
            # If stale, refresh immediately to guarantee up-to-date recommendations
            if is_stale:
                score = calculate_hybrid_match_score(candidate, job, resume=active_resume)
                cache.set(_get_cache_key(candidate.id, job.id), {
                    "score": score,
                    "resume_version": active_version,
                    "calculated_at": timezone.now().isoformat(),
                }, timeout=3600)
                is_stale = False
                version_used = active_version

        matches.append({
            "job": job,
            "score": score,
            "is_stale": is_stale,
            "matched_resume_version": version_used,
        })

    matches.sort(key=lambda x: x["score"], reverse=True)
    return matches

