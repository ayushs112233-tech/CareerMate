import io
import re
import PyPDF2
import docx

SKILL_ALIASES = {
    "js": "JavaScript",
    "react.js": "React",
    "reactjs": "React",
    "node.js": "NodeJS",
    "vue.js": "Vue",
    "postgres": "PostgreSQL",
    "ml": "Machine Learning",
    "nlp": "Natural Language Processing",
    "aws": "Amazon Web Services",
    "gcp": "Google Cloud",
    "k8s": "Kubernetes",
    "golang": "Go",
}

def extract_text_from_pdf(file_obj):
    text = ""
    try:
        reader = PyPDF2.PdfReader(file_obj)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        print(f"Error reading PDF: {e}")
    return text

def extract_text_from_docx(file_obj):
    text = ""
    try:
        doc = docx.Document(file_obj)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error reading DOCX: {e}")
    return text

def extract_text(file_obj, filename):
    """Extracts raw text from the uploaded file object based on its extension."""
    filename = filename.lower()
    text = ""
    
    # Read the file's content in memory if it's not already
    file_content = file_obj.read()
    file_obj.seek(0)  # Reset pointer for subsequent reads/saves
    
    bytes_io = io.BytesIO(file_content)
    
    if filename.endswith(".pdf"):
        text = extract_text_from_pdf(bytes_io)
    elif filename.endswith(".docx"):
        text = extract_text_from_docx(bytes_io)
    
    return text.strip()

def normalize_text(text):
    """Normalize text by converting to lowercase and replacing aliases."""
    text = text.lower()
    
    # Simple word boundary replacement for aliases
    for alias, normalized_name in SKILL_ALIASES.items():
        # Use regex to replace exact word matches
        pattern = r'\b' + re.escape(alias) + r'\b'
        text = re.sub(pattern, normalized_name.lower(), text)
        
    return text

def extract_skills(text, existing_skills_queryset):
    """
    Extracts skills by normalizing the text, applying aliases, and 
    finding matches against the existing Skill database.
    """
    if not text:
        return []

    normalized_text = normalize_text(text)
    matched_skills = []
    
    # We load all skills from DB (it's lightweight enough for this project)
    for skill in existing_skills_queryset:
        skill_name_lower = skill.name.lower()
        
        # Check if the exact skill name (or its normalized alias) is in the text
        # Using word boundaries to avoid partial matches (e.g., 'go' inside 'algorithm')
        # However, for multi-word skills like 'Machine Learning', standard substring search is often better.
        # We'll use word boundaries for short words, substring for long ones.
        
        if len(skill_name_lower) <= 3:
            pattern = r'\b' + re.escape(skill_name_lower) + r'\b'
            if re.search(pattern, normalized_text):
                matched_skills.append(skill)
        else:
            if skill_name_lower in normalized_text:
                matched_skills.append(skill)
                
    return matched_skills
