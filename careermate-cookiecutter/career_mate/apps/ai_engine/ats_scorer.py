import re

def calculate_ats_score(resume, candidate, extracted_skills=None):
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
    
    # 1. Skill Volume & Breadth (Max 40 points)
    num_skills = len(extracted_skills) if extracted_skills is not None else candidate.skills.count()
    skill_score = min(40, num_skills * 5)
    total_score += skill_score
    breakdown.append({
        'category': 'Skill Volume & Breadth',
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


def generate_resume_suggestions(resume, candidate, breakdown=None, extracted_skills=None):
    """
    Generates structured, actionable resume improvement suggestions based on the
    existing ATS scoring rules and candidate document content.
    """
    if not resume or not resume.parsed_text:
        return []

    text = resume.parsed_text.lower()
    suggestions = []
    
    # 1. Section Header suggestions
    if not re.search(r'\b(experience|employment|work history)\b', text):
        suggestions.append({
            'id': 'section_experience',
            'category': 'Sections',
            'title': 'Add an Experience Section',
            'description': 'Include a clearly labeled "Experience" or "Work History" section to help ATS parsers accurately index your past responsibilities.',
            'impact': '+15 pts',
            'automatic_verification': True,
        })
        
    if not re.search(r'\b(education|academic|degree)\b', text):
        suggestions.append({
            'id': 'section_education',
            'category': 'Sections',
            'title': 'Add an Education Section',
            'description': 'Add an "Education" or "Academic Background" section with your degree, college, or graduation details.',
            'impact': '+10 pts',
            'automatic_verification': True,
        })
        
    if not re.search(r'\b(projects|portfolio)\b', text):
        suggestions.append({
            'id': 'section_projects',
            'category': 'Sections',
            'title': 'Include Projects or Portfolio',
            'description': 'Add a "Projects" or "Portfolio" section with practical implementations to demonstrate technical proficiency.',
            'impact': '+5 pts',
            'automatic_verification': True,
        })
        
    # 2. Length & Readability suggestions
    words = len(text.split())
    if words < 250:
        suggestions.append({
            'id': 'length_short',
            'category': 'Readability',
            'title': 'Expand Resume Content',
            'description': f'Your resume contains only {words} words. Expand on your project details, tools, and quantified achievements (optimal: 250–800 words).',
            'impact': '+10 pts',
            'automatic_verification': True,
        })
    elif words > 800:
        suggestions.append({
            'id': 'length_long',
            'category': 'Readability',
            'title': 'Condense Resume Content',
            'description': f'Your resume contains {words} words. Aim for concise bullet points to keep it easily scannable by recruiters and ATS software.',
            'impact': '+5 pts',
            'automatic_verification': True,
        })
        
    # 3. Skill Volume suggestions
    num_skills = len(extracted_skills) if extracted_skills is not None else candidate.skills.count()
    if num_skills < 5:
        suggestions.append({
            'id': 'skill_density',
            'category': 'Skills',
            'title': 'Increase Technical Skill Density',
            'description': f'Only {num_skills} industry skills were detected. Explicitly list standard technologies (e.g. Python, SQL, React, AWS) in your skills section.',
            'impact': '+15 pts',
            'automatic_verification': True,
        })
        
    # 4. Profile Completeness suggestions
    if not candidate.headline:
        suggestions.append({
            'id': 'profile_headline',
            'category': 'Profile',
            'title': 'Add a Professional Headline',
            'description': 'Set a professional headline (e.g., "Full Stack Python Developer") on your profile to align your resume with target roles.',
            'impact': '+3 pts',
            'automatic_verification': True,
        })
        
    if not candidate.bio:
        suggestions.append({
            'id': 'profile_bio',
            'category': 'Profile',
            'title': 'Add a Professional Bio',
            'description': 'Add a brief summary or career objective to provide valuable context for ATS match scoring.',
            'impact': '+3 pts',
            'automatic_verification': True,
        })
        
    return suggestions
