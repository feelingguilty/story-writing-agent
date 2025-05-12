# streamlit_app.py
import streamlit as st
import requests
import json
import base64
import io
from PIL import Image
from datetime import datetime # Used for displaying timestamps
import logging

# Configure basic logging for the Streamlit app (optional, for debugging server-side)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Configuration ---
# IMPORTANT: Replace with your FastAPI server URL if it's not running locally
API_BASE_URL = "http://127.0.0.1:8000" # Default local development URL

# --- Helper Functions for API Interaction ---

def call_api(method: str, endpoint: str, json_data: dict = None):
    """Generic helper to call the FastAPI backend."""
    # Ensure endpoint starts with a slash if not already
    formatted_endpoint = endpoint if endpoint.startswith('/') else '/' + endpoint
    url = f"{API_BASE_URL}{formatted_endpoint}"
    try:
        logger.info(f"Calling API: {method} {url}")
        response = requests.request(method, url, json=json_data)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        logger.info(f"API call successful: {method} {url}")
        return response.json()
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response else 'Unknown'
        error_message = f"API Error ({status_code}): {e}"
        logger.error(error_message, exc_info=True) # Log the full exception

        # Attempt to extract detailed error message from FastAPI response body
        detail = "No additional detail from API."
        if e.response and e.response.content:
            try:
                response_json = e.response.json()
                detail = response_json.get("detail", detail)
            except json.JSONDecodeError:
                # If not JSON, just show the text response
                detail = f"API returned non-JSON error: {e.response.text[:200]}..."
            except Exception as parse_e:
                 detail = f"Failed to parse API error details: {parse_e}"


        st.error(f"API Request Failed: {error_message}", icon="🚨")
        if detail and detail != "No additional detail from API.": # Only show detail if we got something specific
             st.error(f"Details: {detail}")

        return {"error": error_message, "detail": detail}
    except Exception as e:
        unexpected_error_msg = f"An unexpected error occurred during API call: {e}"
        logger.error(unexpected_error_msg, exc_info=True) # Log the full exception
        st.error(unexpected_error_msg, icon="🚨")
        return {"error": unexpected_error_msg}


def get_projects():
    """Fetches the list of projects from the API."""
    response_data = call_api("GET", "/projects")
    if "error" not in response_data:
        return response_data.get("projects", [])
    return [] # Return empty list on error or if 'projects' key is missing


def load_project_api(project_name: str):
    """Loads a project state from the API."""
    response_data = call_api("GET", f"/projects/{project_name}")
    if "error" not in response_data:
        st.session_state.project_state = response_data # Store the full state from API
        st.session_state.active_char_for_display = None # Reset selected char on load
        # Also clear temporary AI outputs from Pro mode
        st.session_state.temp_drafted_scene = ""
        st.session_state.temp_refined_text = ""
        st.session_state.temp_profile_suggestions = ""
        # Ensure pre_production images are loaded (they are part of state)
        st.session_state.project_state['pre_production'] = st.session_state.project_state.get('pre_production', {}) # Ensure dict exists
        st.session_state.project_state['pre_production']['moodboard_images'] = st.session_state.project_state['pre_production'].get('moodboard_images', [])
        st.session_state.project_state['pre_production']['storyboard_images'] = st.session_state.project_state['pre_production'].get('storyboard_images', [])

        st.success(f"Project '{project_name}' loaded from API.")
        st.rerun() # Rerun to update UI based on loaded state
    # Error message is displayed by call_api


def create_project_api(new_project_name: str):
    """Creates a new project via the API."""
    response_data = call_api("POST", "/projects", json_data={"project_name": new_project_name})
    if "error" not in response_data:
        st.session_state.project_state = response_data # API returns the initial state
        st.session_state.active_char_for_display = None # Reset selected char on create
         # Also clear temporary AI outputs from Pro mode
        st.session_state.temp_drafted_scene = ""
        st.session_state.temp_refined_text = ""
        st.session_state.temp_profile_suggestions = ""
        # Initialize pre_production images lists
        st.session_state.project_state['pre_production'] = st.session_state.project_state.get('pre_production', {}) # Ensure dict exists
        st.session_state.project_state['pre_production']['moodboard_images'] = []
        st.session_state.project_state['pre_production']['storyboard_images'] = []


        st.success(f"New project '{new_project_name}' created via API.")
        st.session_state.ti_new_project_name_ui = "" # Clear the input field by updating its key in state
        st.rerun() # Rerun to update project list and UI
    # Error message is displayed by call_api


def save_project_api():
    """Saves the current project state via the API."""
    if 'project_state' not in st.session_state or st.session_state.project_state.get("project_name") in ["Untitled", None]:
        st.warning("Cannot save an unnamed project. Load or create a project first.")
        return

    project_name = st.session_state.project_state["project_name"]
    # Send the *entire* current state from session_state to the API
    # The API saves the state, including updating the log and last_saved timestamp.
    state_to_save = st.session_state.project_state
    response_data = call_api("PUT", f"/projects/{project_name}", json_data=state_to_save)

    if "error" not in response_data:
        # API returns the state with updated save time and log
        st.session_state.project_state = response_data # Update local state with latest from API
        st.success(f"Project '{project_name}' saved via API!")
        # No explicit rerun needed, success message display implies it happens


# --- Initialize Session State ---
# This state is CLIENT-SIDE state, reflecting what's loaded from the API
if 'project_state' not in st.session_state:
    logger.info("Initializing Streamlit Session State: project_state")
    # Start with a default placeholder state reflecting nothing is loaded
    st.session_state.project_state = {
        "project_name": "Untitled",
        "cleaned_name": "untitled",
        "current_phase": "Concept", # Can track which tab the user was on, though not strictly necessary for state
        "concept": {}, # Placeholder, API load will fill this
        "characters": {},
        "script": {},
        "pre_production": { "moodboard_images": [], "storyboard_images": [] }, # Initialize image lists
        "last_saved": None,
        "log": ["UI initialized. Connect to backend API."]
    }

if 'active_char_for_display' not in st.session_state:
    logger.info("Initializing Streamlit Session State: active_char_for_display")
    st.session_state.active_char_for_display = None # Track selected char for display in UI

# Temporary storage for AI outputs that aren't part of persistent project state (Pro mode)
if 'temp_drafted_scene' not in st.session_state:
    logger.info("Initializing Streamlit Session State: temp_drafted_scene")
    st.session_state.temp_drafted_scene = ""

if 'temp_refined_text' not in st.session_state:
    logger.info("Initializing Streamlit Session State: temp_refined_text")
    st.session_state.temp_refined_text = ""

if 'temp_profile_suggestions' not in st.session_state:
    logger.info("Initializing Streamlit Session State: temp_profile_suggestions")
    st.session_state.temp_profile_suggestions = ""

# Flag to signal clearing the storyboard input text area on the next rerun
if 'clear_sb_input_flag' not in st.session_state:
     logger.info("Initializing Streamlit Session State: clear_sb_input_flag")
     st.session_state.clear_sb_input_flag = False

# --- New Session State for Kids Mode ---
if 'mode' not in st.session_state:
    logger.info("Initializing Streamlit Session State: mode")
    st.session_state.mode = "Pro" # Default mode

if 'kids_prompt_ui' not in st.session_state:
     logger.info("Initializing Streamlit Session State: kids_prompt_ui")
     st.session_state.kids_prompt_ui = ""

if 'kids_image_parts' not in st.session_state:
    logger.info("Initializing Streamlit Session State: kids_image_parts")
    st.session_state.kids_image_parts = [] # Stores the list of image/text parts from the API response


# --- Helper to get current project state (from session state) ---
def get_state():
     # Always work with the client's view of the project state from session_state
     return st.session_state.project_state

# --- UI Layout ---

st.set_page_config(layout="wide", page_title="FilmForge AI")
st.title("🎬 FilmForge AI Engine")
st.caption(f"Connected to backend at: {API_BASE_URL}")


# --- Sidebar ---
with st.sidebar:
    st.header("Mode Selection")
    selected_mode = st.radio(
        "Choose Mode",
        options=["Pro Mode", "Kids Mode"],
        index=0 if st.session_state.mode == "Pro" else 1,
        key="mode_select_ui" # Unique key
    )
    # Update session state if the mode changes via radio button
    if selected_mode == "Pro Mode" and st.session_state.mode != "Pro":
        st.session_state.mode = "Pro"
        st.rerun() # Rerun to switch mode
    elif selected_mode == "Kids Mode" and st.session_state.mode != "Kids":
        st.session_state.mode = "Kids"
        st.rerun() # Rerun to switch mode

    st.divider()

    # Project Management section is only shown in Pro Mode
    if st.session_state.mode == "Pro":
        st.header("Project Management")

        # Load Project
        projects = get_projects() # Fetch list from API
        current_project_name = get_state().get("project_name", "Untitled")

        # Determine current index for selectbox default
        try:
            current_project_index = projects.index(current_project_name) if current_project_name != "Untitled" and current_project_name in projects else None
        except ValueError:
             current_project_index = None # Handle case where current project might not be in the list


        selected_project = st.selectbox(
            "Load Existing Project",
            options=projects,
            index=current_project_index,
            placeholder="Select project...",
            key="sb_load_project_ui" # Use a unique key for the widget
        )

        if st.button("Load Project", key="btn_load_ui", disabled=(selected_project is None)):
            if selected_project:
                load_project_api(selected_project)


        st.divider()

        # Create New Project
        new_proj_name = st.text_input("New Project Name", key="ti_new_project_name_ui") # Use a unique key
        if st.button("Create New Project", key="btn_create_ui"): # Use a unique key
            if new_proj_name:
                create_project_api(new_proj_name)
            else:
                st.warning("Please enter a name for the new project.")

        st.divider()

        # Save Project
        # Button is only enabled if a project is loaded (not "Untitled")
        if st.button("Save Current Project", key="btn_save_ui", disabled=(get_state().get("project_name") == "Untitled")): # Use a unique key
            save_project_api()

        st.divider()
        st.write(f"**Current Project:** {get_state().get('project_name', 'Untitled')}")
        last_saved = get_state().get('last_saved')
        if last_saved:
            try:
                # Parse ISO format string
                saved_dt = datetime.fromisoformat(last_saved)
                st.caption(f"Last Saved: {saved_dt.strftime('%Y-%m-%d %H:%M:%S')}")
            except (ValueError, TypeError): # Handle potential errors if last_saved format is unexpected
                st.caption(f"Last Saved: {last_saved}") # Display raw string if parsing fails
        else:
             st.caption("Not saved yet.")


# --- Main Content Area ---

# Conditional rendering based on mode
if st.session_state.mode == "Kids":
    # --- Kids Mode UI ---
    st.header("🎨 FilmForge Kids' Comic Creator!")
    st.markdown("Type what you want to see in a comic picture!")

    # Use key to bind input to session state
    kids_prompt = st.text_input("Tell me what to draw (e.g., 'A superhero flying over a city', 'A friendly monster eating a cookie')", key="kids_prompt_ui")

    # Button to trigger image generation
    if st.button("Generate Comic Image!", key="btn_kids_generate_ui"): # Unique key
        prompt_val = st.session_state.kids_prompt_ui # Read value via key

        if prompt_val.strip():
            st.info(f"Generating comic image for: '{prompt_val}'...")
            # Call the NEW API endpoint for comic image generation
            response_data = call_api("POST", "/generate/comic-image", json_data={"prompt": prompt_val})

            if "error" not in response_data:
                # API returns a list of parts (image/text)
                st.session_state.kids_image_parts = response_data.get("parts", [])
                st.success("Comic image generated!")
                st.rerun() # Rerun to display the images
            # Error is handled and displayed by call_api
        else:
            st.warning("Please enter a prompt to generate a comic image.")

    st.markdown("---")

    # Display generated images and text parts
    if st.session_state.kids_image_parts:
        st.subheader("Generated Comic:")
        for i, part in enumerate(st.session_state.kids_image_parts):
             if part.get("type", "").startswith("image/"):
                 try:
                     img_bytes = base64.b64decode(part.get("content"))
                     img = Image.open(io.BytesIO(img_bytes))
                     # Optional: Resize images for consistency if needed
                     # img.thumbnail((800, 800))
                     st.image(img, caption=f"Part {i+1}", use_column_width=True)
                 except Exception as e:
                     st.warning(f"Failed to display image part {i+1}: {e}")
             elif part.get("type") == "text":
                 st.write(f"**Text Part {i+1}:**")
                 st.markdown(part.get("content")) # Use markdown for potential formatting
             elif part.get("type") == "error":
                 st.error(f"Image generation part {i+1} failed: {part.get('content')}")
             else:
                 st.warning(f"Skipping unknown part type: {part.get('type')}")


else: # st.session_state.mode == "Pro"
    # --- Pro Mode UI (Existing Tabs) ---
    tab_titles = [
        "1. Concept Development",
        "2. Character Development",
        "3. Screenwriting",
        "4. Pre-Production Ideas",
        "Log"
    ]
    tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_titles) # Unique keys implicitly generated by order/labels

    # Ensure we have a loaded project before displaying most tabs' content in Pro mode
    if get_state().get("project_name") == "Untitled":
        st.info("Please load or create a project using the sidebar to begin.")
    else:
        # --- Tab 1: Concept Development ---
        with tab1:
            st.header("Concept Development")
            st.markdown("Define the core idea of your film.")

            current_concept_state = get_state().get("concept", {}) # Get the concept state from loaded project

            seed_idea = st.text_area(
                "Seed Idea (Genre, Theme, Logline, Keywords)",
                value=current_concept_state.get("seed_idea", ""),
                key="concept_seed_idea_ta_ui" # Unique key for UI element
            )

            if st.button("Generate Initial Concepts", key="btn_gen_concepts_ui"): # Unique key
                seed_idea_val = st.session_state.concept_seed_idea_ta_ui

                if seed_idea_val:
                    st.info("Generating initial concepts via API...")
                    response_data = call_api("POST", f"/projects/{get_state()['project_name']}/concept/generate-concepts", json_data={"seed_idea": seed_idea_val})
                    if "error" not in response_data:
                        if "concept" in st.session_state.project_state:
                            st.session_state.project_state["concept"]["generated_concepts_md"] = response_data.get("text", "")
                            st.success("Concepts generated and saved.")
                            st.rerun()
                        else:
                            st.error("API returned success but concept state not found locally.")
                else:
                    st.warning("Please enter a seed idea.")

            st.markdown("---")
            st.markdown("**Generated Concepts:**")
            st.markdown(get_state().get("concept", {}).get("generated_concepts_md", "*No concepts generated yet.*"))
            st.markdown("---")

            st.subheader("Refine Your Concept")
            col1, col2 = st.columns(2)
            with col1:
                logline = st.text_input(
                    "Chosen Logline",
                    value=current_concept_state.get("chosen_logline", ""),
                    key="concept_logline_ui" # Unique key
                )

                theme = st.text_input(
                    "Chosen Theme",
                    value=current_concept_state.get("chosen_theme", ""),
                    key="concept_theme_ui" # Unique key
                )
            with col2:
                framework = st.text_input(
                    "Chosen Narrative Framework",
                     value=current_concept_state.get("chosen_framework", "Three-Act Structure"),
                     key="concept_framework_ui" # Unique key
                )

                conflict = st.text_input(
                    "Chosen Central Conflict",
                    value=current_concept_state.get("chosen_conflict", ""),
                    key="concept_conflict_ui" # Unique key
                )

            if st.button("Generate Synopsis & Twists", key="btn_gen_synopsis_ui"): # Unique key
                logline_val = st.session_state.concept_logline_ui
                theme_val = st.session_state.concept_theme_ui
                framework_val = st.session_state.concept_framework_ui
                conflict_val = st.session_state.concept_conflict_ui

                concept_details_payload = {}
                if logline_val: concept_details_payload['logline'] = logline_val
                if framework_val: concept_details_payload['framework'] = framework_val
                if theme_val: concept_details_payload['theme'] = theme_val
                if conflict_val: concept_details_payload['conflict'] = conflict_val


                if logline_val or theme_val or get_state().get("concept", {}).get("chosen_logline") or get_state().get("concept", {}).get("chosen_theme"):
                    st.info("Generating synopsis via API...")
                    response_data = call_api("POST", f"/projects/{get_state()['project_name']}/concept/generate-synopsis", json_data=concept_details_payload)

                    if "error" not in response_data:
                         if "concept" in st.session_state.project_state:
                             if 'logline' in concept_details_payload: st.session_state.project_state["concept"]["chosen_logline"] = concept_details_payload['logline']
                             if 'framework' in concept_details_payload: st.session_state.project_state["concept"]["chosen_framework"] = concept_details_payload['framework']
                             if 'theme' in concept_details_payload: st.session_state.project_state["concept"]["chosen_theme"] = concept_details_payload['theme']
                             if 'conflict' in concept_details_payload: st.session_state.project_state["concept"]["chosen_conflict"] = concept_details_payload['conflict']

                             st.session_state.project_state["concept"]["synopsis_md"] = response_data.get("text", "")
                             final_synopsis = response_data.get("text", "").split("### Potential Twists")[0].strip() if "### Potential Twists" in response_data.get("text", "") else response_data.get("text", "")
                             st.session_state.project_state["concept"]["final_synopsis"] = final_synopsis

                             st.success("Synopsis generated and saved.")
                             st.rerun()
                         else:
                              st.error("API returned success but concept state not found locally.")

                else:
                    st.warning("Please provide at least a Logline or Theme.")

            st.markdown("**Generated Synopsis & Twists:**")
            st.markdown(get_state().get("concept", {}).get("synopsis_md", "*No synopsis generated yet.*"))


        # --- Tab 2: Character Development ---
        with tab2:
            st.header("Character Development")
            st.markdown("Develop your characters.")

            state_chars = get_state().get("characters", {}) # Get the characters state from loaded project
            char_names = list(state_chars.keys())

            col1, col2 = st.columns([1, 2]) # Adjust column ratios as needed

            with col1:
                st.subheader("Add/Edit Character")
                # Use keys to bind inputs to session state
                char_name_input = st.text_input("Character Name", key="char_name_input_ui")
                char_role_input = st.text_input("Character Role", placeholder="e.g., Protagonist", key="char_role_input_ui")

                # Attempt to pre-fill profile fields if editing an existing character selected in col2
                active_char_name = st.session_state.active_char_for_display
                if active_char_name and active_char_name in state_chars:
                     active_char_data = state_chars[active_char_name]
                     # Set the session state values bound to the input field keys
                     st.session_state.char_name_input_ui = active_char_name
                     st.session_state.char_role_input_ui = active_char_data.get("role", "")
                     active_profile = active_char_data.get("profile", {})
                     st.session_state.char_backstory_ui = active_profile.get("backstory", "")
                     st.session_state.char_motivation_ui = active_profile.get("motivation", "")
                     st.session_state.char_flaw_ui = active_profile.get("flaw", "")
                # Note: If the user changes char_name_input_ui, the link to active_char_for_display is broken
                # for pre-filling, which is the desired behavior (they are now defining a *new* character).

                if st.button("Suggest Profile Elements", key="btn_suggest_profile_ui"): # Unique key
                    # Use values from the text inputs (synced by keys)
                    name_val = st.session_state.char_name_input_ui
                    role_val = st.session_state.char_role_input_ui

                    if name_val and role_val:
                        st.info(f"Generating profile ideas for {name_val} via API...")
                        genre = get_state().get("concept", {}).get("seed_idea", "Unknown Genre")
                        theme = get_state().get("concept", {}).get("chosen_theme", "General Theme")

                        response_data = call_api("POST", f"/projects/{get_state()['project_name']}/characters/suggest-profile", json_data={"role": role_val, "genre": genre, "theme": theme})

                        if "error" not in response_data:
                            st.session_state.temp_profile_suggestions = response_data.get("text", "")
                            st.success("Profile suggestions generated.")
                    else:
                        st.warning("Please enter Character Name and Role.")

                # Display temporary suggestions if they exist
                if st.session_state.temp_profile_suggestions:
                     with st.expander("Show/Hide Profile Suggestions", expanded=True):
                          st.markdown(st.session_state.temp_profile_suggestions)


                st.markdown("**Define Character Profile:**")
                # Use keys to sync these text areas to session state
                backstory = st.text_area("Chosen Backstory", key="char_backstory_ui")
                motivation = st.text_area("Chosen Motivation", key="char_motivation_ui")
                flaw = st.text_area("Chosen Flaw", key="char_flaw_ui")


                if st.button("Save/Update Character Profile", key="btn_save_char_ui"): # Unique key
                     # Read values from session state via keys
                     name_val = st.session_state.char_name_input_ui
                     role_val = st.session_state.char_role_input_ui
                     backstory_val = st.session_state.char_backstory_ui
                     motivation_val = st.session_state.char_motivation_ui
                     flaw_val = st.session_state.char_flaw_ui

                     if name_val and role_val:
                          st.info(f"Saving/Updating character '{name_val}' profile via API...")
                          profile_data = {
                              "role": role_val,
                              "profile": {
                                  "backstory": backstory_val,
                                  "motivation": motivation_val,
                                  "flaw": flaw_val
                              }
                          }
                          response_data = call_api("PUT", f"/projects/{get_state()['project_name']}/characters/{name_val}", json_data=profile_data)

                          if "error" not in response_data:
                               if "characters" not in st.session_state.project_state: st.session_state.project_state["characters"] = {}
                               st.session_state.project_state["characters"][name_val] = response_data
                               st.success(f"Character '{name_val}' profile saved via API.")
                               st.session_state.temp_profile_suggestions = ""
                               st.session_state.active_char_for_display = name_val
                               st.rerun()
                     else:
                          st.warning("Please enter Character Name and Role.")

            with col2:
                st.subheader("Explore Arcs & Relationships")
                current_char_names = list(get_state().get("characters", {}).keys())
                char_options = ["Select a character..."] + current_char_names

                try:
                     current_char_index = char_options.index(st.session_state.active_char_for_display) if st.session_state.active_char_for_display in char_options else 0
                except ValueError:
                     current_char_index = 0


                selected_char_for_arc = st.selectbox(
                     "Select Character",
                     options=char_options,
                     index=current_char_index,
                     key="char_select_arc_ui" # Unique key
                )

                if selected_char_for_arc != "Select a character..." and selected_char_for_arc != st.session_state.active_char_for_display:
                     st.session_state.active_char_for_display = selected_char_for_arc
                     st.rerun()

                active_char_data_for_display = get_state().get("characters", {}).get(st.session_state.active_char_for_display, {})

                st.markdown("**Character Arc:**")
                can_generate_arc = (
                    st.session_state.active_char_for_display
                    and st.session_state.active_char_for_display in get_state().get("characters", {})
                    and get_state()["characters"].get(st.session_state.active_char_for_display, {}).get("profile", {}).get("motivation")
                    and get_state()["characters"].get(st.session_state.active_char_for_display, {}).get("profile", {}).get("flaw")
                )
                if st.button("Generate Character Arc", key="btn_gen_arc_ui", disabled=(not can_generate_arc)): # Unique key
                    char_name_active = st.session_state.active_char_for_display
                    st.info(f"Generating arc for {char_name_active} via API...")
                    response_data = call_api("POST", f"/projects/{get_state()['project_name']}/characters/{char_name_active}/generate-arc")

                    if "error" not in response_data:
                        if "characters" in st.session_state.project_state and char_name_active in st.session_state.project_state["characters"]:
                            st.session_state.project_state["characters"][char_name_active]["arc_description"] = response_data.get("text", "")
                            st.success(f"Arc generated for {char_name_active}.")
                            st.rerun()
                        else:
                            st.error(f"API returned success but character '{char_name_active}' state not found locally after update attempt.")


                arc_desc = active_char_data_for_display.get("arc_description", "*No arc generated yet.*")
                st.markdown(arc_desc)
                st.markdown("---")

                st.markdown("**Relationship Suggestions:**")
                can_suggest_rels = (
                     st.session_state.active_char_for_display
                     and st.session_state.active_char_for_display in get_state().get("characters", {})
                     and len(get_state().get("characters", {})) > 1
                )
                if st.button("Suggest Relationships", key="btn_gen_rels_ui", disabled=(not can_suggest_rels)): # Unique key
                    char_name_active = st.session_state.active_char_for_display
                    st.info(f"Generating relationship suggestions for {char_name_active} via API...")
                    response_data = call_api("POST", f"/projects/{get_state()['project_name']}/characters/{char_name_active}/suggest-relationships")

                    if "error" not in response_data:
                         if "characters" in st.session_state.project_state and char_name_active in st.session_state.project_state["characters"]:
                             st.session_state.project_state["characters"][char_name_active]["relationship_suggestions"] = response_data.get("text", "")
                             st.success(f"Relationship suggestions generated for {char_name_active}.")
                             st.rerun()
                         else:
                              st.error(f"API returned success but character '{char_name_active}' state not found locally after update attempt.")


                rel_sugg = active_char_data_for_display.get("relationship_suggestions", "*No relationship suggestions generated yet.*")
                st.markdown(rel_sugg)


        # --- Tab 3: Screenwriting ---
        with tab3:
            st.header("Screenwriting")
            st.markdown("Write your screenplay.")

            current_script_state = get_state().get("script", {})

            col1, col2 = st.columns(2)
            with col1:
                can_generate_outline = (
                     get_state().get("concept", {}).get("final_synopsis")
                     or get_state().get("concept", {}).get("chosen_logline")
                )
                if st.button("Generate Outline from Synopsis", key="btn_gen_outline_ui", disabled=(not can_generate_outline)): # Unique key
                    st.info("Generating script outline via API...")
                    response_data = call_api("POST", f"/projects/{get_state()['project_name']}/script/generate-outline")

                    if "error" not in response_data:
                        if "script" in st.session_state.project_state:
                             st.session_state.project_state["script"]["outline_md"] = response_data.get("text", "")
                             st.success("Outline generated.")
                             st.rerun()
                        else:
                             st.error("API returned success but script state not found locally.")

                st.markdown("**Generated Outline:**")
                st.markdown(current_script_state.get("outline_md", "*No outline generated yet.*"))

            with col2:
                st.subheader("Draft Scene")
                scene_heading = st.text_input("Scene Heading", placeholder="INT. LOCATION - DAY/NIGHT", key="scene_head_ui") # Unique key
                scene_desc = st.text_area("Scene Description/Goal", key="scene_desc_ui") # Unique key
                scene_context = st.text_input("Character Context (Optional)", key="scene_context_ui") # Unique key
                scene_tone = st.text_input("Scene Tone (Optional)", key="scene_tone_ui") # Unique key


                if st.button("Draft Scene", key="btn_draft_scene_ui"): # Unique key
                     heading_val = st.session_state.scene_head_ui
                     desc_val = st.session_state.scene_desc_ui
                     context_val = st.session_state.scene_context_ui
                     tone_val = st.session_state.scene_tone_ui

                     if heading_val and desc_val:
                          st.info(f"Drafting scene '{heading_val}' via API...")
                          draft_request_data = {
                              "scene_heading": heading_val,
                              "scene_description": desc_val,
                              "character_context": context_val,
                              "tone": tone_val
                          }
                          response_data = call_api("POST", f"/projects/{get_state()['project_name']}/script/draft-scene", json_data=draft_request_data)

                          if "error" not in response_data:
                               st.session_state.temp_drafted_scene = response_data.get("text", "")
                               st.success("Scene drafted.")
                               st.rerun()
                     else:
                          st.warning("Scene Heading and Description are required.")

                st.text_area(
                    "Drafted Scene Output",
                    value=st.session_state.temp_drafted_scene,
                    height=200,
                    key="drafted_scene_disp_ui", # Unique key
                    help="Copy from here",
                    disabled=True
                )


            st.markdown("---")
            st.subheader("Full Script Draft")

            full_script_content = st.text_area(
                "Script Content (.fountain format recommended)",
                value=current_script_state.get("full_script_content", ""),
                height=600,
                key="script_editor_main_ui"
            )

            if st.button("Save Full Script Content", key="btn_save_full_script_ui"): # Unique key
                 st.info("Saving full script content via API...")
                 script_to_save = st.session_state.script_editor_main_ui
                 response_data = call_api("PUT", f"/projects/{get_state()['project_name']}/script/full-script", json_data={"full_script_content": script_to_save})
                 if "error" not in response_data:
                      st.session_state.project_state["script"]["full_script_content"] = script_to_save
                      st.success("Full script content saved.")

            col_refine, col_analyze = st.columns(2)
            with col_refine:
                st.markdown("**Refine Text:**")
                text_to_refine = st.text_area("Paste Dialogue or Action Line to Refine", height=100, key="refine_input_text_ui") # Unique key
                refine_instruction = st.text_input("Refinement Instruction", placeholder="e.g., 'Make dialogue tense' or 'Make action concise'", key="refine_instr_ui") # Unique key

                if st.button("Refine Text", key="btn_refine_ui"): # Unique key
                     refine_text_val = st.session_state.refine_input_text_ui
                     instruction_val = st.session_state.refine_instr_ui

                     if refine_text_val and instruction_val:
                         st.info("Refining text via API...")
                         refine_request_data = {
                             "text_to_refine": refine_text_val,
                             "instruction": instruction_val
                         }
                         response_data = call_api("POST", f"/projects/{get_state()['project_name']}/script/refine-text", json_data=refine_request_data)

                         if "error" not in response_data:
                              st.session_state.temp_refined_text = response_data.get("text", "")
                              st.success("Text refined.")
                              st.rerun()
                     else:
                         st.warning("Text and instruction required for refinement.")

                st.text_area(
                    "Refined Text Output",
                    value=st.session_state.temp_refined_text,
                    height=100,
                    key="refined_text_disp_ui", # Unique key
                    help="Copy from here",
                    disabled=True
                )

            with col_analyze:
                st.markdown("**Analyze Script Issues:**")
                can_analyze = len(get_state().get("script", {}).get("full_script_content", "")) >= 50
                if st.button("Analyze Script Issues (Last ~2000 Chars)", key="btn_analyze_ui", disabled=(not can_analyze)): # Unique key
                    st.info("Analyzing script via API...")
                    response_data = call_api("POST", f"/projects/{get_state()['project_name']}/script/analyze-issues")

                    if "error" not in response_data:
                        if "script" in st.session_state.project_state:
                             st.session_state.project_state["script"]["analysis_md"] = response_data.get("text", "")
                             st.success("Script analysis complete.")
                             st.rerun()
                        else:
                             st.error("API returned success but script state not found locally.")

                st.markdown(current_script_state.get("analysis_md", "*No analysis performed yet.*"))

        # --- Tab 4: Pre-Production Ideas ---
        with tab4:
            st.header("Pre-Production Ideas")
            st.markdown("Generate visual ideas based on your script and concept.")

            current_preprod_state = get_state().get("pre_production", {})

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Moodboard Ideas")
                can_generate_moodboard = (
                     get_state().get("concept", {}).get("chosen_theme")
                     or get_state().get("concept", {}).get("seed_idea")
                     or get_state().get("concept", {}).get("final_synopsis")
                )
                if st.button("Generate Moodboard Ideas", key="btn_gen_mood_ui", disabled=(not can_generate_moodboard)): # Unique key
                    st.info("Generating moodboard ideas and images via API...")
                    response_data = call_api("POST", f"/projects/{get_state()['project_name']}/preproduction/generate-moodboard-ideas")

                    if "error" not in response_data:
                         if "pre_production" in st.session_state.project_state:
                            # The API saves state (text ideas and images), but returns only the image parts.
                            # We need to re-fetch the state to get the updated text ideas markdown and ensure images are fully synced.
                            # Update images immediately for responsiveness
                            st.session_state.project_state["pre_production"]["moodboard_images"] = response_data.get("parts", [])
                            st.success("Moodboard ideas generated.")
                            load_project_api(get_state()['project_name']) # Re-load state to get latest text ideas and trigger rerun
                         else:
                              st.error("API returned success but pre_production state not found locally.")


                st.markdown("**Generated Moodboard Text Ideas:**")
                st.markdown(current_preprod_state.get("moodboard_ideas_md", "*No moodboard text ideas generated yet.*"))

                # Display generated images
                moodboard_image_parts = current_preprod_state.get("moodboard_images", [])
                if moodboard_image_parts:
                    st.markdown("**Generated Moodboard Images:**")
                    for i, part in enumerate(moodboard_image_parts):
                        if part.get("type", "").startswith("image/"):
                            try:
                                img_bytes = base64.b64decode(part.get("content"))
                                img = Image.open(io.BytesIO(img_bytes))
                                st.image(img, caption=f"Image {i+1}", use_column_width=True) # Added caption
                            except Exception as e:
                                st.warning(f"Failed to display image part {i+1}: {e}")
                        elif part.get("type") == "text":
                            st.write(f"**Text Part {i+1}:**")
                            st.markdown(part.get("content"))
                        elif part.get("type") == "error":
                            st.error(f"Image generation part {i+1} failed: {part.get('content')}")
                        else:
                            st.warning(f"Skipping unknown part type {i+1}: {part.get('type')}")


            with col2:
                st.subheader("Storyboard Shot Ideas")

                # FIX: Clear input text area using flag
                if st.session_state.clear_sb_input_flag:
                    st.session_state.sb_scene_input_ui = "" # Clear the value tied to the key
                    st.session_state.clear_sb_input_flag = False # Reset the flag

                scene_text_for_sb = st.text_area(
                    "Paste Scene Text Here",
                    value=st.session_state.get("sb_scene_input_ui", ""), # Use .get for safe initial read
                    height=200,
                    key="sb_scene_input_ui" # Unique key
                )
                # END FIX

                can_generate_storyboard = len(st.session_state.get("sb_scene_input_ui", "").strip()) >= 50 # Needs sufficient length
                if st.button("Generate Storyboard Ideas", key="btn_gen_sb_ui", disabled=(not can_generate_storyboard)): # Unique key
                    scene_text_val = st.session_state.sb_scene_input_ui # Read value via key

                    if scene_text_val.strip():
                        st.info("Generating storyboard ideas and images via API...")
                        response_data = call_api("POST", f"/projects/{get_state()['project_name']}/preproduction/generate-storyboard-ideas", json_data={"scene_text": scene_text_val})

                        if "error" not in response_data:
                             if "pre_production" in st.session_state.project_state:
                                 # API saves state (text ideas and images), but returns only the image parts.
                                 # We need to re-fetch the state to get the updated text ideas markdown and ensure images are fully synced.
                                 # Update images immediately for responsiveness
                                 st.session_state.project_state["pre_production"]["storyboard_images"] = response_data.get("parts", [])
                                 st.success("Storyboard ideas generated.")
                                 # Set the clearing flag instead of writing directly
                                 st.session_state.clear_sb_input_flag = True
                                 load_project_api(get_state()['project_name']) # Re-load state to get latest text ideas and trigger rerun
                             else:
                                  st.error("API returned success but pre_production state not found locally.")

                    else:
                        st.warning("Please paste scene text.")

                st.markdown("**Generated Storyboard Text Ideas:**")
                st.markdown(current_preprod_state.get("storyboard_ideas_md", "*No storyboard text ideas generated yet.*"))

                # Display generated images
                storyboard_image_parts = current_preprod_state.get("storyboard_images", [])
                if storyboard_image_parts:
                    st.markdown("**Generated Storyboard Images:**")
                    for i, part in enumerate(storyboard_image_parts):
                        if part.get("type", "").startswith("image/"):
                            try:
                                img_bytes = base64.b64decode(part.get("content"))
                                img = Image.open(io.BytesIO(img_bytes))
                                st.image(img, caption=f"Image {i+1}", use_column_width=True) # Added caption
                            except Exception as e:
                                st.warning(f"Failed to display image part {i+1}: {e}")
                        elif part.get("type") == "text":
                            st.write(f"**Text Part {i+1}:**")
                            st.markdown(part.get("content"))
                        elif part.get("type") == "error":
                            st.error(f"Image generation part {i+1} failed: {part.get('content')}")
                        else:
                            st.warning(f"Skipping unknown part type {i+1}: {part.get('type')}")


        # --- Tab 5: Log ---
        with tab5:
            st.header("Action Log")
            log_content = "\n".join(get_state().get("log", ["Log is empty."]))
            st.text_area("Log", value=log_content, height=600, disabled=True, key="log_display_area_ui") # Unique key

# --- Final check or message if API URL seems off (Optional) ---
# You could add a visual indicator if API calls consistently fail or latency is high