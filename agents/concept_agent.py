from groq_client import call_groq

class ConceptAgent:
    def __init__(self):
        self.system_prompt = "You are an AI assistant specialized in film concept development. Be creative, structured, and offer clear options in Markdown format."

    def generate_initial_concepts(self, seed_idea: str) -> str:
        """Generates loglines, frameworks, themes, conflicts from a seed idea."""
        if not seed_idea:
            return "Error: Seed idea cannot be empty."
        prompt = f"""
        Analyze this film seed idea: '{seed_idea}'

        Generate the following, clearly separated by Markdown headings (e.g., ### Loglines):
        1.  **Loglines:** Create 3 distinct loglines.
        2.  **Narrative Frameworks:** Suggest 2-3 common structures (e.g., Three-Act, Hero's Journey) and briefly explain their potential application.
        3.  **Potential Themes:** Propose 3 core themes.
        4.  **Central Conflicts:** Suggest 3 potential central conflicts.
        5.  **Clarifying Question:** Pose one question to the user to guide further development (e.g., about tone, protagonist type, or core message).
        """
        return call_groq(prompt, self.system_prompt)

    def generate_synopsis(self, concept_details: dict) -> str:
        """Generates a synopsis based on selected concept elements."""
        logline = concept_details.get('logline', 'Not specified')
        framework = concept_details.get('framework', 'Not specified')
        theme = concept_details.get('theme', 'Not specified')
        conflict = concept_details.get('conflict', 'Not specified')

        if logline == 'Not specified' and theme == 'Not specified':
             return "Error: Please provide at least a chosen logline or theme to generate a synopsis."

        prompt = f"""
        Based on these chosen film concept elements:
        - Logline Idea: {logline}
        - Narrative Framework: {framework}
        - Core Theme: {theme}
        - Central Conflict: {conflict}

        Write a compelling one-paragraph synopsis (around 100-150 words) that weaves these elements together into a coherent story concept.
        Also, suggest 2 potential plot twists relevant to these elements, listed under a "### Potential Twists" heading.
        """
        return call_groq(prompt, self.system_prompt)