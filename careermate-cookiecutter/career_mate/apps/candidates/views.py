from django.shortcuts import render


def candidate_dashboard(request):
    context = {
        "page_title": "Candidate Dashboard", "candidate_name": "Aarav Sharma",
        "stats": [{"label": "ATS Score", "value": "87%", "trend": "+8% from last review"}, {"label": "Jobs Applied", "value": "24", "trend": "+4 this week"}, {"label": "Matches Found", "value": "12", "trend": "+3 new matches"}, {"label": "Skill Gap", "value": "3", "trend": "2 critical skills left"}],
        "skills": [{"name": "Python", "value": 92}, {"name": "Django", "value": 80}, {"name": "SQL", "value": 74}],
        "jobs": [{"title": "Junior Python Developer", "company": "TechNova", "status": "Good Match"}, {"title": "Software Engineer Intern", "company": "BrightCode", "status": "Recommended"}],
    }
    return render(request, "candidate/dashboard.html", context)


def candidate_profile(request):
    profile = {"name": "Aarav Sharma", "role": "Aspiring Full Stack Developer", "email": "aarav.sharma@email.com", "phone": "+91 98765 43210", "location": "Bengaluru, India", "education": "BCA / MCA Student", "skills": ["Python", "Django", "JavaScript", "SQL", "React"]}
    return render(request, "candidate/profile.html", {"page_title": "Candidate Profile", "profile": profile})


def candidate_resume(request):
    resume = {"file_name": "Aarav_Sharma_Resume.pdf", "status": "Verified", "last_updated": "Today", "summary": "Full-stack aspiring developer with hands-on experience in Python, Django, HTML, CSS, JavaScript and SQL.", "keywords": ["Python", "Django", "SQL", "REST API"], "score": 87}
    return render(request, "candidate/resume.html", {"page_title": "Resume Center", "resume": resume})


def candidate_jobs(request):
    jobs = [{"title": "Junior Python Developer", "company": "TechNova", "location": "Bengaluru", "type": "Full-time", "match": "92%"}, {"title": "Software Engineer Intern", "company": "BrightCode", "location": "Hyderabad", "type": "Internship", "match": "85%"}, {"title": "Data Analyst", "company": "InsightWorks", "location": "Remote", "type": "Hybrid", "match": "78%"}]
    return render(request, "candidate/jobs.html", {"page_title": "Job Opportunities", "jobs": jobs})


def candidate_ats_score(request):
    metrics = [{"label": "ATS Match", "value": "87%", "detail": "Strong keyword alignment"}, {"label": "Readability", "value": "91%", "detail": "Very easy to scan"}, {"label": "Formatting", "value": "84%", "detail": "Few adjustments needed"}, {"label": "Skills Coverage", "value": "89%", "detail": "Most required skills present"}]
    suggestions = ["Add one more project using Django REST Framework.", "Include cloud deployment keywords like AWS or Docker.", "Mention measurable impact from internship or project work."]
    return render(request, "candidate/ats_score.html", {"page_title": "ATS Score", "metrics": metrics, "suggestions": suggestions})


def candidate_career_path(request):
    roadmap = [{"step": "Phase 1", "title": "Core Python & Data Structures", "status": "Completed"}, {"step": "Phase 2", "title": "Django Web Development", "status": "In Progress"}, {"step": "Phase 3", "title": "SQL + Backend APIs", "status": "Next"}, {"step": "Phase 4", "title": "Portfolio + Job Ready", "status": "Planned"}]
    return render(request, "candidate/career_path.html", {"page_title": "Career Path", "roadmap": roadmap})
