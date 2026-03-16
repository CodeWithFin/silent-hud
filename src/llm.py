"""
SilentHUD - Anthropic LLM Client
Handles communication with Anthropic's Claude API for generating responses.
"""

import os
from typing import Optional
from anthropic import Anthropic
from dotenv import load_dotenv
from PIL import Image
import base64
import io

# Load environment variables
load_dotenv()

# EMBEDDED KEYS
EMBEDDED_ANTHROPIC_KEY = None

class LLMClient:
    """
    Client for interacting with Anthropic API (Claude).
    Designed for concise, helpful responses suitable for overlay display.
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are SilentHUD, an intelligent, concise AI assistant tailored for coding and general tasks.
**Your Goal:** Provide direct, helpful answers to the user's questions.
- If the user asks a question, answer it clearly.
- If the user shows code, explain or fix it using markdown format.
- If the user shows an image, analyze it contextually.
- **Keep responses concise** and suitable for a HUD overlay.
- Do NOT hallucinate conversational filler ("Sure, I can help with that", "Here is the code"). Just answer directly."""

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-6"):
        """
        Initialize the Claude client.
        
        Args:
            api_key: Anthropic API key. If None, reads from ANTHROPIC_API_KEY env var.
            model: Model to use for completions. Defaults to latest sonnet.
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY") or EMBEDDED_ANTHROPIC_KEY
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in .env and not provided.")
            
        self.model = model
        self.client = Anthropic(api_key=self.api_key)
        self.system_prompt = self.DEFAULT_SYSTEM_PROMPT
        self.history = []  # Conversation history buffer
        
    def get_response(self, prompt: str, max_tokens: int = 1000) -> str:
        """
        Get a response from the LLM for text.
        """
        try:
            # Claude handles system prompt separately, history is strictly user/assistant
            messages = list(self.history)
            messages.append({"role": "user", "content": prompt})

            response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt,
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            
            # Anthropic returns a list of ContentBlocks
            response_text = response.content[0].text.strip()
            
            # Update History
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": response_text})
            if len(self.history) > 20: self.history = self.history[-20:]
            
            return response_text
            
        except Exception as e:
            return f"❌ Claude Text API Error: {str(e)}"
            
    def get_response_for_question(self, captured_text: str) -> str:
        """Process text captured via OCR."""
        prompt = f"""The following text was captured from my screen:
{captured_text}

---
**INSTRUCTION:**
Analyze the text above.
- If it is a **Question**, answer it directly.
- If it is a **Coding Problem**, solve it using clear, simple logic. Use code blocks.
- If it is a **Statement**, acknowledge or summarize it.
Answer concisely."""
        
        return self.get_response(prompt)

    def get_response_for_image(self, image_input, prompt: str = "Analyze this image and solve any problem.") -> str:
        """
        Process visual input using Claude 3.5 Sonnet.
        """
        try:
            # Convert PIL Image to Base64
            buffered = io.BytesIO()
            if isinstance(image_input, Image.Image):
                image_input.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            else:
                return "❌ Error: Invalid image input for Claude"

            messages = list(self.history)
            
            current_user_message = {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": img_str
                        }
                    },
                    {
                        "type": "text",
                        "text": prompt
                    }
                ]
            }
            messages.append(current_user_message)

            response = self.client.messages.create(
                model=self.model,
                system=self.system_prompt, # Re-inject system rules for vision
                messages=messages,
                temperature=0.1,
                max_tokens=1000
            )
            
            response_text = response.content[0].text.strip()
            
            # Store only text to save history token size
            self.history.append({"role": "user", "content": prompt})
            self.history.append({"role": "assistant", "content": response_text})
            
            if len(self.history) > 20: 
                self.history = self.history[-20:]
                
            return response_text

        except Exception as e:
            return f"❌ Claude Vision Error: {str(e)}"

    def get_transcription(self, audio_filepath: str) -> str:
        return "Audio transcription is currently disabled (Anthropic backend selected)."

# Global clients
_llm_client: Optional[LLMClient] = None

def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client

def answer_captured_text(captured_text: str) -> str:
    """Legacy text-only answer."""
    return get_llm_client().get_response_for_question(captured_text)

def answer_captured_image(image, prompt: str = "Analyze this image and solve any problem.") -> str:
    """
    Answer based on Visual Input using Claude.
    """
    return get_llm_client().get_response_for_image(image, prompt)

def answer_audio_question(audio_path: str) -> str:
    """Disabled for Anthropic backend."""
    return "🎤 *Audio mode is currently disabled in this Claude implementation workflow. Use Text or Snippet mode.*"
