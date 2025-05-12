import os
from fastapi import FastAPI, HTTPException, Body
from typing import Dict, List, Optional
import logging
from image_generator import generate_image_from_prompt
# Configure logging for FastAPI and its modules
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__) # Logger for this module
import datetime
# --- Project Imports ---
import config # Ensure config.py is in the same directory or PYTHONPATH
from project_manager import project_manager, ProjectManager # Import the instance and the class if needed
from image_generator import generate_image_from_prompt
from agents.concept_agent import ConceptAgent
from agents.character_agent import CharacterCrafterAgent
from agents.script_agent import ScriptSmithAgent
from models import (
    ProjectState, CreateProjectRequest, SaveProjectRequest,
    ProjectListResponse, SuccessResponse, GeneratedTextResponse,
    GenerateConceptsRequest, GenerateSynopsisRequest,
    CharacterProfileUpdate, SuggestProfileRequest,
    DraftSceneRequest, UpdateScriptContentRequest,
    RefineTextRequest, AnalyzeScriptRequest,
    GenerateStoryboardRequest, GeneratedImageResponse,
    GenerateMoodboardRequest, CharacterData, CharacterProfile # Import CharacterData and Profile
)
from models import (ComicPromptRequest,GeneratedImageResponse)
# --- FastAPI App Setup ---
app = FastAPI(
    title="FilmForge AI Assistant API",
    description="Backend API for FilmForge AI features and project management.",
    version="0.1.0",
)

# --- Instantiate Agents ---
# Agents are stateless and can be instantiated once globally
concept_agent = ConceptAgent()
character_agent = CharacterCrafterAgent()
script_agent = ScriptSmithAgent()

# --- Dependency (Optional but good practice) ---
# Could add dependency for ProjectManager if multiple instances were needed,
# but a single global instance is fine for this scope.
# def get_project_manager():
#     return project_manager


# --- Helper to load and save state within endpoints ---
def load_project_state_safe(project_name: str) -> ProjectState:
    """Loads state or raises HTTPException."""
    try:
        state_dict = project_manager.load_project(project_name)
        return ProjectState(**state_dict) # Validate with Pydantic model
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found.")
    except (IOError, json.JSONDecodeError) as e:
        logger.exception(f"Failed to load project '{project_name}':")
        raise HTTPException(status_code=500, detail=f"Failed to load project '{project_name}': {e}")
    except Exception as e:
        logger.exception(f"Unexpected error loading project '{project_name}':")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred loading project: {e}")


def save_project_state_safe(state: ProjectState) -> ProjectState:
    """Saves state or raises HTTPException."""
    try:
        state_dict = state.model_dump() # Convert Pydantic model to dict
        saved_state_dict = project_manager.save_project(state_dict)
        return ProjectState(**saved_state_dict) # Return the updated state (with save time/log)
    except (ValueError, IOError) as e:
        logger.exception(f"Failed to save project '{state.project_name}':")
        raise HTTPException(status_code=500, detail=f"Failed to save project '{state.project_name}': {e}")
    except Exception as e:
        logger.exception(f"Unexpected error saving project '{state.project_name}':")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred saving project: {e}")


# --- Endpoints ---

@app.get("/", summary="Root endpoint", tags=["General"])
async def read_root():
    return {"message": "FilmForge AI Assistant API"}

# --- Project Management Endpoints ---
@app.get("/projects", response_model=ProjectListResponse, summary="List all projects", tags=["Project Management"])
async def list_projects():
    """Lists all available filmforge projects."""
    projects = project_manager.get_project_list()
    return {"projects": projects}

@app.post("/projects", response_model=ProjectState, status_code=201, summary="Create a new project", tags=["Project Management"])
async def create_project(request: CreateProjectRequest):
    """Creates a new filmforge project."""
    try:
        new_state_dict = project_manager.create_project(request.project_name)
        return ProjectState(**new_state_dict)
    except FileExistsError:
        raise HTTPException(status_code=409, detail=f"Project '{request.project_name}' already exists.")
    except ValueError as e:
         raise HTTPException(status_code=400, detail=f"Invalid project name: {e}")
    except Exception as e:
        logger.exception(f"Failed to create project '{request.project_name}':")
        raise HTTPException(status_code=500, detail=f"Failed to create project: {e}")

@app.get("/projects/{project_name}", response_model=ProjectState, summary="Load a project", tags=["Project Management"])
async def load_project(project_name: str):
    """Loads the state of a specific project."""
    return load_project_state_safe(project_name)

@app.put("/projects/{project_name}", response_model=ProjectState, summary="Save project state", tags=["Project Management"])
async def save_project(project_name: str, state: SaveProjectRequest):
    """Saves the current state of a project."""
    if state.project_name != project_name:
        raise HTTPException(status_code=400, detail="Project name in path and body do not match.")

    # Optional: Load existing state first if you need to merge instead of overwrite
    try:
        existing_state = load_project_state_safe(project_name)
        # Merge logic if needed, e.g., preserving log entries not in the request state
        state.log = existing_state.log + [f"State received for save at {datetime.now().isoformat()}"] # Example
    except HTTPException as e:
         if e.status_code != 404: raise e # Re-raise if not just not found
         # If 404, it's a new save, proceed with the provided state

    return save_project_state_safe(state)

@app.delete("/projects/{project_name}", response_model=SuccessResponse, summary="Delete a project", tags=["Project Management"])
async def delete_project(project_name: str):
    """Deletes a project."""
    try:
        deleted = project_manager.delete_project(project_name)
        if not deleted:
             raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found.")
        return {"message": f"Project '{project_name}' deleted successfully."}
    except IOError as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project '{project_name}': {e}")
    except Exception as e:
        logger.exception(f"Unexpected error deleting project '{project_name}':")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred deleting project: {e}")


# --- Concept Development Endpoints ---
@app.post("/projects/{project_name}/concept/generate-concepts", response_model=GeneratedTextResponse, summary="Generate initial concepts", tags=["Concept Development"])
async def generate_initial_concepts(project_name: str, request: GenerateConceptsRequest):
    """Generates initial loglines, frameworks, themes, and conflicts."""
    state = load_project_state_safe(project_name)
    result_md = concept_agent.generate_initial_concepts(request.seed_idea)

    if "Error:" in result_md:
        raise HTTPException(status_code=500, detail=result_md)

    # Update state and save
    state.concept.seed_idea = request.seed_idea
    state.concept.generated_concepts_md = result_md
    save_project_state_safe(state)

    return {"text": result_md}

@app.post("/projects/{project_name}/concept/generate-synopsis", response_model=GeneratedTextResponse, summary="Generate synopsis", tags=["Concept Development"])
async def generate_synopsis(project_name: str, request: GenerateSynopsisRequest):
    """Generates a synopsis based on chosen concept elements."""
    state = load_project_state_safe(project_name)
    concept_details = request.model_dump(exclude_none=True) # Only include fields explicitly set

    # Use existing state values as defaults if not provided in the request body
    if concept_details.get('logline') is None:
         concept_details['logline'] = state.concept.chosen_logline
    if concept_details.get('framework') is None:
         concept_details['framework'] = state.concept.chosen_framework
    if concept_details.get('theme') is None:
         concept_details['theme'] = state.concept.chosen_theme
    if concept_details.get('conflict') is None:
         concept_details['conflict'] = state.concept.chosen_conflict


    if not concept_details.get('logline') and not concept_details.get('theme'):
         raise HTTPException(status_code=400, detail="At least 'logline' or 'theme' must be provided or exist in the current state.")

    result_md = concept_agent.generate_synopsis(concept_details)

    if "Error:" in result_md:
        raise HTTPException(status_code=500, detail=result_md)

    # Update state with chosen fields if provided, otherwise keep existing
    state.concept.chosen_logline = concept_details.get('logline') or state.concept.chosen_logline
    state.concept.chosen_framework = concept_details.get('framework') or state.concept.chosen_framework
    state.concept.chosen_theme = concept_details.get('theme') or state.concept.chosen_theme
    state.concept.chosen_conflict = concept_details.get('conflict') or state.concept.chosen_conflict
    state.concept.synopsis_md = result_md

    # Extract final synopsis without twists for other agents
    final_synopsis = result_md.split("### Potential Twists")[0].strip() if "### Potential Twists" in result_md else result_md
    state.concept.final_synopsis = final_synopsis

    save_project_state_safe(state)

    return {"text": result_md}


# --- Character Development Endpoints ---
@app.get("/projects/{project_name}/characters", response_model=Dict[str, CharacterData], summary="Get all characters", tags=["Character Development"])
async def get_all_characters(project_name: str):
    """Retrieves all character data for a project."""
    state = load_project_state_safe(project_name)
    return state.characters

@app.post("/projects/{project_name}/characters/suggest-profile", response_model=GeneratedTextResponse, summary="Suggest character profile elements", tags=["Character Development"])
async def suggest_character_profile(project_name: str, request: SuggestProfileRequest):
    """Suggests backstory, motivation, and flaw ideas for a character role."""
    state = load_project_state_safe(project_name) # Load state to get genre/theme context
    genre = state.concept.seed_idea # Using seed_idea as a proxy for genre
    theme = state.concept.chosen_theme

    result_md = character_agent.suggest_profile_elements(request.role, genre, theme)

    if "Error:" in result_md:
        raise HTTPException(status_code=500, detail=result_md)

    # Note: This endpoint does NOT save to state, it's just a suggestion tool.
    return {"text": result_md}

@app.put("/projects/{project_name}/characters/{char_name}", response_model=CharacterData, summary="Save/Update character profile", tags=["Character Development"])
async def save_character_profile(project_name: str, char_name: str, character_update: CharacterProfileUpdate):
    """Saves or updates a character's profile."""
    state = load_project_state_safe(project_name)

    # Ensure character exists or initialize if new
    if char_name not in state.characters:
        state.characters[char_name] = CharacterData(project_name=char_name, role=character_update.role) # Initialize base structure
    else:
         # Update role if provided, or keep existing
         state.characters[char_name].role = character_update.role # Always update role from input

    # Update profile fields
    state.characters[char_name].profile = character_update.profile # Overwrite profile or use defaults from model

    save_project_state_safe(state)

    return state.characters[char_name] # Return the saved character data

@app.post("/projects/{project_name}/characters/{char_name}/generate-arc", response_model=GeneratedTextResponse, summary="Generate character arc", tags=["Character Development"])
async def generate_character_arc(project_name: str, char_name: str):
    """Generates a character arc based on their profile and the project's framework."""
    state = load_project_state_safe(project_name)

    if char_name not in state.characters:
        raise HTTPException(status_code=404, detail=f"Character '{char_name}' not found.")

    char_data = state.characters[char_name]
    if not char_data.profile or not char_data.profile.motivation or not char_data.profile.flaw:
         raise HTTPException(status_code=400, detail=f"Character '{char_name}' needs motivation and flaw defined in their profile before generating an arc.")

    framework = state.concept.chosen_framework

    result_md = character_agent.map_character_arc(char_data.profile.model_dump(), framework) # Pass profile dict

    if "Error:" in result_md:
        raise HTTPException(status_code=500, detail=result_md)

    # Update state and save
    state.characters[char_name].arc_description = result_md
    save_project_state_safe(state)

    return {"text": result_md}

@app.post("/projects/{project_name}/characters/{char_name}/suggest-relationships", response_model=GeneratedTextResponse, summary="Suggest relationships", tags=["Character Development"])
async def suggest_relationships(project_name: str, char_name: str):
    """Suggests relationships between a character and other characters in the project."""
    state = load_project_state_safe(project_name)

    if char_name not in state.characters:
        raise HTTPException(status_code=404, detail=f"Character '{char_name}' not found.")

    primary_char_data = state.characters[char_name]
    # Get roles of other characters
    other_char_roles = [
        char_data.role for name, char_data in state.characters.items()
        if name != char_name and char_data.role
    ]

    if not other_char_roles:
         return {"text": "No other characters defined to suggest relationships with."}


    result_md = character_agent.suggest_relationships(primary_char_data.model_dump(), other_char_roles) # Pass primary char dict

    if "Error:" in result_md:
        raise HTTPException(status_code=500, detail=result_md)

    # Update state and save
    state.characters[char_name].relationship_suggestions = result_md
    save_project_state_safe(state)

    return {"text": result_md}


# --- Screenwriting Endpoints ---
@app.post("/projects/{project_name}/script/generate-outline", response_model=GeneratedTextResponse, summary="Generate script outline", tags=["Screenwriting"])
async def generate_script_outline(project_name: str):
    """Generates a script outline from the project's synopsis."""
    state = load_project_state_safe(project_name)

    synopsis = state.concept.final_synopsis # Use the potentially trimmed synopsis
    if not synopsis:
        # Fallback to logline if no synopsis generated yet
        synopsis = state.concept.chosen_logline

    if not synopsis:
        raise HTTPException(status_code=400, detail="Cannot generate outline without a synopsis or logline.")

    framework = state.concept.chosen_framework

    result_md = script_agent.generate_outline(synopsis, framework)

    if "Error:" in result_md:
        raise HTTPException(status_code=500, detail=result_md)

    # Update state and save
    state.script.outline_md = result_md
    save_project_state_safe(state)

    return {"text": result_md}

@app.post("/projects/{project_name}/script/draft-scene", response_model=GeneratedTextResponse, summary="Draft a scene", tags=["Screenwriting"])
async def draft_scene(project_name: str, request: DraftSceneRequest):
    """Drafts a single scene based on heading, description, and context."""
    # No need to load/save full state for drafting a single scene, it's output for user to copy
    # However, agents might need context from state later (e.g., character list for dialogue cues),
    # so maybe loading state for context is good practice, just don't save the result here.
    # Let's load state to potentially pass character list or other context if agent evolves
    state = load_project_state_safe(project_name)
    # Currently agents don't use full state context for drafting, so just call agent

    result_text = script_agent.draft_scene(
        request.scene_heading,
        request.scene_description,
        request.character_context,
        request.tone
    )

    if "Error:" in result_text:
        raise HTTPException(status_code=500, detail=result_text)

    # Do NOT save this result to project state as it's temporary output
    return {"text": result_text}

@app.put("/projects/{project_name}/script/full-script", response_model=SuccessResponse, summary="Update full script content", tags=["Screenwriting"])
async def update_full_script(project_name: str, request: UpdateScriptContentRequest):
    """Updates the full script content for the project."""
    state = load_project_state_safe(project_name)

    state.script.full_script_content = request.full_script_content
    save_project_state_safe(state)

    return {"message": "Full script content updated successfully."}

@app.post("/projects/{project_name}/script/refine-text", response_model=GeneratedTextResponse, summary="Refine text snippet", tags=["Screenwriting"])
async def refine_text_snippet(project_name: str, request: RefineTextRequest):
    """Refines a text snippet (dialogue or action) based on instruction."""
    # No need to load/save state for refinement, it's output for user to copy
    # Load state potentially for context (e.g., character names for dialogue check)
    state = load_project_state_safe(project_name)

    result_text = "Error: Could not determine refinement type."
    # Basic logic to guess dialogue vs action or rely solely on instruction
    # Let's refine the logic slightly: if instruction mentions 'dialogue' or looks like a tone, use dialogue agent.
    # If instruction mentions 'concise' or 'action', use action agent. Otherwise, use generic.
    instruction_lower = request.instruction.lower()
    # Simple heuristic: check if input contains potential character cue lines? Or just rely on instruction?
    # Relying on instruction is clearer for the API contract.
    if 'dialogue' in instruction_lower or any(tone in instruction_lower for tone in ['tense', 'emotional', 'funny', 'serious']): # Add more tones
         result_text = script_agent.refine_dialogue_tone(request.text_to_refine, request.instruction)
    elif 'concise' in instruction_lower or 'action' in instruction_lower:
         result_text = script_agent.refine_action_conciseness(request.text_to_refine)
    else:
         # Generic fallback - requires a generic call_groq wrapper or agent method
         # For now, let's just use dialogue refine as a generic text refine if unsure
         # TODO: Add a proper generic refine method to ScriptSmithAgent if needed
         result_text = script_agent.refine_dialogue_tone(request.text_to_refine, request.instruction) # Misleading method name for generic refine


    if "Error:" in result_text:
        raise HTTPException(status_code=500, detail=result_text)

    # Do NOT save this result to project state
    return {"text": result_text}

@app.post("/projects/{project_name}/script/analyze-issues", response_model=GeneratedTextResponse, summary="Analyze script issues", tags=["Screenwriting"])
async def analyze_script_issues(project_name: str):
    """Analyzes the last part of the full script content for potential issues."""
    state = load_project_state_safe(project_name)

    script_content = state.script.full_script_content
    if len(script_content) < 50:
        raise HTTPException(status_code=400, detail="Not enough script content to analyze meaningfully (requires at least 50 characters).")

    # Analyze the last 2000 characters, matching Streamlit logic
    excerpt = script_content[-2000:]

    result_md = script_agent.analyze_script_issues(excerpt)

    if "Error:" in result_md:
        raise HTTPException(status_code=500, detail=result_md)

    # Update state and save
    state.script.analysis_md = result_md
    save_project_state_safe(state)

    return {"text": result_md}


# --- Pre-Production Ideas Endpoints ---
@app.post("/projects/{project_name}/preproduction/generate-moodboard-ideas", response_model=GeneratedImageResponse, summary="Generate moodboard ideas and images", tags=["Pre-Production Ideas"])
async def generate_moodboard_ideas_and_images(project_name: str):
    """Generates textual moodboard ideas and corresponding images."""
    state = load_project_state_safe(project_name)

    theme = state.concept.chosen_theme
    genre = state.concept.seed_idea
    synopsis = state.concept.final_synopsis # Use final synopsis if available

    if not theme and not genre and not synopsis:
         raise HTTPException(status_code=400, detail="Provide Theme, Genre (Seed Idea), or Synopsis in the concept phase.")

    # 1. Generate text ideas
    text_result = script_agent.generate_moodboard_ideas(theme, genre, synopsis)

    if "Error:" in text_result:
        # If text generation fails, stop here and raise the error
        raise HTTPException(status_code=500, detail=text_result)
    else:
        # Only proceed to image generation if text ideas were successfully generated
        # 2. Generate images based on the text ideas
        # The Google model often produces multiple images from a single complex prompt.
        # Craft a prompt that asks for a set of images visualizing the moodboard ideas.
        image_generation_prompt = f"Visualize a moodboard for a film concept based on the following ideas:\n---\n{text_result}\n---\nGenerate diverse visual elements for a mood board based on these descriptions."

        # Call the image generation function
        # *** REMOVE num_images=3 *** unless you modified image_generator.py
        image_parts = generate_image_from_prompt(image_generation_prompt)

        if "error" in image_parts: # Image generation failed
             # If image generation fails, raise a different error.
             raise HTTPException(status_code=500, detail=f"Failed to generate images: {image_parts['error']}")

        # Update state and save (only if BOTH text and image generation succeeded)
        state.pre_production.moodboard_ideas_md = text_result # Save the generated text ideas
        state.pre_production.moodboard_images = image_parts # Store the list of parts
        save_project_state_safe(state)

        # Return the generated image parts (which might include text parts from the API)
        return GeneratedImageResponse(parts=image_parts)


@app.post("/projects/{project_name}/preproduction/generate-storyboard-ideas", response_model=GeneratedImageResponse, summary="Generate storyboard shot ideas and images", tags=["Pre-Production Ideas"])
async def generate_storyboard_ideas_and_images(project_name: str, request: GenerateStoryboardRequest):
    """Generates textual storyboard shot ideas and corresponding images for a scene."""
    state = load_project_state_safe(project_name) # Load state maybe for context, but not strictly needed by agent now

    if not request.scene_text.strip():
         raise HTTPException(status_code=400, detail="Please paste scene text.")

    # 1. Generate textual shot ideas
    text_result = script_agent.generate_storyboard_shot_ideas(request.scene_text)

    if "Error:" in text_result:
        # If text generation fails, stop here and raise the error
        raise HTTPException(status_code=500, detail=text_result)
    else:
        # Only proceed to image generation if text ideas were successfully generated
        # 2. Generate images based on the *textual ideas*.
        # The Google GenAI model is good at interpreting descriptions like "Extreme Close-Up: Character's trembling hand".
        # So, feed the generated markdown text for images.
        image_generation_prompt = f"Visualize storyboard shots for a film scene based on these descriptions:\n---\n{text_result}\n---\nGenerate distinct storyboard-style images for each described shot."

        # Call the image generation function
        # *** REMOVE num_images=3 *** unless you modified image_generator.py
        image_parts = generate_image_from_prompt(image_generation_prompt)

        if "error" in image_parts: # Image generation failed
             # If image generation fails, raise a different error.
             raise HTTPException(status_code=500, detail=f"Failed to generate images: {image_parts['error']}")

        # Update state and save (only if BOTH text and image generation succeeded)
        state.pre_production.storyboard_ideas_md = text_result # Save the generated text ideas
        state.pre_production.storyboard_images = image_parts # Store list of parts
        save_project_state_safe(state)

        # Return image data (including potential text parts from Google GenAI)
        return GeneratedImageResponse(parts=image_parts)
@app.post("/generate/comic-image", response_model=GeneratedImageResponse, summary="Generate a comic-style image from a prompt", tags=["Image Generation"])
async def generate_comic_image(request: ComicPromptRequest):
    """Generates a comic-style image based on a text prompt."""
    if not config.GOOGLE_API_KEY:
         logger.error("Google GenAI API key not configured. Cannot generate images.")
         raise HTTPException(status_code=500, detail="Image generation API key not configured.")

    # Craft the prompt, adding style hints
    image_generation_prompt = f"{request.prompt}" + """
Explain the concept using a fun, kid-friendly story filled with lots of characters.  
Make each sentence short, simple, and playful — like you're telling a bedtime story.  
Keep the tone cheerful, curious, and easy for kids to understand.  
For every sentence, create a cute, colorful ink illustration that matches the story.  
No extra explanations — just start the story and keep going until the concept is clear through the animal adventure."""

    logger.info(f"Generating comic image for prompt: '{image_generation_prompt[:100]}...'")

    image_parts = generate_image_from_prompt(image_generation_prompt)

    if "error" in image_parts:
         logger.error(f"Image generation failed: {image_parts['error']}")
         raise HTTPException(status_code=500, detail=f"Failed to generate image: {image_parts['error']}")

    logger.info("Comic image generation successful.")
    # Note: This endpoint does NOT interact with project state.
    return GeneratedImageResponse(parts=image_parts)

# --- API Key Check (Startup) ---
@app.on_event("startup")
async def startup_event():
    if not config.GROQ_API_KEY:
        logger.error("GROQ_API_KEY environment variable not set. Groq API calls will fail.")
    if not config.GOOGLE_API_KEY:
        logger.error("GOOGLE_API_KEY environment variable not set. Google GenAI (Image generation) calls will fail.")
    logger.info("FilmForge AI Assistant API started.")

# --- Example Usage (How to run this API) ---
# Save this file as api.py
# Install necessary libraries: pip install fastapi uvicorn python-dotenv groq google-generativeai pydantic pillow
# Run from your terminal in the project directory:
# uvicorn api:app --reload
# The API documentation will be available at http://127.0.0.1:8000/docs