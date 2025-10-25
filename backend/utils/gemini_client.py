# Gemini Vision/Text wrappers
import google.generativeai as genai
import os
from typing import Optional

class GeminiClient:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found in environment variables")
        
        genai.configure(api_key=self.api_key)
        # Use Gemini 2.5 Flash Image - optimized for OCR and image intelligence
        self.model = genai.GenerativeModel('gemini-2.5-flash-image')
    
    def generate_text(self, prompt: str) -> str:
        """Generate text response from Gemini"""
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            raise Exception(f"Error generating text: {str(e)}")
    
    def analyze_image(self, image_path: str, prompt: str) -> str:
        """Analyze image with Gemini Vision"""
        try:
            import PIL.Image
            image = PIL.Image.open(image_path)
            response = self.model.generate_content([prompt, image])
            return response.text
        except Exception as e:
            raise Exception(f"Error analyzing image: {str(e)}")
    
    def test_connection(self) -> bool:
        """Test if Gemini API connection is working"""
        try:
            response = self.generate_text("Hello! Are you working? Please respond with 'Yes, I am working!'")
            return "working" in response.lower()
        except Exception as e:
            print(f"Connection test failed: {str(e)}")
            return False


# Create singleton instance
try:
    gemini_client = GeminiClient()
except ValueError as e:
    print(f"Warning: {str(e)}")
    gemini_client = None