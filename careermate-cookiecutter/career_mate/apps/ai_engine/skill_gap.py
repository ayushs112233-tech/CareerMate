def analyze_skill_gap(candidate, job):
    """
    Analyzes the skill gap between a candidate and a specific job.
    Returns dictionaries of matching and missing skills.
    """
    job_skills = set(job.skills_required.all())
    candidate_skills = set(candidate.skills.all())
    
    matching_skills = list(job_skills.intersection(candidate_skills))
    missing_skills = list(job_skills.difference(candidate_skills))
    
    return {
        'matching': matching_skills,
        'missing': missing_skills,
        'has_gap': len(missing_skills) > 0,
        'match_percentage': round(len(matching_skills) / len(job_skills) * 100) if job_skills else 100
    }
