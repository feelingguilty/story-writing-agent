import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from a .env file

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    # In Gradio, we might want to handle this more gracefully than raising an error
    print("Warning: GROQ_API_KEY environment variable not set. API calls will fail.")
    # raise ValueError("GROQ_API_KEY environment variable not set.") # Keep commented for Gradio

# You can choose different models available via Groq
DEFAULT_MODEL = "llama-3.3-70b-versatile" #"mixtral-8x7b-32768"

# Base directory for projects
PROJECTS_BASE_DIR = "filmforge_projects"

# Ensure base project directory exists
os.makedirs(PROJECTS_BASE_DIR, exist_ok=True)