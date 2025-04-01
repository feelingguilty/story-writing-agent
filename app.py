# streamlit_app.py
import streamlit as st
import os
import json
from datetime import datetime
import copy # To deep copy default state

# --- Project Imports ---
import config # Ensure config.py is in the same directory or PYTHONPATH
from agents.concept_agent import ConceptAgent
from agents.character_agent import CharacterCrafterAgent
from agents.script_agent import ScriptSmithAgent
# Note: call_groq is used within agents, no direct import needed here normally

# --- Constants and Initial Setup ---
DEFAULT_PROJECT_STATE = {
    "project_name": "Untitled", # Will store the display name (potentially uncleaned)
    "cleaned_name": "untitled", # For internal file/dir usage
    "current_phase": "Concept", # Could track active tab
    "concept": { "seed_idea": "", "generated_concepts_md": "", "chosen_logline": "", "chosen_framework": "Three-Act Structure", "chosen_theme": "", "chosen_conflict": "", "synopsis_md": "", "final_synopsis": "" },
    "characters": {},
    "script": { "outline_md": "", "full_script_content": "", "analysis_md": "" },
    "pre_production": { "moodboard_ideas_md": "", "storyboard_ideas_md": "" },
    "last_saved": None,
    "log": ["Project state initialized."]
}

# --- Helper Functions (Adapted for Streamlit) ---

def get_project_list():
    """Returns a list of existing project names (directory names)."""
    projects = []
    if os.path.exists(config.PROJECTS_BASE_DIR):
        for item in os.listdir(config.PROJECTS_BASE_DIR):
            project_dir = os.path.join(config.PROJECTS_BASE_DIR, item)
            if os.path.isdir(project_dir):
                # Check if a state file exists (using cleaned name convention)
                clean_name = item.strip().replace(" ", "_").lower()
                state_file = os.path.join(project_dir, f"{clean_name}_state.json")
                if os.path.exists(state_file):
                     projects.append(item) # Return original directory name
    return sorted(projects) if projects else []

def _get_project_state_path(project_name_display):
    """Gets the path to the project's state file using display name."""
    if not project_name_display: return None
    project_dir = os.path.join(config.PROJECTS_BASE_DIR, project_name_display)
    clean_name = project_name_display.strip().replace(" ", "_").lower()
    return os.path.join(project_dir, f"{clean_name}_state.json")

def save_project_state():
    """Saves the current st.session_state.project_state to its file."""
    state = st.session_state.project_state
    if not state or state.get("project_name", "Untitled") == "Untitled":
        st.error("Cannot save an unnamed project. Create or load a project first.")
        return

    project_name_display = state["project_name"]
    state_file = _get_project_state_path(project_name_display)
    if not state_file:
         st.error(f"Error: Invalid project name '{project_name_display}' for saving.")
         return

    project_dir = os.path.dirname(state_file)

    try:
        os.makedirs(project_dir, exist_ok=True)
        state["last_saved"] = datetime.now().isoformat()
        state["log"] = state.get("log", [])[-50:]
        state["log"].append(f"State saved at {state['last_saved']}")

        with open(state_file, 'w') as f:
            json.dump(state, f, indent=4)
        st.success(f"Project '{project_name_display}' saved successfully!")
        print(f"Project '{project_name_display}' saved.")
        # Update state in session_state (mainly for log/save time)
        st.session_state.project_state = state
        # No explicit rerun needed, success message display implies it happens
    except Exception as e:
        error_msg = f"Error saving project '{project_name_display}': {e}"
        print(error_msg)
        st.error(error_msg)
        # Log failure but don't corrupt state if save fails
        st.session_state.project_state["log"] = st.session_state.project_state.get("log", [])
        st.session_state.project_state["log"].append(f"SAVE FAILED: {error_msg}")
        st.session_state.project_state["log"] = st.session_state.project_state["log"][-50:]


def load_project_state(project_name_display: str):
    """Loads project state from file into st.session_state."""
    if not project_name_display:
        st.error("No project selected to load.")
        return

    state_file = _get_project_state_path(project_name_display)
    if not state_file or not os.path.exists(state_file):
        msg = f"Error: Project state file not found for '{project_name_display}'. Cannot load."
        print(msg)
        st.error(msg)
        # Don't load default, keep existing state or let user create new
        return

    try:
        with open(state_file, 'r') as f:
            loaded_state = json.load(f)

        # --- State Merging Logic ---
        default_copy = copy.deepcopy(DEFAULT_PROJECT_STATE)
        # Ensure loaded state has the correct project display name
        loaded_state["project_name"] = project_name_display
        loaded_state["cleaned_name"] = project_name_display.strip().replace(" ", "_").lower()
        # Merge missing keys from default
        for key, default_value in default_copy.items():
            if key not in loaded_state:
                loaded_state[key] = default_value
            elif isinstance(default_value, dict):
                 if not isinstance(loaded_state.get(key), dict): loaded_state[key] = {}
                 for sub_key, default_sub_value in default_value.items():
                     if sub_key not in loaded_state[key]: loaded_state[key][sub_key] = default_sub_value
        # --- End State Merging ---

        loaded_state["log"] = loaded_state.get("log", [])[-50:]
        loaded_state["log"].append(f"Project '{project_name_display}' loaded.")
        st.session_state.project_state = loaded_state # Update session state
        st.success(f"Project '{project_name_display}' loaded successfully.")
        print(f"Project '{project_name_display}' loaded.")
        st.rerun() # Rerun to reflect loaded state in UI widgets
    except Exception as e:
        error_msg = f"Error loading project '{project_name_display}': {e}."
        print(error_msg)
        st.error(error_msg)

def create_new_project(new_project_name_display: str):
    """Creates and saves a new project, updating st.session_state."""
    if not new_project_name_display:
        st.error("New project name cannot be empty.")
        return

    project_name_orig = new_project_name_display.strip()
    if not project_name_orig:
        st.error("Project name cannot be empty.")
        return

    project_dir_check = os.path.join(config.PROJECTS_BASE_DIR, project_name_orig)
    clean_name = project_name_orig.replace(" ", "_").lower()
    state_file = os.path.join(project_dir_check, f"{clean_name}_state.json")

    if os.path.isdir(project_dir_check) or os.path.exists(state_file):
        st.error(f"Error: Project '{project_name_orig}' already exists. Try loading or choose different name.")
        return

    # Create new state
    new_state = copy.deepcopy(DEFAULT_PROJECT_STATE)
    new_state["project_name"] = project_name_orig # Store original display name
    new_state["cleaned_name"] = clean_name
    new_state["log"] = [f"Created new project '{project_name_orig}'."]
    new_state["last_saved"] = None

    # Initial save (uses name from state)
    status, saved_state = save_project_state(new_state) # Pass the state dict

    if "Error" in status:
         # If save failed, display error but keep the unsaved state in session for potential retry?
         st.session_state.project_state = new_state # Reflect the attempted new state
         st.error(status)
    else:
        # If save succeeded, update session state with the *saved* state (has save time, log)
        st.session_state.project_state = saved_state
        st.success(f"New project '{project_name_orig}' created and saved.")
        st.rerun() # Rerun to reflect the new project state

def update_log(message):
    """Appends a message to the project log in session_state."""
    if 'project_state' in st.session_state and isinstance(st.session_state.project_state, dict):
        log_list = st.session_state.project_state.get("log", [])
        log_list.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
        st.session_state.project_state["log"] = log_list[-50:]
    else:
        print("Warning: update_log called before project_state initialized.")


# --- Instantiate Agents ---
concept_agent = ConceptAgent()
character_agent = CharacterCrafterAgent()
script_agent = ScriptSmithAgent()


# ==============================================================================
# Streamlit App Layout and Logic
# ==============================================================================

st.set_page_config(layout="wide", page_title="FilmForge AI Assistant")
st.title("🎬 FilmForge AI Assistant")

# --- Initialize Session State ---
if 'project_state' not in st.session_state:
    st.session_state.project_state = copy.deepcopy(DEFAULT_PROJECT_STATE)
    print("Initialized Session State")
if 'active_char_for_display' not in st.session_state:
     st.session_state.active_char_for_display = None # Track selected char for display


# --- Helper to get current project state ---
def get_state():
     # Ensures we always work with the session state's project data
     if 'project_state' not in st.session_state:
          st.session_state.project_state = copy.deepcopy(DEFAULT_PROJECT_STATE)
     return st.session_state.project_state

# --- Sidebar for Project Management ---
with st.sidebar:
    st.header("Project Management")

    # Load Project
    projects = get_project_list()
    # Ensure current project name is valid for selectbox default
    current_project_name = get_state().get("project_name", "Untitled")
    try:
        # Set index=None if current project isn't in the list or is "Untitled"
        current_project_index = projects.index(current_project_name) if current_project_name != "Untitled" and current_project_name in projects else None
    except ValueError:
         current_project_index = None # Handle case where project name exists but not in list (e.g. after deletion)


    selected_project = st.selectbox(
        "Load Existing Project",
        options=projects,
        index=current_project_index,
        placeholder="Select project...",
        key="sb_load_project" # Use key to track selection
    )

    if st.button("Load Project", key="btn_load", disabled=(selected_project is None)):
        if selected_project:
            update_log(f"Attempting to load project: {selected_project}")
            load_project_state(selected_project)
            st.session_state.active_char_for_display = None # Reset active char on load

    st.divider()

    # Create New Project
    new_proj_name = st.text_input("New Project Name", key="ti_new_project_name")
    if st.button("Create New Project", key="btn_create"):
        if new_proj_name:
            update_log(f"Attempting to create project: {new_proj_name}")
            create_new_project(new_proj_name)
            # Clear input after attempt (handled by rerun if successful)
            st.session_state.ti_new_project_name = "" # Explicitly clear input state if needed
            st.session_state.active_char_for_display = None # Reset active char on create
        else:
            st.warning("Please enter a name for the new project.")

    st.divider()

    # Save Project
    if st.button("Save Current Project", key="btn_save"):
        save_project_state()

    st.divider()
    st.write(f"**Current Project:** {get_state().get('project_name', 'Untitled')}")
    last_saved = get_state().get('last_saved')
    if last_saved:
        st.caption(f"Last Saved: {datetime.fromisoformat(last_saved).strftime('%Y-%m-%d %H:%M:%S')}")
    else:
         st.caption("Not saved yet.")


# --- Main Content Area with Tabs ---
tab_titles = [
    "1. Concept Development",
    "2. Character Development",
    "3. Screenwriting",
    "4. Pre-Production Ideas",
    "Log"
]
tab1, tab2, tab3, tab4, tab5 = st.tabs(tab_titles)

# --- Tab 1: Concept Development ---
with tab1:
    st.header("Concept Development")
    st.markdown("Define the core idea of your film.")

    # Use session state to preserve input across runs
    seed_idea = st.text_area(
        "Seed Idea (Genre, Theme, Logline, Keywords)",
        value=get_state().get("concept", {}).get("seed_idea", ""), # Pre-fill from state
        key="concept_seed_idea_ta" # Unique key
    )
    # Update state immediately if text area changes (Streamlit reruns on change)
    get_state()["concept"]["seed_idea"] = seed_idea

    if st.button("Generate Initial Concepts", key="btn_gen_concepts"):
        if seed_idea:
            update_log("Generating initial concepts...")
            with st.spinner("AI is thinking..."):
                result = concept_agent.generate_initial_concepts(seed_idea)
            if "Error:" in result:
                st.error(result)
                update_log(f"Concept generation failed: {result}")
            else:
                get_state()["concept"]["generated_concepts_md"] = result
                update_log("Concept generation complete.")
                # Result will be displayed below because state is updated
        else:
            st.warning("Please enter a seed idea.")

    # Display generated concepts (always reads from state)
    st.markdown("---")
    st.markdown("**Generated Concepts:**")
    st.markdown(get_state().get("concept", {}).get("generated_concepts_md", "*No concepts generated yet.*"))
    st.markdown("---")

    st.subheader("Refine Your Concept")
    # Use columns for better layout
    col1, col2 = st.columns(2)
    with col1:
        logline = st.text_input(
            "Chosen Logline",
            value=get_state().get("concept", {}).get("chosen_logline", ""),
            key="concept_logline"
        )
        get_state()["concept"]["chosen_logline"] = logline # Update state on change

        theme = st.text_input(
            "Chosen Theme",
            value=get_state().get("concept", {}).get("chosen_theme", ""),
            key="concept_theme"
        )
        get_state()["concept"]["chosen_theme"] = theme
    with col2:
        framework = st.text_input(
            "Chosen Narrative Framework",
             value=get_state().get("concept", {}).get("chosen_framework", "Three-Act Structure"),
             key="concept_framework"
        )
        get_state()["concept"]["chosen_framework"] = framework

        conflict = st.text_input(
            "Chosen Central Conflict",
            value=get_state().get("concept", {}).get("chosen_conflict", ""),
            key="concept_conflict"
        )
        get_state()["concept"]["chosen_conflict"] = conflict

    if st.button("Generate Synopsis & Twists", key="btn_gen_synopsis"):
        concept_details = {
            'logline': logline, 'framework': framework, 'theme': theme, 'conflict': conflict
        }
        if logline or theme: # Need at least one element
            update_log("Generating synopsis...")
            with st.spinner("AI is thinking..."):
                result = concept_agent.generate_synopsis(concept_details)
            if "Error:" in result:
                st.error(result)
                update_log(f"Synopsis generation failed: {result}")
            else:
                get_state()["concept"]["synopsis_md"] = result
                update_log("Synopsis generation complete.")
        else:
            st.warning("Please provide at least a Logline or Theme.")

    st.markdown("**Generated Synopsis & Twists:**")
    st.markdown(get_state().get("concept", {}).get("synopsis_md", "*No synopsis generated yet.*"))


# --- Tab 2: Character Development ---
with tab2:
    st.header("Character Development")
    st.markdown("Develop your characters.")

    state_chars = get_state().get("characters", {})
    char_names = list(state_chars.keys())

    col1, col2 = st.columns([1, 2]) # Adjust column ratios as needed

    with col1:
        st.subheader("Add/Edit Character")
        char_name = st.text_input("Character Name", key="char_name_input")
        char_role = st.text_input("Character Role", placeholder="e.g., Protagonist", key="char_role_input")

        if st.button("Suggest Profile Elements", key="btn_suggest_profile"):
            if char_name and char_role:
                update_log(f"Generating profile ideas for {char_name}...")
                genre = get_state().get("concept", {}).get("seed_idea", "Unknown Genre")
                theme = get_state().get("concept", {}).get("chosen_theme", "General Theme")
                with st.spinner("AI is suggesting..."):
                     result = character_agent.suggest_profile_elements(char_role, genre, theme)
                # Display suggestions temporarily, don't save to state unless user copies
                st.session_state.temp_profile_suggestions = result # Store in session state for display this run
                update_log("Profile suggestions generated.")
            else:
                st.warning("Please enter Character Name and Role.")

        # Display temporary suggestions if they exist
        if 'temp_profile_suggestions' in st.session_state and st.session_state.temp_profile_suggestions:
             with st.expander("Show/Hide Profile Suggestions", expanded=True):
                  st.markdown(st.session_state.temp_profile_suggestions)
                  # Clear after display? Or keep until next suggestion? Let's keep for now.
                  # del st.session_state.temp_profile_suggestions

        st.markdown("**Define Character Profile:**")
        # Use current char name for default values if editing
        current_profile = state_chars.get(char_name, {}).get("profile", {}) if char_name else {}
        backstory = st.text_area("Chosen Backstory", value=current_profile.get("backstory", ""), key="char_backstory")
        motivation = st.text_area("Chosen Motivation", value=current_profile.get("motivation", ""), key="char_motivation")
        flaw = st.text_area("Chosen Flaw", value=current_profile.get("flaw", ""), key="char_flaw")

        if st.button("Save/Update Character Profile", key="btn_save_char"):
             if char_name and char_role:
                  update_log(f"Saving/Updating character: {char_name}")
                  if "characters" not in get_state(): get_state()["characters"] = {} # Ensure dict exists
                  # Preserve existing arc/rels if updating
                  existing_data = get_state()["characters"].get(char_name, {})
                  get_state()["characters"][char_name] = {
                      "role": char_role,
                      "profile": { "backstory": backstory, "motivation": motivation, "flaw": flaw },
                      "arc_description": existing_data.get("arc_description", ""),
                      "relationship_suggestions": existing_data.get("relationship_suggestions", "")
                  }
                  st.success(f"Character '{char_name}' profile saved.")
                  update_log(f"Character {char_name} saved.")
                  # Clear inputs? Or keep for further editing? Let's keep for now.
                  # Reset temporary suggestion display
                  if 'temp_profile_suggestions' in st.session_state: del st.session_state.temp_profile_suggestions
                  st.rerun() # Rerun to update character list dropdown
             else:
                  st.warning("Please enter Character Name and Role.")

    with col2:
        st.subheader("Explore Arcs & Relationships")
        char_options = ["Select a character..."] + char_names
        # Use the session state variable to control the selection
        selected_char_for_arc = st.selectbox(
             "Select Character",
             options=char_options,
             index=char_options.index(st.session_state.active_char_for_display) if st.session_state.active_char_for_display in char_options else 0,
             key="char_select_arc"
        )

        # Update the active character display variable when selection changes
        if selected_char_for_arc != "Select a character..." and selected_char_for_arc != st.session_state.active_char_for_display:
             st.session_state.active_char_for_display = selected_char_for_arc
             # Rerun might be needed if display depends heavily on this, but let's try without first
             # st.rerun()

        active_char_data = state_chars.get(st.session_state.active_char_for_display, {}) if st.session_state.active_char_for_display else {}

        # Display Arc
        st.markdown("**Character Arc:**")
        if st.button("Generate Character Arc", key="btn_gen_arc", disabled=(not st.session_state.active_char_for_display)):
            char_name_active = st.session_state.active_char_for_display
            if char_name_active and char_name_active in get_state()["characters"]:
                 update_log(f"Generating arc for {char_name_active}...")
                 profile = get_state()["characters"][char_name_active].get("profile", {})
                 framework = get_state()["concept"].get("chosen_framework", "Three-Act Structure")
                 with st.spinner("AI is mapping the arc..."):
                      result = character_agent.map_character_arc(profile, framework)
                 if "Error:" in result:
                      st.error(result)
                      update_log(f"Arc generation FAILED for {char_name_active}: {result}")
                 else:
                      get_state()["characters"][char_name_active]["arc_description"] = result
                      update_log(f"Arc generation complete for {char_name_active}.")
                      st.success(f"Generated arc for {char_name_active}.")
                      # Rerun likely needed to update the display below immediately
                      st.rerun()

        # Always display arc description from state for the active character
        arc_desc = active_char_data.get("arc_description", "*No arc generated yet.*")
        st.markdown(arc_desc)
        st.markdown("---")

        # Display Relationships
        st.markdown("**Relationship Suggestions:**")
        if st.button("Suggest Relationships", key="btn_gen_rels", disabled=(not st.session_state.active_char_for_display)):
            char_name_active = st.session_state.active_char_for_display
            if char_name_active and char_name_active in get_state()["characters"]:
                 update_log(f"Generating relationships for {char_name_active}...")
                 profile = get_state()["characters"][char_name_active].get("profile", {})
                 other_roles = [data["role"] for name, data in get_state()["characters"].items() if name != char_name_active and isinstance(data, dict)]
                 with st.spinner("AI is exploring connections..."):
                      result = character_agent.suggest_relationships(profile, other_roles)

                 if "Error:" in result:
                      st.error(result)
                      update_log(f"Relationship suggestions FAILED for {char_name_active}: {result}")
                 else:
                      get_state()["characters"][char_name_active]["relationship_suggestions"] = result
                      update_log(f"Relationship suggestions complete for {char_name_active}.")
                      st.success(f"Generated relationship suggestions for {char_name_active}.")
                      st.rerun() # Rerun likely needed

        # Always display relationship suggestions from state for the active character
        rel_sugg = active_char_data.get("relationship_suggestions", "*No relationship suggestions generated yet.*")
        st.markdown(rel_sugg)


# --- Tab 3: Screenwriting ---
with tab3:
    st.header("Screenwriting")
    st.markdown("Write your screenplay.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Generate Outline from Synopsis", key="btn_gen_outline"):
            update_log("Generating script outline...")
            synopsis = get_state()["concept"].get("synopsis_md", "")
            if synopsis and "### Potential Twists" in synopsis: synopsis = synopsis.split("### Potential Twists")[0].strip()
            if not synopsis: synopsis = get_state()["concept"].get("chosen_logline", "")
            if synopsis:
                framework = get_state()["concept"].get("chosen_framework", "Three-Act Structure")
                with st.spinner("AI is outlining..."):
                     result = script_agent.generate_outline(synopsis, framework)
                if "Error:" in result:
                     st.error(result); update_log(f"Outline generation FAILED: {result}")
                else:
                     get_state()["script"]["outline_md"] = result
                     update_log("Outline generation complete.")
                     st.success("Outline generated.")
                     # No rerun needed, display below will update
            else:
                st.warning("Cannot generate outline without a synopsis or logline.")

        st.markdown("**Generated Outline:**")
        st.markdown(get_state().get("script", {}).get("outline_md", "*No outline generated yet.*"))

    with col2:
        st.subheader("Draft Scene")
        scene_heading = st.text_input("Scene Heading", placeholder="INT. LOCATION - DAY/NIGHT", key="scene_head")
        scene_desc = st.text_area("Scene Description/Goal", key="scene_desc")
        scene_context = st.text_input("Character Context (Optional)", key="scene_context")
        scene_tone = st.text_input("Scene Tone (Optional)", key="scene_tone")

        # Temporarily store drafted scene result in session state for display
        if 'temp_drafted_scene' not in st.session_state: st.session_state.temp_drafted_scene = ""

        if st.button("Draft Scene", key="btn_draft_scene"):
             if scene_heading and scene_desc:
                  update_log(f"Drafting scene: {scene_heading}")
                  with st.spinner("AI is writing..."):
                       result = script_agent.draft_scene(scene_heading, scene_desc, scene_context, scene_tone)
                  st.session_state.temp_drafted_scene = result # Store for display
                  if "Error:" in result:
                       st.error(result); update_log(f"Scene drafting FAILED: {result}")
                  else:
                       update_log("Scene drafting complete.")
                       st.info("Drafted scene below. Copy and paste into the main script editor.")
             else:
                  st.warning("Scene Heading and Description are required.")

        st.text_area("Drafted Scene Output", value=st.session_state.temp_drafted_scene, height=200, key="drafted_scene_disp", help="Copy from here")

    st.markdown("---")
    st.subheader("Full Script Draft")
    full_script = st.text_area(
        "Script Content (.fountain format recommended)",
        value=get_state().get("script", {}).get("full_script_content", ""),
        height=600,
        key="script_editor_main"
    )
    # Update state immediately on change
    get_state()["script"]["full_script_content"] = full_script

    col_refine, col_analyze = st.columns(2)
    with col_refine:
        st.markdown("**Refine Text:**")
        text_to_refine = st.text_area("Paste Dialogue or Action Line to Refine", height=100, key="refine_input_text")
        refine_instruction = st.text_input("Refinement Instruction", placeholder="e.g., 'Make dialogue tense'", key="refine_instr")
        if 'temp_refined_text' not in st.session_state: st.session_state.temp_refined_text = ""

        if st.button("Refine Text", key="btn_refine"):
             if text_to_refine and refine_instruction:
                 update_log("Refining text...")
                 # Basic dialogue check (can be improved)
                 is_dialogue = any(f"\n{cue.upper()}\n" in f"\n{text_to_refine}\n" for cue in get_state().get("characters", {}).keys())
                 with st.spinner("AI is editing..."):
                    if is_dialogue: result = script_agent.refine_dialogue_tone(text_to_refine, refine_instruction)
                    elif "concise" in refine_instruction.lower(): result = script_agent.refine_action_conciseness(text_to_refine)
                    else: # Generic fallback
                        generic_prompt = f"Instruction: '{refine_instruction}'. Apply to:\n---\n{text_to_refine}\n---"
                        result = call_groq(generic_prompt, script_agent.sp_editor)
                 st.session_state.temp_refined_text = result # Store for display
                 if "Error:" in result: st.error(result); update_log(f"Refinement FAILED: {result}")
                 else: update_log("Refinement complete."); st.info("Refined text below.")
             else: st.warning("Text and instruction required.")
        st.text_area("Refined Text Output", value=st.session_state.temp_refined_text, height=100, key="refined_text_disp", help="Copy from here")

    with col_analyze:
        st.markdown("**Analyze Script Issues:**")
        if st.button("Analyze Script Issues (Last ~2000 Chars)", key="btn_analyze"):
            script_content = get_state().get("script", {}).get("full_script_content", "")
            if len(script_content) > 50:
                update_log("Analyzing script...")
                excerpt = script_content[-2000:]
                with st.spinner("AI is analyzing..."):
                     result = script_agent.analyze_script_issues(excerpt)
                if "Error:" in result: st.error(result); update_log(f"Analysis FAILED: {result}")
                else:
                     get_state()["script"]["analysis_md"] = result
                     update_log("Analysis complete.")
                     st.success("Analysis complete.")
                     # Rerun needed to show result below
                     st.rerun()
            else: st.warning("Not enough script content to analyze meaningfully.")
        st.markdown(get_state().get("script", {}).get("analysis_md", "*No analysis performed yet.*"))


# --- Tab 4: Pre-Production Ideas ---
with tab4:
    st.header("Pre-Production Ideas")
    st.markdown("Generate visual ideas based on your script and concept.")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Moodboard Ideas")
        if st.button("Generate Moodboard Ideas", key="btn_gen_mood"):
            update_log("Generating moodboard ideas...")
            state = get_state()
            theme = state["concept"].get("chosen_theme", "")
            genre = state["concept"].get("seed_idea", "")
            synopsis = state["concept"].get("final_synopsis", state["concept"].get("chosen_logline",""))
            if theme or genre or synopsis:
                with st.spinner("AI is brainstorming visuals..."):
                    result = script_agent.generate_moodboard_ideas(theme, genre, synopsis)
                if "Error:" in result: st.error(result); update_log(f"Moodboard generation FAILED: {result}")
                else:
                    state["pre_production"]["moodboard_ideas_md"] = result
                    update_log("Moodboard ideas generated.")
                    st.success("Moodboard ideas generated.")
                    # Rerun needed
                    st.rerun()
            else: st.warning("Provide Theme, Genre (Seed Idea), or Synopsis.")
        st.markdown(get_state().get("pre_production",{}).get("moodboard_ideas_md", "*No moodboard ideas generated yet.*"))

    with col2:
        st.subheader("Storyboard Shot Ideas")
        scene_text_for_sb = st.text_area("Paste Scene Text Here", height=200, key="sb_scene_input")
        if st.button("Generate Storyboard Ideas", key="btn_gen_sb"):
            if scene_text_for_sb.strip():
                update_log("Generating storyboard ideas...")
                with st.spinner("AI is visualizing shots..."):
                     result = script_agent.generate_storyboard_shot_ideas(scene_text_for_sb)
                if "Error:" in result: st.error(result); update_log(f"Storyboard generation FAILED: {result}")
                else:
                     # Store result directly in state this time
                     get_state()["pre_production"]["storyboard_ideas_md"] = result
                     update_log("Storyboard ideas generated.")
                     st.success("Storyboard ideas generated.")
                     # Clear input area after generation?
                     st.session_state.sb_scene_input = ""
                     st.rerun() # Rerun needed
            else: st.warning("Please paste scene text.")
        st.markdown(get_state().get("pre_production",{}).get("storyboard_ideas_md", "*No storyboard ideas generated yet.*"))


# --- Tab 5: Log ---
with tab5:
    st.header("Action Log")
    log_content = "\n".join(get_state().get("log", ["Log is empty."]))
    st.text_area("Log", value=log_content, height=600, disabled=True, key="log_display_area")

# --- Final Check for API Key ---
if not config.GROQ_API_KEY:
     st.sidebar.error("GROQ API Key missing! AI features disabled.", icon="🚨")