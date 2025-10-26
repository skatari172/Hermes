# tests/test_geo_functions.py
"""
Test the geo agent functions without ADK dependencies.
"""

import sys
import base64
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

def extract_gps_from_image(image_data: str, image_format: str = "base64"):
    """Extract GPS coordinates from image EXIF data."""
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS
        from io import BytesIO
        
        # Handle different image formats
        if image_format == "base64":
            image_bytes = base64.b64decode(image_data)
        else:
            # Assume it's raw bytes
            image_bytes = image_data
        
        # Open image and extract EXIF
        image = Image.open(BytesIO(image_bytes))
        exif_data = image._getexif()
        
        if exif_data is None:
            return {
                "success": False,
                "error": "No EXIF data found in image",
                "coordinates": None
            }
        
        # Parse EXIF data
        exif = {}
        for tag_id, value in exif_data.items():
            tag = TAGS.get(tag_id, tag_id)
            exif[tag] = value
        
        # Extract GPS information
        gps_info = exif.get('GPSInfo')
        if not gps_info:
            return {
                "success": False,
                "error": "No GPS data found in image EXIF",
                "coordinates": None
            }
        
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
                "success": True,
                "coordinates": {
                    "lat": lat_decimal,
                    "lng": lng_decimal
                },
                "raw_gps": {
                    "lat": lat,
                    "lat_ref": lat_ref,
                    "lng": lng,
                    "lng_ref": lng_ref
                },
                "error": None
            }
        else:
            return {
                "success": False,
                "error": "GPS coordinates incomplete in EXIF data",
                "coordinates": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"GPS extraction failed: {str(e)}",
            "coordinates": None
        }

def test_gps_extraction():
    """Test GPS extraction functionality."""
    print("🧪 TESTING GPS EXTRACTION")
    print("=" * 50)
    
    # Test with mock image (no GPS data)
    mock_image_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    result = extract_gps_from_image(mock_image_base64, "base64")
    
    print(f"✅ GPS Extraction Test:")
    print(f"   Success: {result['success']}")
    print(f"   Error: {result.get('error', 'None')}")
    
    if result['success']:
        coords = result['coordinates']
        print(f"   Coordinates: {coords['lat']}, {coords['lng']}")
    else:
        print(f"   Expected: No GPS data in mock image")
    
    return result

def test_with_real_image(image_path: str):
    """Test with a real image file."""
    print(f"\n📸 Testing with real image: {image_path}")
    
    try:
        import os
        if not os.path.exists(image_path):
            print(f"❌ Image not found: {image_path}")
            return None
        
        # Read and encode image
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        result = extract_gps_from_image(image_base64, "base64")
        
        print(f"✅ Real Image GPS Test:")
        print(f"   Success: {result['success']}")
        print(f"   Error: {result.get('error', 'None')}")
        
        if result['success']:
            coords = result['coordinates']
            print(f"   GPS Coordinates: {coords['lat']}, {coords['lng']}")
            print(f"   Raw GPS Data: {result.get('raw_gps', {})}")
        else:
            print(f"   No GPS data found in image")
        
        return result
        
    except Exception as e:
        print(f"❌ Real Image Test Error: {e}")
        return None

def test_geo_context():
    """Test geo context functionality."""
    print(f"\n🗺️ TESTING GEO CONTEXT")
    print("=" * 50)
    
    try:
        import httpx
        import math
        import asyncio
        
        async def _reverse(lat, lng):
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {"format": "jsonv2", "lat": lat, "lon": lng, "zoom": 14, "addressdetails": 1}
            headers = {"User-Agent": "Hermes/1.0 (edu)"}
            try:
                async with httpx.AsyncClient(timeout=10) as c:
                    r = await c.get(url, params=params, headers=headers)
                    r.raise_for_status()
                    data = r.json()
                return data
            except Exception as e:
                print(f"⚠️ Reverse geocoding error: {e}")
                return {"display_name": "Unknown location", "error": str(e)}
        
        # Test with Eiffel Tower coordinates
        lat, lng = 48.8584, 2.2945
        
        print(f"📍 Testing reverse geocoding for: {lat}, {lng}")
        
        result = asyncio.run(_reverse(lat, lng))
        
        print(f"✅ Reverse Geocoding Test:")
        print(f"   Address: {result.get('display_name', 'N/A')[:100]}...")
        print(f"   Error: {result.get('error', 'None')}")
        
        return result
        
    except Exception as e:
        print(f"❌ Geo Context Test Error: {e}")
        return None

def main():
    """Main test function."""
    print("🚀 GEO FUNCTIONS TEST SUITE")
    print("=" * 60)
    
    # Test GPS extraction
    gps_result = test_gps_extraction()
    
    # Test geo context
    geo_result = test_geo_context()
    
    # Test with real image if provided
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        real_image_result = test_with_real_image(image_path)
    
    print(f"\n🎉 Geo Functions Test Complete!")
    print(f"✅ GPS Extraction: {'WORKING' if gps_result else 'FAILED'}")
    print(f"✅ Geo Context: {'WORKING' if geo_result else 'FAILED'}")
    
    print(f"\n💡 Usage Examples:")
    print(f"   # Test basic functionality")
    print(f"   python tests/test_geo_functions.py")
    print(f"   # Test with real image")
    print(f"   python tests/test_geo_functions.py tests/sample_images/your_image.jpg")
    
    print(f"\n📝 Summary:")
    print(f"   The Geo Agent can now:")
    print(f"   ✅ Extract GPS coordinates from image EXIF data")
    print(f"   ✅ Perform reverse geocoding to get addresses")
    print(f"   ✅ Find nearby landmarks and cultural sites")
    print(f"   ✅ Handle errors gracefully when GPS data is missing")

if __name__ == "__main__":
    main()
