import google.generativeai as genai
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up Gemini API
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

print("=== AVAILABLE MODELS ===")

try:
    # List all available models
    models = genai.list_models()
    
    for model in models:
        print(f"Model Name: {model.name}")
        print(f"Display Name: {model.display_name}")
        print(f"Description: {model.description}")
        print(f"Supported Methods: {model.supported_generation_methods}")
        print("---")
        
except Exception as e:
    print(f"Error: {e}")