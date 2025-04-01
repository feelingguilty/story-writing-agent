import time
from groq import Groq, RateLimitError, APIError # Import APIError
import config

# Initialize client only if key exists
groq_client = None
if config.GROQ_API_KEY:
    groq_client = Groq(api_key=config.GROQ_API_KEY)
else:
    print("Groq client not initialized due to missing API key.")

def call_groq(prompt: str, system_prompt: str = "You are a helpful AI assistant.", model: str = config.DEFAULT_MODEL, max_retries: int = 3, initial_delay: int = 5) -> str:
    """
    Calls the Groq API with retry logic for rate limiting.

    Args:
        prompt: The user's prompt.
        system_prompt: The system message to set the AI's role.
        model: The Groq model to use.
        max_retries: Maximum number of retries on rate limit errors.
        initial_delay: Initial delay in seconds before retrying.

    Returns:
        The AI's response content as a string, or an error message prefixed with "Error:".
    """
    if not groq_client:
        return "Error: Groq API key not configured."

    delay = initial_delay
    last_error = None
    for attempt in range(max_retries):
        try:
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model=model,
                # Consider adding temperature=0.7 for more creative tasks
            )
            # Check for valid response structure
            if chat_completion.choices and chat_completion.choices[0].message:
                 return chat_completion.choices[0].message.content or "Error: Received empty response from Groq."
            else:
                 last_error = "Error: Invalid response structure from Groq."
                 print(f"Invalid response received: {chat_completion}") # Log for debugging
                 break # Don't retry if structure is wrong

        except RateLimitError as e:
            last_error = e
            print(f"Rate limit hit. Retrying in {delay} seconds... (Attempt {attempt + 1}/{max_retries})")
            time.sleep(delay)
            delay *= 2 # Exponential backoff
        except APIError as e: # Catch other API errors
            last_error = e
            print(f"An API error occurred calling Groq: {e}")
            break # Don't retry on general API errors unless specific ones are known safe
        except Exception as e: # Catch unexpected errors
            last_error = e
            print(f"An unexpected error occurred calling Groq: {e}")
            break # Don't retry unknown errors

    # If loop finishes without returning, an error occurred
    error_message = f"Error: Could not get response from Groq. Last error: {last_error}"
    if attempt == max_retries - 1 and isinstance(last_error, RateLimitError):
        error_message = f"Error: Exceeded maximum retries ({max_retries}) due to rate limiting. Last error: {last_error}"

    return error_message