from django.shortcuts import render


def candidate_dashboard(request):
    stats = [
        {"label": "ATS Score", "value": "87%", "trend": "+8% from last review"},
        {"label": "Jobs Applied", "value": "24", "trend": "+4 this week"},
        {"label": "Matches Found", "value": "12", "trend": "+3 new matches"},
        {"label": "Skill Gap", "value": "3", "trend": "2 critical skills left"},
    ]

    skills = [
        {"name": "Python", "value": 92},
        {"name": "Django", "value": 80},
        {"name": "SQL", "value": 74},
        {"name": "Problem Solving", "value": 88},
    ]

    jobs = [
        {"title": "Junior Python Developer", "company": "TechNova", "status": "Good Match", "badge": "success"},
        {"title": "Software Engineer Intern", "company": "BrightCode", "status": "Recommended", "badge": "info"},
        {"title": "Data Analyst", "company": "InsightWorks", "status": "Check skills", "badge": "warning"},
    ]

    activities = [
        {"text": "Resume analyzed for Data Analyst role", "time": "2h ago"},
        {"text": "Career recommendation updated", "time": "Yesterday"},
        {"text": "Skill gap report generated", "time": "3 days ago"},
    ]

    context = {
        "page_title": "Candidate Dashboard",
        "stats": stats,
        "skills": skills,
        "jobs": jobs,
        "activities": activities,
        "candidate_name": "Aarav Sharma",
    }
    return render(request, "candidate/dashboard.html", context)


def candidate_profile(request):
    profile = {
        "name": "Aarav Sharma",
        "role": "Aspiring Full Stack Developer",
        "email": "aarav.sharma@email.com",
        "phone": "+91 98765 43210",
        "location": "Bengaluru, India",
        "experience": "Fresher",
        "skills": ["Python", "Django", "JavaScript", "SQL", "React"],
        "education": "BCA / MCA Student",
        "resume_status": "Uploaded and analyzed",
        "last_updated": "Today",
    }

    context = {
        "page_title": "Candidate Profile",
        "profile": profile,
        "candidate_name": "Aarav Sharma",
    }
    return render(request, "candidate/profile.html", context)


def candidate_resume(request):
    resume = {
        "file_name": "Aarav_Sharma_Resume.pdf",
        "status": "Verified",
        "last_updated": "Today",
        "summary": "Full-stack aspiring developer with hands-on experience in Python, Django, HTML, CSS, JavaScript and SQL.",
        "keywords": ["Python", "Django", "SQL", "REST API", "Problem Solving", "Data Structures"],
        "score": 87,
    }
    context = {"page_title": "Resume Center", "candidate_name": "Aarav Sharma", "resume": resume}
    return render(request, "candidate/resume.html", context)


def candidate_jobs(request):
    jobs = [
        {"title": "Junior Python Developer", "company": "TechNova", "location": "Bengaluru", "type": "Full-time", "match": "92%", "badge": "success"},
        {"title": "Software Engineer Intern", "company": "BrightCode", "location": "Hyderabad", "type": "Internship", "match": "85%", "badge": "info"},
        {"title": "Data Analyst", "company": "InsightWorks", "location": "Remote", "type": "Hybrid", "match": "78%", "badge": "warning"},
    ]
    context = {"page_title": "Job Opportunities", "candidate_name": "Aarav Sharma", "jobs": jobs}
    return render(request, "candidate/jobs.html", context)


def candidate_ats_score(request):
    metrics = [
        {"label": "ATS Match", "value": "87%", "detail": "Strong keyword alignment"},
        {"label": "Readability", "value": "91%", "detail": "Very easy to scan"},
        {"label": "Formatting", "value": "84%", "detail": "Few adjustments needed"},
        {"label": "Skills Coverage", "value": "89%", "detail": "Most required skills present"},
    ]
    suggestions = [
        "Add one more project using Django REST Framework.",
        "Include cloud deployment keywords like AWS or Docker.",
        "Mention measurable impact from internship or project work.",
    ]
    context = {"page_title": "ATS Score", "candidate_name": "Aarav Sharma", "metrics": metrics, "suggestions": suggestions}
    return render(request, "candidate/ats_score.html", context)


def candidate_career_path(request):
    roadmap = [
        {"step": "Phase 1", "title": "Core Python & Data Structures", "status": "Completed"},
        {"step": "Phase 2", "title": "Django Web Development", "status": "In Progress"},
        {"step": "Phase 3", "title": "SQL + Backend APIs", "status": "Next"},
        {"step": "Phase 4", "title": "Portfolio + Job Ready", "status": "Planned"},
    ]
    context = {"page_title": "Career Path", "candidate_name": "Aarav Sharma", "roadmap": roadmap}
    return render(request, "candidate/career_path.html", context)
