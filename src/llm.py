"""
SilentHUD - Groq LLM Client
Handles communication with Groq API for generating responses.
"""

import os
from typing import Optional
from groq import Groq
from dotenv import load_dotenv
from PIL import Image


# Load environment variables
load_dotenv()

# EMBEDDED KEYS REMOVED (Use environment variables: GROQ_API_KEY, GEMINI_API_KEY)
EMBEDDED_GROQ_KEY = None
EMBEDDED_GEMINI_KEY = None

class LLMClient:
    """
    Client for interacting with Groq API.
    Designed for concise, helpful responses suitable for overlay display.
    """
    
    # System prompt optimized for brief, direct answers
    # System prompt optimized for helpful, educational answers
    DEFAULT_SYSTEM_PROMPT = """You are SilentHUD, an intelligent, concise AI assistant.
**Your Goal:** Provide direct, helpful answers to the user's questions.
- If the user asks a question, answer it clearly.
- If the user shows code, explain or fix it.
- If the user shows an image, analyze it.
- **Keep responses concise** and suitable for a HUD overlay.
- Do NOT hallucinate conversational filler ("Sure, I can help with that"). Just answer.
"""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize the LLM client.
        
        Args:
            api_key: Groq API key. If None, reads from GROQ_API_KEY env var.
            model: Model to use for completions.
        """

        self.api_key = api_key or os.getenv("GROQ_API_KEY") or EMBEDDED_GROQ_KEY
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not found (and embedded key missing)")
            
        self.model = model
        self.client = Groq(api_key=self.api_key)
        self.system_prompt = self.DEFAULT_SYSTEM_PROMPT
        self.history = []  # Conversation history buffer
        
    def get_response(self, prompt: str, max_tokens: int = 500) -> str:
        """
        Get a response from the LLM.
        
        Args:
            prompt: The user's question or captured text
            max_tokens: Maximum response length
            
        Returns:
            The LLM's response text
        """
        try:
            # Build messages with history
            messages = [{"role": "system", "content": self.system_prompt}]
            messages.extend(self.history)
            messages.append({"role": "user", "content": prompt})

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            
            response = completion.choices[0].message.content.strip()
            
            # Update History
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": response})
            if len(self.history) > 20: self.history = self.history[-20:]
            
            return response
            
        except Exception as e:
            return f"❌ Error: {str(e)}"
            
    def get_response_for_question(self, captured_text: str) -> str:
        """
        Process captured text as a question and get an answer.
        Adds context to help the LLM understand the task.
        
        Args:
            captured_text: Text captured from screen via OCR
            
        Returns:
            The LLM's response
        """
        # Format the prompt
        prompt = f"""The following text was captured from screen:
{captured_text}

---
**INSTRUCTION:**
**INSTRUCTION:**
Analyze the text above.
- If it is a **Question**, answer it directly.
- If it is a **Coding Problem**, solve it using clear, simple logic. Use code blocks.
- If it is a **Statement**, acknowledge or summarize it.
Answer concisely."""
        
        return self.get_response(prompt)
        
    def set_system_prompt(self, prompt: str):
        """Update the system prompt."""
        self.system_prompt = prompt

    def get_response_for_image(self, image_input, prompt: str = "Solve this.") -> str:
        """
        Process visual input using Groq Vision (Llama 4 Scout).
        Args:
            image_input: PIL Image or path
            prompt: Question about image
        """
        import base64
        import io
        from PIL import Image

        try:
            # Convert PIL to Base64
            buffered = io.BytesIO()
            if isinstance(image_input, Image.Image):
                image_input.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            else:
                return "❌ Error: Invalid image input"

            # Call Groq Vision Model with History
            messages = []
            
            # Add System Prompt if needed (though Vision models sometimes ignore it, it helps context)
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
                
            # Add Conversation History
            messages.extend(self.history)
            
            # Add Current User Message (Text + Image)
            current_user_message = {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_str}"
                        }
                    }
                ]
            }
            messages.append(current_user_message)

            completion = self.client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=messages,
                temperature=0.1,
                max_tokens=1024
            )
            
            response_text = completion.choices[0].message.content.strip()
            
            # Update History (Store TEXT ONLY to save tokens/complexity)
            # We don't store the base64 image in history.
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": response_text})
            
            # Limit history to last 10 turns to prevent context explosion
            if len(self.history) > 20: 
                self.history = self.history[-20:]
                
            return response_text

        except Exception as e:
            return f"❌ Vision Error: {str(e)}"


    def get_transcription(self, audio_filepath: str) -> str:
        """Transcribe audio file using Groq Whisper."""
        try:
            with open(audio_filepath, "rb") as file_obj:
                transcription = self.client.audio.transcriptions.create(
                    file=(os.path.basename(audio_filepath), file_obj),
                    model="whisper-large-v3",
                    response_format="json",
                    language="en",
                    temperature=0.0
                )
            return transcription.text.strip()
        except Exception as e:
            return f"❌ Transcription Error: {str(e)}"

# Global clients
_groq_client: Optional[LLMClient] = None

def get_groq_client() -> LLMClient:
    global _groq_client
    if _groq_client is None:
        _groq_client = LLMClient()
    return _groq_client

def answer_captured_text(captured_text: str) -> str:
    """Legacy text-only answer (uses Groq)."""
    return get_groq_client().get_response_for_question(captured_text)

def answer_captured_image(image, prompt: str = "Analyze this image and solve any problem.") -> str:
    """
    Answer based on Visual Input (uses Groq Vision).
    """
    return get_groq_client().get_response_for_image(image, prompt)

def answer_audio_question(audio_path: str) -> str:
    """
    Transcribe audio and answer the question using History.
    """
    client = get_groq_client()
    
    # 1. Transcribe
    transcript = client.get_transcription(audio_path)
    if not transcript or "Error" in transcript:
        return f"Could not hear question: {transcript}"
        
    # 2. Add to history and answer
    # 2. Add to history and answer
    # We treat it like a direct conversation
    answer = client.get_response(transcript)
    
    # Update history manually since get_response_for_question might not (depends on impl)
    # Actually get_response_for_question uses get_response which uses system prompt but maybe not history logic I added to vision?
    # Let's fix get_response to use history too!
    
    return f"🗣️ **You asked:** \"{transcript}\"\n\n{answer}"
