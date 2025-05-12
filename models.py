from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, List, Any, Literal
from datetime import datetime

# Pydantic models for the state structure
class ConceptState(BaseModel):
    seed_idea: str = ""
    generated_concepts_md: str = ""
    chosen_logline: str = ""
    chosen_framework: str = "Three-Act Structure"
    chosen_theme: str = ""
    chosen_conflict: str = ""
    synopsis_md: str = ""
    final_synopsis: str = "" # Added from app.py's logic implicitly

class CharacterProfile(BaseModel):
    backstory: str = ""
    motivation: str = ""
    flaw: str = ""

class CharacterData(BaseModel):
    role: str = ""
    profile: CharacterProfile = CharacterProfile()
    arc_description: str = ""
    relationship_suggestions: str = ""

class ScriptState(BaseModel):
    outline_md: str = ""
    full_script_content: str = ""
    analysis_md: str = ""

class PreProductionState(BaseModel):
    moodboard_ideas_md: str = ""
    storyboard_ideas_md: str = ""
    # Image data stored as list of dicts { "type": "image/jpeg", "content": "base64_string" }
    moodboard_images: List[Dict[str, str]] = []
    storyboard_images: List[Dict[str, str]] = []


class ProjectState(BaseModel):
    # project_name is the display name used for directory/user interaction
    project_name: str = Field(..., description="Display name of the project")
    # cleaned_name is for internal file naming if needed, derived from project_name
    cleaned_name: str = Field(..., description="Cleaned name for internal use")
    current_phase: Literal["Concept", "Character", "Script", "Pre-Production"] = "Concept" # Use Literal for known phases
    concept: ConceptState = ConceptState()
    characters: Dict[str, CharacterData] = {} # Keyed by character name
    script: ScriptState = ScriptState()
    pre_production: PreProductionState = PreProductionState()
    last_saved: Optional[datetime] = None
    log: List[str] = []

    @validator('cleaned_name', pre=True, always=True)
    def generate_cleaned_name(cls, v, values):
        if 'project_name' in values and values['project_name']:
            return values['project_name'].strip().replace(" ", "_").lower()
        return "untitled" # Default if project_name is missing

# API Request Models

class CreateProjectRequest(BaseModel):
    project_name: str = Field(..., min_length=1, description="Name for the new project")

class LoadProjectResponse(ProjectState):
    # Response is the full state, already defined by ProjectState
    pass

class SaveProjectRequest(ProjectState):
    # Request to save is the full state, already defined by ProjectState
    pass

class GenerateConceptsRequest(BaseModel):
    seed_idea: str = Field(..., min_length=1, description="Seed idea for concept generation")

class GenerateSynopsisRequest(BaseModel):
    logline: Optional[str] = None
    framework: Optional[str] = "Three-Act Structure"
    theme: Optional[str] = None
    conflict: Optional[str] = None

class SuggestProfileRequest(BaseModel):
    role: str = Field(..., min_length=1, description="Character's role")
    genre: Optional[str] = None
    theme: Optional[str] = None

class CharacterProfileUpdate(BaseModel):
    role: str = Field(..., min_length=1, description="Character's role")
    profile: CharacterProfile = CharacterProfile()
    # Optionally allow updating arc/relationships via PUT, though generating is POST
    # arc_description: Optional[str] = None
    # relationship_suggestions: Optional[str] = None

class GenerateArcRequest(BaseModel):
    # arc generation needs the profile which is part of the state
    # and framework from concept state. No extra body needed, just char_name in path
    pass

class SuggestRelationshipsRequest(BaseModel):
    # Needs current character profile and other character roles from state
    # No extra body needed, just char_name in path
    pass

class GenerateOutlineRequest(BaseModel):
     # Needs synopsis from concept state
     pass

class DraftSceneRequest(BaseModel):
    scene_heading: str = Field(..., min_length=1, description="Scene heading (e.g., INT. OFFICE - DAY)")
    scene_description: str = Field(..., min_length=1, description="Description or goal of the scene")
    character_context: Optional[str] = None
    tone: Optional[str] = "neutral"

class UpdateScriptContentRequest(BaseModel):
    full_script_content: str = ""

class RefineTextRequest(BaseModel):
    text_to_refine: str = Field(..., min_length=1, description="Text snippet (dialogue or action) to refine")
    instruction: str = Field(..., min_length=1, description="Instruction for refinement (e.g., 'make tense', 'make concise')")

class AnalyzeScriptRequest(BaseModel):
     # Analyze from saved state, no body needed
     pass

class GenerateMoodboardRequest(BaseModel):
     # Needs concept details from state, no body needed
     pass

class GenerateStoryboardRequest(BaseModel):
    scene_text: str = Field(..., min_length=50, description="Text of the scene to generate storyboard ideas for")

# Response Models
class SuccessResponse(BaseModel):
    message: str

class ProjectListResponse(BaseModel):
    projects: List[str]

class GeneratedTextResponse(BaseModel):
    text: str

class GeneratedImageResponse(BaseModel):
     # Matches the structure returned by image_generator.py
    parts: List[Dict[str, str]]
    # Could also include the text ideas that prompted the images if generated together
    # prompt_ideas: Optional[str] = None # For moodboard/storyboard text ideas

class ComicPromptRequest(BaseModel):
    prompt: str = Field(..., min_length=1, description="Text prompt for generating a comic image")