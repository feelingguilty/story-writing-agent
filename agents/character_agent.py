from groq_client import call_groq
import json

class CharacterCrafterAgent:
    def __init__(self):
        self.system_prompt = "You are an AI assistant specialized in character development for films. Focus on depth, motivation, flaws, and arcs. Respond in Markdown."

    def suggest_profile_elements(self, role: str, genre: str, theme: str) -> str:
        """Suggests backstories, motivations, flaws for a character."""
        if not role: return "Error: Character role must be provided."
        if not genre: genre = "Unknown Genre"
        if not theme: theme = "General Theme"

        prompt = f"""
        For a character in a '{genre}' film exploring the theme of '{theme}', who plays the role of the '{role}':

        Suggest 3 distinct options for each of the following, formatted clearly with Markdown lists:
        1.  **Potential Backstories:** Brief descriptions of shaping experiences.
        2.  **Core Motivations:** What drives their primary actions?
        3.  **Significant Flaws:** Key weaknesses or internal struggles.
        """
        return call_groq(prompt, self.system_prompt)

    def map_character_arc(self, character_profile: dict, narrative_framework: str = "Three-Act Structure") -> str:
        """Outlines a potential character arc based on profile and story structure."""
        role = character_profile.get('role', 'character')
        motivation = character_profile.get('motivation', '')
        flaw = character_profile.get('flaw', '')
        backstory = character_profile.get('backstory', '')

        if not motivation or not flaw:
            return "Error: Character motivation and flaw are needed to map a meaningful arc."

        prompt = f"""
        Consider a character:
        - Role: {role}
        - Core Motivation: {motivation}
        - Significant Flaw: {flaw}
        - Backstory Summary: {backstory}

        Outline a potential character arc for them within a standard '{narrative_framework}'. Describe the following key stages concisely under Markdown headings:
        - **Beginning State (Setup):** Initial presentation embodying flaw/motivation.
        - **Inciting Incident Reaction:** How the plot's trigger affects them.
        - **Rising Action / Confrontation:** Key challenges related to their flaw/goal.
        - **Midpoint Shift:** A significant realization or turning point.
        - **Climax / Final Confrontation:** Facing the core conflict, demonstrating change (or lack thereof).
        - **Ending State (Resolution):** Their final emotional/psychological state.
        """
        return call_groq(prompt, self.system_prompt)

    def suggest_relationships(self, primary_char_profile: dict, other_char_roles: list) -> str:
        """Suggests potential relationship dynamics."""
        role = primary_char_profile.get('role', 'This character')
        profile_summary = f"Role: {role}, Motivation: {primary_char_profile.get('motivation', 'N/A')}, Flaw: {primary_char_profile.get('flaw', 'N/A')}"

        if not other_char_roles:
            return "No other characters defined to suggest relationships with."

        prompt = f"""
        Consider the primary character: {profile_summary}

        Suggest potential relationship dynamics between this character and characters playing these roles: {', '.join(other_char_roles)}.

        For each potential relationship pair (e.g., {role} <-> {other_char_roles[0]}):
        1.  **Dynamic Type:** (e.g., Mentor-Mentee, Rivals, Allies, Foil, Family, Romantic) - Suggest 1-2 options.
        2.  **Potential Conflict Source:** Based on likely goals or personalities derived from their roles.
        3.  **Potential Synergy/Support Source:** How they might help each other.

        Format clearly using Markdown lists for each pair.
        """
        return call_groq(prompt, self.system_prompt)