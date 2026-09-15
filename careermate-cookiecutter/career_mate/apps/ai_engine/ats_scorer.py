import re

def calculate_ats_score(resume, candidate):
    """
    Calculates a weighted ATS score from 0-100 based on the parsed resume text and candidate profile.
    
    Weights:
    1. Skills Match (40%): Presence of extracted skills.
    2. Sections (30%): Standard headers like Experience, Education, Projects.
    3. Readability & Formatting (15%): Optimal length (not too short/long).
    4. Profile Completeness (15%): How complete the CareerMate profile is.
    """
    if not resume or not resume.parsed_text:
        return 0, []
        
    text = resume.parsed_text.lower()
    breakdown = []
    total_score = 0
    
    # 1. Skills (Max 40 points)
    # Give points based on the number of skills extracted (up to 8 skills for max points)
    num_skills = candidate.skills.count()
    skill_score = min(40, num_skills * 5)
    total_score += skill_score
    breakdown.append({
        'category': 'Skills Identification',
        'score': skill_score,
        'max': 40,
        'message': f"Found {num_skills} skills." if num_skills > 0 else "No skills identified. Make sure to use standard skill names."
    })
    
    # 2. Key Sections (Max 30 points)
    # Look for common ATS section headers
    section_score = 0
    found_sections = []
    
    if re.search(r'\b(experience|employment|work history)\b', text):
        section_score += 15
        found_sections.append("Experience")
        
    if re.search(r'\b(education|academic|degree)\b', text):
        section_score += 10
        found_sections.append("Education")
        
    if re.search(r'\b(projects|portfolio)\b', text):
        section_score += 5
        found_sections.append("Projects")
        
    total_score += section_score
    breakdown.append({
        'category': 'Section Headers',
        'score': section_score,
        'max': 30,
        'message': f"Found sections: {', '.join(found_sections)}" if found_sections else "Missing standard headers like 'Experience' or 'Education'."
    })
    
    # 3. Readability & Formatting (Max 15 points)
    # Check word count. Optimal is roughly between 250 and 800 words.
    word_count = len(text.split())
    readability_score = 0
    readability_msg = ""
    if 250 <= word_count <= 800:
        readability_score = 15
        readability_msg = f"Optimal length ({word_count} words)."
    elif word_count < 250:
        readability_score = 5
        readability_msg = f"Resume is quite short ({word_count} words). Consider adding more detail."
    else:
        readability_score = 10
        readability_msg = f"Resume is quite long ({word_count} words). Ensure it is concise."
        
    total_score += readability_score
    breakdown.append({
        'category': 'Readability & Length',
        'score': readability_score,
        'max': 15,
        'message': readability_msg
    })
    
    # 4. Profile Completeness (Max 15 points)
    # A complete profile helps match better.
    completion_items = [candidate.headline, candidate.bio, candidate.education, candidate.location, candidate.phone]
    completion_score = min(15, sum(3 for item in completion_items if item))
    total_score += completion_score
    breakdown.append({
        'category': 'Profile Completeness',
        'score': completion_score,
        'max': 15,
        'message': "Your CareerMate profile adds valuable context for ATS scoring."
    })
    
    return total_score, breakdown
