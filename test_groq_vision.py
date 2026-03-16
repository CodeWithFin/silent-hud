
import os
from groq import Groq
import base64

# Embedded key from source (Masked)
API_KEY = os.getenv("GROQ_API_KEY")

def encode_image(image_path):
  with open(image_path, "rb") as image_file:
    return base64.b64encode(image_file.read()).decode('utf-8')

# Use one of the uploaded images for testing
image_path = "/home/isaacdev14/.gemini/antigravity/brain/7f3eb016-68fe-431b-ad74-0622914ad28b/uploaded_media_1769859120847.png"

try:
    client = Groq(api_key=API_KEY)
    
    base64_image = encode_image(image_path)
    
    print("Testing Groq Vision (Llama 3.2-11b-vision-preview)...")
    
    completion = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": "What is the correct answer to this multiple choice question? Explain why."
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        temperature=0.1,
        max_tokens=1024,
        top_p=1,
        stream=False,
        stop=None,
    )

    print("\n--- RESPONSE ---")
    print(completion.choices[0].message.content)
    print("----------------")
    print("✅ Success! Groq Vision is available.")

except Exception as e:
    print(f"\n❌ Error: {e}")
