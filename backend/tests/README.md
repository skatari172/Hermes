# tests/README.md
# Hermes Agent Pipeline Test Suite

Simple tests for the Hermes agent pipeline.

## Quick Start

### 1. Add Your Image
```bash
# Copy your image to the sample images folder
cp your_photo.jpg tests/sample_images/
```

### 2. Run the Test
```bash
# Test with automatic GPS extraction
python tests/test_image.py tests/sample_images/your_photo.jpg
```

That's it! The system will:
- ✅ Extract GPS coordinates from your image
- ✅ Analyze the image content
- ✅ Get location context and nearby landmarks
- ✅ Research cultural/historical facts
- ✅ Generate a cultural response
- ✅ Test follow-up questions

## Available Tests

### `test_image.py` - Main Test
**Tests the complete pipeline with your image.**

```bash
python tests/test_image.py tests/sample_images/your_photo.jpg
```

### `quick_test.py` - Detailed Test
**More detailed output with step-by-step results.**

```bash
python tests/quick_test.py tests/sample_images/your_photo.jpg
```

### `test_geo_functions.py` - Geo Agent Test
**Test just the GPS extraction and location features.**

```bash
python tests/test_geo_functions.py tests/sample_images/your_photo.jpg
```

### `test_api_upload.py` - API Test
**Test via the API endpoint.**

```bash
# Start server first
python main.py

# Then test
python tests/test_api_upload.py tests/sample_images/your_photo.jpg
```

## What Gets Tested

1. **📸 Image Analysis**: Visual content, objects, text recognition
2. **📍 GPS Extraction**: Automatic coordinate extraction from EXIF data
3. **🗺️ Location Context**: Address and nearby landmarks
4. **📚 Cultural Research**: Historical and cultural facts
5. **🧠 Entity Verification**: AI-powered entity identification
6. **💬 Response Generation**: Cultural responses with Hermes personality
7. **🔄 Follow-up Questions**: Context-aware conversation

## Expected Results

A successful test should show:
- ✅ GPS coordinates extracted from image
- ✅ Entity verified (high confidence)
- ✅ Cultural facts found (>0)
- ✅ Response generated (engaging, cultural)
- ✅ Follow-up questions answered (context-aware)

## Image Requirements

- **Format**: JPG, PNG, or other common formats
- **GPS Data**: Images with EXIF GPS data work best (photos from phones/cameras)
- **Content**: Cultural landmarks, historical sites, or interesting locations

## Troubleshooting

**No GPS coordinates found?**
- Use manual coordinates: `python tests/quick_test.py image.jpg 48.8584 2.2945 "Eiffel Tower"`

**ADK import errors?**
- Use `test_geo_functions.py` for core functionality testing

**API connection errors?**
- Make sure server is running: `python main.py`

## Sample Output

```
🚀 HERMES IMAGE TEST
==================================================
📸 Testing with image: tests/sample_images/my_photo.jpg
📍 Extracting GPS coordinates using Geo Agent...
✅ GPS coordinates extracted: 48.8584, 2.2945

📋 STEP 1: PERCEPTION AGENT - Image Analysis
------------------------------------------------------------
✅ Scene Summary: A famous iron tower structure in Paris, France...
✅ Objects Detected: 3
✅ Text Analysis: 2
✅ Cultural Notes: ['Iron lattice architecture', 'Historic monument']

📋 STEP 2: GEO AGENT - Location Context
------------------------------------------------------------
✅ Address: Champ de Mars, 7th arrondissement, Paris, France
✅ Landmarks Found: 3

📋 STEP 3: WIKI AGENT - Cultural Research
------------------------------------------------------------
✅ Facts Found: 2
   - Eiffel Tower: Cultural Relevance: 0.95

📋 STEP 4: CONTEXT AGENT - Entity Verification
------------------------------------------------------------
✅ Entity Verified: True
✅ Entity Name: Eiffel Tower
✅ Certainty: 0.95

📋 STEP 5: RESPONSE AGENT - Cultural Response
------------------------------------------------------------
✅ Response Generated: Wow! You're looking at the Eiffel Tower...

📋 STEP 6: FOLLOW-UP QUESTIONS
------------------------------------------------------------
📝 Follow-up Question 1: What's the history of this place?
✅ Response: The Eiffel Tower has a fascinating history...

🎉 SUCCESS! The agent pipeline is working correctly.
🏛️ Cultural & historical retrieval: ✅ WORKING
💬 Follow-up question handling: ✅ WORKING
```

The system successfully retrieves historical and cultural information and uses it to answer follow-up questions with rich, engaging responses! 🏛️✨