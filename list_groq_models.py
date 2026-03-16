
import os
from groq import Groq

# Embedded key removed for security. Please set GROQ_API_KEY environment variable.
API_KEY = os.getenv("GROQ_API_KEY")

try:
    client = Groq(api_key=API_KEY)
    models = client.models.list()
    
    print("Available Groq Models:")
    for model in models.data:
        print(f" - {model.id}")
        
except Exception as e:
    print(f"Error: {e}")
