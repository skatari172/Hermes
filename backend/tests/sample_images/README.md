# tests/sample_images/README.md
# Sample Images Directory

This directory is for storing test images for the Hermes agent pipeline.

## How to Use

1. **Add your test images here:**
   ```bash
   # Copy your images to this directory
   cp /path/to/your/image.jpg tests/sample_images/
   ```

2. **Test with automatic coordinate extraction:**
   ```bash
   # Extract coordinates from image EXIF data
   python tests/extract_coordinates.py tests/sample_images/your_image.jpg
   
   # Then test with the extracted coordinates
   python tests/quick_test.py tests/sample_images/your_image.jpg <lat> <lng>
   ```

3. **Test with manual coordinates:**
   ```bash
   # If no GPS data in image, use manual coordinates
   python tests/quick_test.py tests/sample_images/your_image.jpg 48.8584 2.2945 "Eiffel Tower"
   ```

## Image Requirements

- **Format**: JPG, PNG, or other common image formats
- **GPS Data**: Images with EXIF GPS data work best (photos from phones/cameras)
- **Size**: Any size (will be processed by Gemini Vision)
- **Content**: Cultural landmarks, historical sites, or interesting locations

## Sample Test Images

You can add images of:
- Famous landmarks (Eiffel Tower, Colosseum, Statue of Liberty)
- Historical sites (castles, monuments, museums)
- Cultural locations (temples, churches, traditional buildings)
- Any location with cultural or historical significance

## Example Usage

```bash
# 1. Add an image
cp my_paris_photo.jpg tests/sample_images/

# 2. Extract coordinates
python tests/extract_coordinates.py tests/sample_images/my_paris_photo.jpg

# 3. Test the pipeline
python tests/quick_test.py tests/sample_images/my_paris_photo.jpg 48.8584 2.2945 "Eiffel Tower"
```

The system will:
1. ✅ Analyze the image for visual content
2. ✅ Extract GPS coordinates (if available)
3. ✅ Get location context from coordinates
4. ✅ Research cultural/historical facts
5. ✅ Verify the entity
6. ✅ Generate cultural summary
7. ✅ Create engaging responses
8. ✅ Handle follow-up questions
