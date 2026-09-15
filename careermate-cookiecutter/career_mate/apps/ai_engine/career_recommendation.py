from .job_matching import calculate_job_matches
from apps.jobs.models import Job

def generate_career_roadmap(candidate):
    """
    Generates dynamic career recommendations based on the candidate's profile,
    parsed resume, and skill gaps from top matching active jobs.
    """
    roadmap = []
    
    # Step 1: Foundation
    is_profile_complete = candidate.profile_complete
    has_resume = candidate.resumes.filter(parsed_text__isnull=False).exclude(parsed_text="").exists()
    
    roadmap.append({
        'title': 'Build your Profile & Resume',
        'completed': is_profile_complete and has_resume,
        'advice': "Your foundational step. Ensure your profile is 100% complete and your resume is parsed." 
                  if not (is_profile_complete and has_resume) 
                  else "Great job! Your profile and resume are ready."
    })
    
    # Step 2: Skill Gaps
    active_jobs = Job.objects.filter(status="active").prefetch_related('skills_required')
    if not active_jobs.exists():
        roadmap.append({
            'title': 'Market Analysis',
            'completed': False,
            'advice': 'No active jobs available in the market right now to analyze.'
        })
    else:
        # Get top 5 job matches
        top_matches = calculate_job_matches(candidate, active_jobs)[:5]
        
        missing_skills_freq = {}
        for match in top_matches:
            job = match['job']
            job_skills = set(job.skills_required.values_list('name', flat=True))
            candidate_skills = set(candidate.skills.values_list('name', flat=True))
            
            missing = job_skills.difference(candidate_skills)
            for skill in missing:
                missing_skills_freq[skill] = missing_skills_freq.get(skill, 0) + 1
                
        # Sort missing skills by frequency
        sorted_missing = sorted(missing_skills_freq.items(), key=lambda x: x[1], reverse=True)
        
        if sorted_missing:
            top_3_missing = [s[0] for s in sorted_missing[:3]]
            roadmap.append({
                'title': 'Close your Skill Gaps',
                'completed': False, # Always something to learn
                'advice': f"Based on your top matching jobs, you should learn: {', '.join(top_3_missing)}."
            })
        else:
            roadmap.append({
                'title': 'Close your Skill Gaps',
                'completed': True,
                'advice': "You have all the required skills for your top matching jobs!"
            })
            
    # Step 3: Application Momentum
    app_count = candidate.applications.count()
    roadmap.append({
        'title': 'Apply to Roles',
        'completed': app_count >= 3,
        'advice': f"You've applied to {app_count} jobs. Aim for at least 3 active applications." 
                  if app_count < 3 else "You have good application momentum!"
    })
    
    return roadmap
