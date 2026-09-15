from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def _create_candidate_document(candidate):
    """Combines candidate resume text, bio, and skills into a single document."""
    doc_parts = []
    
    # Add latest parsed resume
    latest_resume = candidate.resumes.first()
    if latest_resume and latest_resume.parsed_text:
        doc_parts.append(latest_resume.parsed_text)
        
    # Add profile information
    if candidate.headline:
        doc_parts.append(candidate.headline)
    if candidate.bio:
        doc_parts.append(candidate.bio)
        
    # Add skills (give them extra weight by joining them)
    skills = candidate.skills.values_list('name', flat=True)
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
        
    skills = job.skills_required.values_list('name', flat=True)
    if skills:
        doc_parts.append(" ".join(skills))
        
    return " ".join(doc_parts).lower()

def calculate_hybrid_match_score(candidate, job):
    """
    Calculates a hybrid match score between a candidate and a job (0-100).
    Components:
    - 40%: Text Similarity (TF-IDF + Cosine Similarity)
    - 40%: Required Skill Coverage (What % of job's required skills the candidate has)
    - 20%: Candidate Skill Overlap (How many of candidate's skills match the job)
    """
    candidate_doc = _create_candidate_document(candidate)
    job_doc = _create_job_document(job)
    
    # 1. Text Similarity (TF-IDF) - 40% weight
    text_score = 0
    if candidate_doc.strip() and job_doc.strip():
        try:
            vectorizer = TfidfVectorizer(stop_words='english')
            tfidf_matrix = vectorizer.fit_transform([candidate_doc, job_doc])
            # cosine_similarity returns a matrix, we want [0][1]
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            text_score = similarity * 100
        except Exception:
            text_score = 0
            
    # 2. Required Skill Coverage - 40% weight
    job_skills = set(job.skills_required.values_list('id', flat=True))
    candidate_skills = set(candidate.skills.values_list('id', flat=True))
    
    coverage_score = 0
    if job_skills:
        intersection = job_skills.intersection(candidate_skills)
        coverage_score = (len(intersection) / len(job_skills)) * 100
    else:
        # If no skills required, we default to full coverage based on text similarity
        coverage_score = text_score
        
    # 3. Relevance Precision (20% weight)
    # Measures what percentage of the candidate's skills are actually relevant to this specific job.
    # Formula: (Intersecting Skills) / (Total Candidate Skills)
    # This rewards candidates with highly focused, relevant profiles and penalizes "keyword stuffing"
    # where a candidate lists dozens of irrelevant skills.
    precision_score = 0
    if candidate_skills and job_skills:
        precision_score = (len(job_skills.intersection(candidate_skills)) / len(candidate_skills)) * 100
    else:
        precision_score = text_score
        
    # Hybrid Calculation
    final_score = (0.40 * text_score) + (0.40 * coverage_score) + (0.20 * precision_score)
    return round(final_score)

def calculate_job_matches(candidate, jobs_queryset):
    """
    Given a candidate and a queryset of jobs, returns a list of dictionaries:
    [
        {'job': Job, 'score': 85},
        ...
    ]
    Sorted by score descending.
    """
    matches = []
    for job in jobs_queryset:
        score = calculate_hybrid_match_score(candidate, job)
        matches.append({'job': job, 'score': score})
        
    # Sort by highest score
    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches
