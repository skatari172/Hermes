# tests/test_image.py
"""
Simple test runner for image processing.
Usage: python tests/test_image.py <image_path>
"""

import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

async def test_image(image_path: str):
    """Test the complete agent pipeline with an image."""
    print("🚀 HERMES IMAGE TEST")
    print("=" * 50)
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    print(f"📸 Testing with image: {image_path}")
    
    try:
        # Import the quick test function
        from quick_test import test_with_image, encode_image_to_base64, extract_coordinates_from_image
        
        # Encode image
        image_data = encode_image_to_base64(image_path)
        if not image_data:
            return
        
        # Try to extract coordinates from image with location API fallback
        try:
            from utils.location_api_standalone import process_image_location_with_api
            
            print("📍 Processing image location with API fallback...")
            geo_result = process_image_location_with_api(image_data, "base64")
            
            if geo_result["success"]:
                coords = geo_result["coordinates"]
                method = geo_result.get("method", "unknown")
                print(f"✅ Location determined ({method}): {coords['lat']}, {coords['lng']}")
                
                if method == "location_api":
                    api_data = geo_result.get('location_api', {})
                    print(f"🌐 Location: {api_data.get('location', 'Unknown')}")
                
                lat = coords['lat']
                lng = coords['lng']
            else:
                print(f"❌ Could not determine location: {geo_result['error']}")
                print("💡 Try using a photo with GPS metadata or check your internet connection.")
                return
        except Exception as e:
            print(f"⚠️ Location processing error: {e}")
            print("❌ Could not process image location.")
            return
        
        # Run the complete test
        await test_with_image(image_path, lat, lng, None)
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python tests/test_image.py <image_path>")
        print("\nExample:")
        print("  python tests/test_image.py tests/sample_images/my_photo.jpg")
        return
    
    image_path = sys.argv[1]
    await test_image(image_path)

if __name__ == "__main__":
    asyncio.run(main())
