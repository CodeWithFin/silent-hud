import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ No API Key found.")
    exit(1)

genai.configure(api_key=api_key)

# Models to test in order of "intelligence"
models_to_test = ["gemini-2.5-pro", "gemini-3-pro-preview", "gemini-2.0-flash"]

for model_name in models_to_test:
    print(f"\nTesting model: {model_name}...")
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content("Hello! Are you working? Reply with yes.")
        print(f"✅ Success! Response: {response.text.strip()}")
        print(f"🎉 We will use {model_name}!")
        break
    except Exception as e:
        print(f"❌ Failed: {str(e)}")
