import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from a .env file

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DEFAULT_MODEL = "llama-3.3-70b-versatile" #"mixtral-8x7b-32768"

# Base directory for projects
PROJECTS_BASE_DIR = "filmforge_projects"

# Ensure base project directory exists
os.makedirs(PROJECTS_BASE_DIR, exist_ok=True)

DEFAULT_PROJECT_STATE = {
    "project_name": "Untitled",
    "cleaned_name": "untitled",
    "current_phase": "Concept",
    "concept": { "seed_idea": "", "generated_concepts_md": "", "chosen_logline": "", "chosen_framework": "Three-Act Structure", "chosen_theme": "", "chosen_conflict": "", "synopsis_md": "", "final_synopsis": "" },
    "characters": {},
    "script": { "outline_md": "", "full_script_content": "", "analysis_md": "" },
    "pre_production": { "moodboard_ideas_md": "", "storyboard_ideas_md": "", "moodboard_images": [], "storyboard_images": [] }, # Add image storage
    "last_saved": None,
    "log": ["Project state initialized."]
}