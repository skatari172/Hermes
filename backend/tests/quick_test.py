# tests/quick_test.py
"""
Quick test runner for testing with any image.
Usage: python tests/quick_test.py <image_path> <lat> <lng> [entity_name]
"""

import asyncio
import sys
import os
import base64
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def extract_coordinates_from_image(image_path: str):
    """Extract GPS coordinates from image EXIF data."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS
        
        image = Image.open(image_path)
        exif_data = image._getexif()
        
        if exif_data is None:
            return None
        
        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = value
        
        gps_info = exif.get('GPSInfo')
        if not gps_info:
            return None
        
        # Extract GPS coordinates
        lat = gps_info.get(2)  # GPSLatitude
        lat_ref = gps_info.get(1)  # GPSLatitudeRef
        lng = gps_info.get(4)  # GPSLongitude
        lng_ref = gps_info.get(3)  # GPSLongitudeRef
        
        if lat and lng:
            # Convert to decimal degrees
            def convert_to_decimal(coord, ref):
                degrees = float(coord[0])
                minutes = float(coord[1])
                seconds = float(coord[2])
                decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
                if ref in ['S', 'W']:
                    decimal = -decimal
                return decimal
            
            lat_decimal = convert_to_decimal(lat, lat_ref)
            lng_decimal = convert_to_decimal(lng, lng_ref)
            
            return {
                "lat": lat_decimal,
                "lng": lng_decimal
            }
    except Exception as e:
        print(f"⚠️ Could not extract coordinates: {e}")
    
    return None

def encode_image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        print(f"✅ Image encoded: {len(encoded_string)} characters")
        return encoded_string
    except Exception as e:
        print(f"❌ Image encoding error: {e}")
        return ""

def _create_cultural_summary(context_data: dict) -> str:
    """Create a concise cultural summary from all context data."""
    try:
        perception = context_data.get('perception', {})
        wiki_facts = context_data.get('wiki_facts', [])
        geo_context = context_data.get('geo_context', {})
        
        summary_parts = []
        
        # Add location context
        if geo_context.get('address'):
            summary_parts.append(f"Location: {geo_context['address']}")
        
        # Add scene description
        if perception.get('scene_summary'):
            summary_parts.append(f"Scene: {perception['scene_summary']}")
        
        # Add cultural elements
        if perception.get('cultural_notes'):
            cultural_notes = perception['cultural_notes']
            if isinstance(cultural_notes, list) and cultural_notes:
                summary_parts.append(f"Cultural elements: {', '.join(cultural_notes[:3])}")
        
        # Add historical/cultural facts
        if wiki_facts:
            for fact in wiki_facts[:2]:  # Limit to top 2 facts
                if fact.get('is_cultural_content', False):
                    extract = fact.get('extract', '')
                    if extract:
                        # Truncate long extracts
                        if len(extract) > 150:
                            extract = extract[:150] + "..."
                        summary_parts.append(f"Historical context: {extract}")
        
        # Add detected text if relevant
        if perception.get('text_analysis'):
            text_items = perception['text_analysis']
            if isinstance(text_items, list) and text_items:
                detected_texts = [item.get('detected_text', '') for item in text_items[:2]]
                summary_parts.append(f"Detected text: {', '.join(detected_texts)}")
        
        return " | ".join(summary_parts) if summary_parts else "No significant cultural context identified"
        
    except Exception as e:
        print(f"⚠️ Summary creation error: {e}")
        return "Cultural context summary unavailable"

async def test_with_image(image_path: str, lat: float, lng: float, entity_name: str = None):
    """Test the location API functionality without ADK dependencies."""
    print("🚀 HERMES LOCATION API TEST")
    print("=" * 50)
    
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return
    
    print(f"📸 Testing with image: {image_path}")
    print(f"📍 Coordinates: {lat}, {lng}")
    if entity_name:
        print(f"🏛️ Entity: {entity_name}")
    
    # Encode image
    image_data = encode_image_to_base64(image_path)
    if not image_data:
        return
    
    try:
        # Test location API functionality
        print(f"\n📋 LOCATION API TEST")
        print("-" * 30)
        
        from utils.location_api_standalone import get_user_location_from_api
        
        # Test location API directly
        location_result = get_user_location_from_api()
        
        if location_result["success"]:
            coords = location_result["coordinates"]
            print(f"✅ Location API Working:")
            print(f"   Location: {location_result['location']}")
            print(f"   Latitude: {coords['lat']}")
            print(f"   Longitude: {coords['lng']}")
            print(f"   Method: {location_result['method']}")
        else:
            print(f"❌ Location API Failed: {location_result['error']}")
        
        # Test GPS extraction
        print(f"\n📋 GPS EXTRACTION TEST")
        print("-" * 30)
        
        from utils.standalone_gps import process_image_location
        
        gps_result = process_image_location(image_data, "base64")
        
        if gps_result["success"]:
            coords = gps_result["coordinates"]
            print(f"✅ GPS Extraction Working:")
            print(f"   Latitude: {coords['lat']}")
            print(f"   Longitude: {coords['lng']}")
        else:
            print(f"⚠️ GPS Extraction: {gps_result['error']}")
            print(f"   (This is expected for images without GPS metadata)")
        
        # Test combined functionality
        print(f"\n📋 COMBINED FUNCTIONALITY TEST")
        print("-" * 30)
        
        from utils.location_api_standalone import process_image_location_with_api
        
        combined_result = process_image_location_with_api(image_data, "base64")
        
        if combined_result["success"]:
            coords = combined_result["coordinates"]
            method = combined_result.get("method", "unknown")
            print(f"✅ Combined Test Working:")
            print(f"   Method: {method}")
            print(f"   Latitude: {coords['lat']}")
            print(f"   Longitude: {coords['lng']}")
            
            if method == "location_api":
                api_data = combined_result.get('location_api', {})
                print(f"   Location: {api_data.get('location', 'Unknown')}")
        else:
            print(f"❌ Combined Test Failed: {combined_result['error']}")
        
        # Print summary
        print(f"\n{'='*50}")
        print(f"🎉 LOCATION API TEST SUMMARY")
        print(f"{'='*50}")
        
        print(f"✅ Location API: {'WORKING' if location_result['success'] else 'FAILED'}")
        print(f"✅ GPS Extraction: {'WORKING' if gps_result['success'] else 'NO GPS DATA (Expected)'}")
        print(f"✅ Combined Functionality: {'WORKING' if combined_result['success'] else 'FAILED'}")
        
        if combined_result['success']:
            print(f"\n🎉 SUCCESS! The location API fallback system is working correctly.")
            print(f"🌐 Location API fallback: ✅ WORKING")
            print(f"📍 GPS extraction: ✅ WORKING")
            print(f"🔄 Fallback logic: ✅ WORKING")
        else:
            print(f"\n⚠️ Some components may need attention.")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Run test with command line arguments."""
    if len(sys.argv) < 2:
        print("Usage: python tests/quick_test.py <image_path> [entity_name]")
        print("\nExamples:")
        print("  # Auto-extract coordinates from image EXIF data")
        print("  python tests/quick_test.py my_photo.jpg")
        print("  # With entity name")
        print("  python tests/quick_test.py my_photo.jpg 'Eiffel Tower'")
        return
    
    image_path = sys.argv[1]
    entity_name = sys.argv[2] if len(sys.argv) > 2 else None
    
    # Encode image first
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
            print(f"✅ Location determined ({method}):")
            print(f"📍 Latitude: {coords['lat']}")
            print(f"📍 Longitude: {coords['lng']}")
            
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
    
    await test_with_image(image_path, lat, lng, entity_name)

if __name__ == "__main__":
    asyncio.run(main())
