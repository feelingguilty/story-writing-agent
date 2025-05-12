import os
import base64
from io import BytesIO
from PIL import Image
import config
from google import genai
from google.genai import types
import logging

# --- File: filmforge_api/image_generator.py (Modified generate_image_from_prompt function) ---

# ... (imports and client initialization) ...

IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation" # Or "gemini-2.0-flash-exp-image-generation"

# ... (generate_image_from_prompt function definition) ...

def generate_image_from_prompt(prompt: str, num_images: int = 3):

    client = genai.Client()
    # Refined prompt to encourage distinct visuals based on the input text.
    # Explicitly ask for "visual concepts" or "distinct images".
    # Keep the original ideas for context.
    modified_prompt = f"""
Generate {num_images} distinct visual concepts or images based on the following ideas and descriptions for a film:

---
{prompt}
---

Focus on creating varied visual styles or content for each image, inspired by the text above.
"""

    try:
        logging.info(f"Calling Google GenAI for image generation with prompt: '{modified_prompt[:200]}...'") # Log more prompt
        response = client.models.generate_content(
            model=IMAGE_MODEL,
            contents=modified_prompt,
            config=types.GenerateContentConfig(
                response_modalities=['TEXT', 'IMAGE'] # Explicitly ask for text and image
            )
        )

        # ... (rest of the response processing and base64 encoding logic remains the same) ...
        # The logic to iterate through parts and append {"type": "text", "content": ...}
        # or {"type": "image/...", "content": "base64_string"} should be kept.
        # Ensure you are correctly handling the base64 encoding and PIL image processing
        # as shown in the corrected image_generator.py in the previous response.

        if response.candidates and response.candidates[0].content:
            result_parts = []
            for part in response.candidates[0].content.parts:
                if part.text is not None:
                    logging.info(f"Received text part: {part.text[:50]}...")
                    result_parts.append({"type": "text", "content": part.text})
                elif part.inline_data is not None:
                     # Convert image bytes to base64
                     try:
                         image_bytes = part.inline_data.data
                         img = Image.open(BytesIO(image_bytes))
                         img_format = img.format
                         buffered = BytesIO()
                         if img_format in ['JPEG', 'PNG', 'WEBP']: # Supported formats for saving
                             img.save(buffered, format=img_format) # Save in original format
                         else:
                             # Convert unsupported formats (like animated GIFs) to PNG
                             img.save(buffered, format="PNG")
                             img_format = "PNG" # Update format

                         base64_img = base64.b64encode(buffered.getvalue()).decode('utf-8')
                         result_parts.append({"type": f"image/{img_format.lower()}", "content": base64_img})
                         logging.info(f"Processed image part ({img_format}).")

                     except Exception as img_e:
                         logging.error(f"Error processing image data from Google GenAI: {img_e}")
                         result_parts.append({"type": "error", "content": f"Failed to process image: {img_e}"})
                else:
                     logging.warning(f"Unexpected part type in Google GenAI response: {part}")


            # Check if we got at least one image or text part
            if not result_parts:
                 logging.error("Google GenAI call succeeded but returned no parts.")
                 return {"error": "Image generation returned no content parts."}

            logging.info(f"Google GenAI image generation successful, returned {len(result_parts)} parts.")
            return result_parts
        else:
            # Handle cases where candidate is empty or content is missing
            error_detail = "No candidates or content in Google GenAI response."
            # Attempt to get feedback if available
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                 # Convert prompt_feedback to a string representation
                 feedback_str = str(response.prompt_feedback)
                 error_detail += f" Prompt Feedback: {feedback_str}"

            logging.error(f"Google GenAI response structure invalid: {error_detail}. Full Response: {response}")
            # Return a structured error dictionary
            return {"error": f"Invalid response structure from Google GenAI. Details: {error_detail}"}


    except Exception as e:
        logging.exception(f"An error occurred during Google GenAI image generation:")
        return {"error": f"An error occurred generating image: {e}"}