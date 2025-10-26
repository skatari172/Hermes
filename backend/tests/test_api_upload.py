# tests/test_api_upload.py
"""
Test the image processing API endpoint.
This demonstrates how to upload images and get cultural analysis.
"""

import requests
import os
import sys
from pathlib import Path

def test_api_upload(image_path: str, server_url: str = "http://localhost:8000"):
    """Test image upload via API with automatic GPS extraction."""
    print(f"🚀 Testing API upload with: {image_path}")
    
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    # Test with automatic GPS extraction only
    print(f"\n📸 Testing with automatic GPS extraction...")
    
    try:
        with open(image_path, 'rb') as f:
            files = {'image_file': f}
            data = {
                'user_id': 'test_user',
                'session_id': 'test_session'
            }
            
            response = requests.post(
                f"{server_url}/api/image/process",
                files=files,
                data=data,
                timeout=60
            )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get('status') == 'success':
                print(f"✅ Image processed successfully!")
                
                data = result.get('data', {})
                
                print(f"\n📊 RESULTS:")
                print(f"📍 Coordinates: {data.get('coordinates', {})}")
                print(f"📸 Scene: {data.get('perception', {}).get('scene_summary', 'N/A')}")
                print(f"🏛️ Entity: {data.get('context', {}).get('entity_name', 'N/A')}")
                print(f"✅ Verified: {data.get('context', {}).get('entity_verified', False)}")
                print(f"📚 Cultural Facts: {data.get('wiki', {}).get('facts_found', 0)}")
                print(f"💬 Response: {data.get('response', {}).get('text', 'N/A')[:100]}...")
                
                return result
            else:
                print(f"❌ Processing failed: {result.get('message', 'Unknown error')}")
                if result.get('error_type') == 'no_gps_data':
                    print(f"💡 Suggestion: {result.get('suggestion', '')}")
                return None
        else:
            print(f"❌ API error: {response.status_code} - {response.text}")
            return None
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Could not connect to server at {server_url}")
        print(f"   Make sure the server is running: python main.py")
        return None
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return None

def main():
    """Main test function."""
    if len(sys.argv) < 2:
        print("Usage: python tests/test_api_upload.py <image_path>")
        print("\nExamples:")
        print("  # Auto-extract GPS coordinates from image")
        print("  python tests/test_api_upload.py tests/sample_images/my_photo.jpg")
        print("\nNote: Image must contain GPS metadata (EXIF data) to work.")
        print("Try using photos taken with smartphones or cameras with location enabled.")
        return
    
    image_path = sys.argv[1]
    
    # Test with automatic GPS extraction
    result = test_api_upload(image_path)
    
    if result:
        print(f"\n🎉 API Test Complete!")
        print(f"✅ Image processed successfully with GPS coordinates")
    else:
        print(f"\n⚠️ API Test Failed!")
        print(f"💡 Make sure your image contains GPS metadata (EXIF data)")
        print(f"📝 To test more images, add them to tests/sample_images/ and run:")
        print(f"   python tests/test_api_upload.py tests/sample_images/your_image.jpg")

if __name__ == "__main__":
    main()
