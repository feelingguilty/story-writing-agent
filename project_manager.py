import os
import json
import copy
from datetime import datetime
import config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ProjectManager:
    def __init__(self, base_dir=config.PROJECTS_BASE_DIR):
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True) # Ensure base dir exists on init

    def _get_project_dir(self, project_name_display: str) -> str:
        """Gets the path to the project's directory using display name."""
        if not project_name_display:
             raise ValueError("Project display name cannot be empty.")
        # Simple directory name - could be the clean name, but using display name matches Streamlit behavior for dir creation
        return os.path.join(self.base_dir, project_name_display)

    def _get_state_file_path(self, project_name_display: str) -> str:
        """Gets the path to the project's state file using display name."""
        if not project_name_display:
             raise ValueError("Project display name cannot be empty.")
        project_dir = self._get_project_dir(project_name_display)
        # Use a cleaned name for the *file* itself
        clean_name = project_name_display.strip().replace(" ", "_").lower()
        return os.path.join(project_dir, f"{clean_name}_state.json")

    def get_project_list(self) -> list[str]:
        """Returns a list of existing project names (directory names)."""
        projects = []
        if not os.path.exists(self.base_dir):
            return []

        for item in os.listdir(self.base_dir):
            project_dir = os.path.join(self.base_dir, item)
            if os.path.isdir(project_dir):
                # Check if a state file exists within this directory
                clean_name = item.strip().replace(" ", "_").lower()
                state_file = os.path.join(project_dir, f"{clean_name}_state.json")
                if os.path.exists(state_file):
                     projects.append(item) # Return original directory name
        return sorted(projects)

    def load_project(self, project_name_display: str) -> dict:
        """Loads project state from file."""
        state_file = self._get_state_file_path(project_name_display)
        if not os.path.exists(state_file):
            logging.warning(f"Project state file not found: {state_file}")
            raise FileNotFoundError(f"Project '{project_name_display}' not found.")

        try:
            with open(state_file, 'r') as f:
                loaded_state = json.load(f)

            # --- State Merging Logic (Robust load) ---
            default_copy = copy.deepcopy(config.DEFAULT_PROJECT_STATE)
            # Ensure loaded state has the correct project display name and cleaned name
            loaded_state["project_name"] = project_name_display
            loaded_state["cleaned_name"] = project_name_display.strip().replace(" ", "_").lower()

            # Merge missing keys from default (recursive for nested dicts)
            def merge_dict(source, destination):
                for key, value in source.items():
                    if isinstance(value, dict):
                        # Get the value from destination if it exists and is a dict, otherwise use default empty dict
                        node = destination.setdefault(key, {})
                        if not isinstance(node, dict):
                             logging.warning(f"Key '{key}' in state is not a dict, overwriting with default.")
                             destination[key] = {}
                             node = destination[key] # Update node reference
                        merge_dict(value, node)
                    else:
                         # Only set if key doesn't exist in destination
                         if key not in destination:
                            destination[key] = value
                         # Special handling for lists - ensure they exist, but don't merge contents recursively by default
                         elif isinstance(value, list) and not isinstance(destination[key], list):
                              logging.warning(f"Key '{key}' in state is not a list, overwriting with default empty list.")
                              destination[key] = []

            merge_dict(default_copy, loaded_state)

            # Ensure log exists and trim
            loaded_state["log"] = loaded_state.get("log", [])[-50:]
            loaded_state["log"].append(f"Project '{project_name_display}' loaded.")

            logging.info(f"Project '{project_name_display}' loaded successfully.")
            return loaded_state
        except json.JSONDecodeError as e:
            logging.error(f"Error decoding JSON for project '{project_name_display}': {e}")
            raise IOError(f"Invalid project state file format for '{project_name_display}'.") from e
        except Exception as e:
            logging.exception(f"Unexpected error loading project '{project_name_display}':")
            raise IOError(f"Error loading project '{project_name_display}': {e}") from e


    def save_project(self, state: dict):
        """Saves a project state dictionary to its file."""
        if not state or state.get("project_name") is None:
            logging.error("Cannot save state: project_name is missing.")
            raise ValueError("Invalid state: project_name is missing.")

        project_name_display = state["project_name"]
        state_file = self._get_state_file_path(project_name_display)

        try:
            project_dir = self._get_project_dir(project_name_display)
            os.makedirs(project_dir, exist_ok=True)

            state["last_saved"] = datetime.now().isoformat()
            state["log"] = state.get("log", [])[-50:] # Keep log trimmed
            state["log"].append(f"State saved at {state['last_saved']}")

            with open(state_file, 'w') as f:
                json.dump(state, f, indent=4)

            logging.info(f"Project '{project_name_display}' saved successfully.")
            return state # Return the state including save time/log entry

        except Exception as e:
            logging.exception(f"Error saving project '{project_name_display}':")
            raise IOError(f"Error saving project '{project_name_display}': {e}") from e

    def create_project(self, new_project_name_display: str) -> dict:
        """Creates and saves a new project state."""
        if not new_project_name_display or not new_project_name_display.strip():
            raise ValueError("New project name cannot be empty.")

        project_name_orig = new_project_name_display.strip()
        state_file_check = self._get_state_file_path(project_name_orig)

        if os.path.exists(state_file_check):
            raise FileExistsError(f"Project '{project_name_orig}' already exists.")

        # Create new state
        new_state = copy.deepcopy(config.DEFAULT_PROJECT_STATE)
        new_state["project_name"] = project_name_orig
        new_state["cleaned_name"] = project_name_orig.replace(" ", "_").lower()
        new_state["log"] = [f"Created new project '{project_name_orig}'."]
        new_state["last_saved"] = None # Set on first save

        # Save the initial state
        saved_state = self.save_project(new_state)

        logging.info(f"New project '{project_name_orig}' created.")
        return saved_state # Return the state after initial save

    def delete_project(self, project_name_display: str) -> bool:
        """Deletes a project's directory and all its contents."""
        project_dir = self._get_project_dir(project_name_display)

        if not os.path.exists(project_dir):
            logging.warning(f"Attempted to delete non-existent project directory: {project_dir}")
            return False # Project directory didn't exist

        try:
            import shutil
            shutil.rmtree(project_dir)
            logging.info(f"Project directory deleted: {project_dir}")
            return True
        except OSError as e:
            logging.error(f"Error deleting project directory {project_dir}: {e}")
            raise IOError(f"Error deleting project '{project_name_display}': {e}") from e
        except Exception as e:
            logging.exception(f"Unexpected error deleting project '{project_name_display}':")
            raise IOError(f"Error deleting project '{project_name_display}': {e}") from e


# Instantiate the ProjectManager
project_manager = ProjectManager()