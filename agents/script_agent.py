from groq_client import call_groq

class ScriptSmithAgent:
    def __init__(self):
        # System prompts tailored to task
        self.sp_writer = "You are an AI assistant specialized in screenwriting. Adhere strictly to standard screenplay format (scene headings, action lines, character cues, dialogue). Be concise and clear."
        self.sp_analyzer = "You are an AI script analyst. Critically evaluate the provided text for logical consistency, pacing issues, and character voice based ONLY on the text itself. Be objective and specific."
        self.sp_editor = "You are an AI script editor. Revise the provided text precisely according to the user's instruction, maintaining the original format (e.g., dialogue, action line)."
        self.sp_creative = "You are a creative AI assistant helping with film pre-production visualization. Generate evocative ideas based on script content."

    def generate_outline(self, synopsis: str, framework: str = "Three-Act Structure") -> str:
        """Generates a scene-by-scene outline."""
        if not synopsis: return "Error: Synopsis cannot be empty."
        prompt = f"""
        Based on the following film synopsis and using the '{framework}':
        Synopsis: "{synopsis}"

        Generate a scene-by-scene outline. For each scene, provide:
        - SCENE HEADING (INT./EXT. LOCATION - DAY/NIGHT)
        - BRIEF DESCRIPTION (1-2 sentences: core action, character goal, plot point).

        Number scenes sequentially. Ensure logical progression. Use standard screenplay formatting for headings.
        Example:
        1. INT. COFFEE SHOP - DAY
           JANE waits nervously. MARK arrives late, revealing a plot-triggering secret.
        """
        # Use a model potentially better suited for longer structured output if available via Groq
        return call_groq(prompt, self.sp_writer, model=config.DEFAULT_MODEL) # Adjust model if needed

    def draft_scene(self, scene_heading: str, scene_description: str, character_context: str = "", tone: str = "neutral") -> str:
        """Drafts a full scene based on outline/description."""
        if not scene_heading or not scene_description:
             return "Error: Scene heading and description are required."
        prompt = f"""
        Write the full screenplay scene:
        - Scene Heading: {scene_heading}
        - Scene Description/Goal: {scene_description}
        - Character Context: {character_context if character_context else 'None provided'}
        - Desired Tone: {tone if tone else 'neutral'}

        Follow standard screenplay format STRICTLY (HEADINGS, ACTION, CHARACTER, DIALOGUE, (parentheticals)).
        Generate ONLY the scene content.
        """
        return call_groq(prompt, self.sp_writer)

    def refine_dialogue_tone(self, dialogue: str, target_tone: str) -> str:
        """Refines dialogue towards a specific tone."""
        if not dialogue or not target_tone: return "Error: Dialogue and target tone are required."
        prompt = f"""
        Refine the following dialogue snippet to have a '{target_tone}' tone, while keeping the core meaning and character voice consistent.

        Original Dialogue:
        ---
        {dialogue}
        ---

        Provide ONLY the revised dialogue snippet, maintaining the original Character Cue if present.
        """
        return call_groq(prompt, self.sp_editor)

    def refine_action_conciseness(self, action_line: str) -> str:
        """Makes action lines more concise."""
        if not action_line: return "Error: Action line cannot be empty."
        prompt = f"""
        Make the following action line(s) more concise and impactful, suitable for a screenplay. Remove unnecessary words while preserving the essential visual information.

        Original Action Line(s):
        ---
        {action_line}
        ---

        Provide ONLY the revised, concise action line(s).
        """
        return call_groq(prompt, self.sp_editor)


    def analyze_script_issues(self, script_excerpt: str) -> str:
        """Analyzes a script excerpt for plot holes or pacing issues."""
        if not script_excerpt or len(script_excerpt) < 50:
             return "Error: Please provide a substantial script excerpt (at least 50 characters) for analysis."
        prompt = f"""
        Analyze the following script excerpt for potential issues. Focus ONLY on:
        1.  **Plot Holes/Continuity:** Contradictions or logical gaps *within the excerpt*.
        2.  **Pacing:** Sections that feel rushed, slow, or redundant *based on the text*.
        3.  **Character Consistency/Voice:** Actions or dialogue inconsistent *within the excerpt*.
        4.  **Clarity/Formatting:** Confusing descriptions or non-standard formatting.

        List identified potential issues clearly with brief explanations. Do NOT suggest solutions. If no major issues are found, state that.

        Script Excerpt:
        ---
        {script_excerpt}
        ---
        """
        return call_groq(prompt, self.sp_analyzer)

    # --- Pre-Production Ideas ---

    def generate_moodboard_ideas(self, theme: str, genre: str, synopsis: str) -> str:
         """Generates textual ideas for a mood board."""
         if not theme and not genre and not synopsis:
             return "Error: Please provide theme, genre, or synopsis for mood board ideas."
         prompt = f"""
         Based on the film concept:
         - Genre: {genre if genre else 'N/A'}
         - Theme: {theme if theme else 'N/A'}
         - Synopsis: {synopsis if synopsis else 'N/A'}

         Generate textual ideas for a mood board. Suggest:
         1.  **Color Palette:** Describe 3-5 key colors and their emotional association (e.g., "Deep blues for mystery, sickly yellow for decay").
         2.  **Key Textures:** Suggest relevant textures (e.g., "Rough concrete, smooth chrome, decaying lace").
         3.  **Lighting Style:** Describe the overall lighting approach (e.g., "High-contrast noir, soft natural light, harsh neon").
         4.  **Reference Keywords:** List 5-10 keywords for image searching (e.g., "Urban decay, isolated cabin, bioluminescence, vintage tech").
         5.  **Comparable Films/Art (Optional):** Mention 1-2 existing works with a similar visual feel.

         Format clearly using Markdown headings.
         """
         return call_groq(prompt, self.sp_creative)

    def generate_storyboard_shot_ideas(self, scene_text: str) -> str:
        """Generates textual ideas for key storyboard shots for a scene."""
        if not scene_text or len(scene_text) < 50:
             return "Error: Please provide a sufficiently detailed scene text."

        prompt = f"""
        Analyze the following screenplay scene text:
        ---
        {scene_text}
        ---

        Suggest 3-5 key storyboard shot ideas to visually capture the essence of this scene. For each shot idea, describe:
        1.  **Shot Type:** (e.g., Wide Shot, Medium Close-Up, POV, Insert Shot, Over-the-Shoulder).
        2.  **Subject/Action:** What is the main focus of the frame and what is happening?
        3.  **Purpose/Emotion:** Why is this shot important? What feeling should it evoke?

        Example:
        1.  **Shot Type:** Extreme Close-Up
        2.  **Subject/Action:** Character's trembling hand reaching for a key.
        3.  **Purpose/Emotion:** Emphasize nervousness and the importance of the object.

        Format clearly using Markdown numbered lists.
        """
        return call_groq(prompt, self.sp_creative)