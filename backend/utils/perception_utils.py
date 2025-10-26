"""
Perception Agent Utilities
Standalone functions for image analysis with translation priority
"""
import os
import json
import base64
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

load_dotenv()


async def analyze_image_with_translation(image_data: str, image_format: str = "base64") -> dict:
    """Analyze image with priority on OCR and translation."""
    try:
        print("🔍 Analyzing image with OCR and translation priority...")
        
        # Use Gemini for image analysis with translation focus
        from google.generativeai import GenerativeModel
        import google.generativeai as genai
        
        # Configure API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ GEMINI_API_KEY not found in environment variables")
            return {
                "success": False,
                "error": "Google API key not configured",
                "scene_summary": "Unable to analyze image - API key missing",
                "translated_text": [],
                "cultural_landmarks": [],
                "architectural_style": "",
                "cultural_elements": [],
                "atmosphere": "",
                "cultural_notes": []
            }
        
        genai.configure(api_key=api_key)
        model = GenerativeModel("gemini-2.5-flash")
        
        # Handle different image formats
        if image_format == "base64":
            image_bytes = base64.b64decode(image_data)
        else:
            image_bytes = image_data
        
        # Create image object
        image = Image.open(BytesIO(image_bytes))
        
        # Prompt that prioritizes translation above all else - NO ASTERISKS
        prompt = """You are a multilingual OCR and translation expert. Your PRIMARY and MOST IMPORTANT task is to detect and translate ALL foreign text in this image.

CRITICAL PRIORITIES (in this exact order):
1. FIRST and FOREMOST: Scan the entire image for ANY text visible (signs, menus, documents, labels, street signs, etc.)
2. TRANSLATE every piece of text you find - convert to English
3. IDENTIFY the source language of each text
4. If there is ANY text in a foreign language, that MUST be your main focus and MUST be output

IMPORTANT TRANSLATION RULES:
- Look for text on signs, menus, documents, walls, vehicles, clothing, etc.
- Translate EVERYTHING - even small text
- Include the original text, English translation, and detected language
- If you see foreign characters (Chinese, Arabic, Japanese, etc.), translate them
- Be thorough - check all parts of the image for text

ADDITIONAL ANALYSIS (only after translation):
- Identify cultural landmarks
- Note architectural styles
- Describe cultural elements
- Assess atmosphere

CRITICAL FORMATTING RULES FOR YOUR RESPONSE:
- NO asterisks (*) in any output
- NO bold formatting in any output
- Plain text only in translations and summaries
- NEVER mention coordinates, latitude, or longitude in any descriptions
- Keep all text clean and simple

Provide your analysis in this JSON format:
{
    "scene_summary": "Brief description focusing on what text was found and translated",
    "translated_text": [
        {"original": "complete original foreign text", "translation": "complete English translation", "language": "detected language"},
        {"original": "another text", "translation": "translation", "language": "language"}
    ],
    "cultural_landmarks": ["list of landmarks"],
    "architectural_style": "description",
    "cultural_elements": ["elements"],
    "atmosphere": "description",
    "cultural_notes": ["observations"]
}

TRANSLATION IS YOUR TOP PRIORITY - BE THOROUGH!"""
        
        # Use generation config to emphasize translation
        response = model.generate_content(
            [prompt, image],
            generation_config={
                "temperature": 0.1,  # Lower temperature for more focused analysis
                "max_output_tokens": 2048
            }
        )
        response_text = response.text.strip()
        
        # Try to parse JSON response
        try:
            analysis_data = json.loads(response_text)
            translations = analysis_data.get('translated_text', [])
            print(f"✅ Image analysis complete with {len(translations)} translations")
            if translations:
                print("📝 DETECTED TRANSLATIONS:")
                for i, trans in enumerate(translations, 1):
                    print(f"  {i}. [{trans.get('language', 'unknown')}] {trans.get('original', '')} → {trans.get('translation', '')}")
            return {
                "success": True,
                "scene_summary": analysis_data.get("scene_summary", ""),
                "translated_text": analysis_data.get("translated_text", []),
                "cultural_landmarks": analysis_data.get("cultural_landmarks", []),
                "architectural_style": analysis_data.get("architectural_style", ""),
                "cultural_elements": analysis_data.get("cultural_elements", []),
                "atmosphere": analysis_data.get("atmosphere", ""),
                "cultural_notes": analysis_data.get("cultural_notes", [])
            }
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "success": True,
                "scene_summary": response_text[:200] + "...",
                "translated_text": [],
                "cultural_landmarks": [],
                "architectural_style": "",
                "cultural_elements": [],
                "atmosphere": "",
                "cultural_notes": []
            }
        
    except Exception as e:
        print(f"❌ Image analysis error: {e}")
        return {
            "success": False,
            "error": f"Image analysis failed: {str(e)}",
            "scene_summary": "Unable to analyze image",
            "translated_text": [],
            "cultural_landmarks": [],
            "architectural_style": "",
            "cultural_elements": [],
            "atmosphere": "",
            "cultural_notes": []
        }

