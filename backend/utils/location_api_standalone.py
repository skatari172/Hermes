# utils/location_api_standalone.py
"""
Standalone location API functions that don't require ADK.
This provides location API functionality without ADK dependency.
"""

import httpx
from typing import Dict, Any

def get_user_location_from_api() -> Dict[str, Any]:
    """Get user's current location from location API."""
    try:
        print("🌐 Getting user location from API...")
        
        # Call location API to get user's current location
        # Using a free IP geolocation API as an example
        # You can replace this with your preferred location API
        response = httpx.get("http://ip-api.com/json/", timeout=10)
        
        if response.status_code == 200:
            location_data = response.json()
            
            if location_data.get("status") == "success":
                lat = location_data.get("lat")
                lng = location_data.get("lon")
                city = location_data.get("city", "Unknown")
                country = location_data.get("country", "Unknown")
                
                print(f"✅ User location determined: {city}, {country}")
                print(f"📍 Coordinates: {lat}, {lng}")
                
                return {
                    "success": True,
                    "coordinates": {"lat": lat, "lng": lng},
                    "location": f"{city}, {country}",
                    "method": "location_api",
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": f"Location API returned error: {location_data.get('message', 'Unknown error')}",
                    "coordinates": None
                }
        else:
            return {
                "success": False,
                "error": f"Location API request failed: HTTP {response.status_code}",
                "coordinates": None
            }
            
    except Exception as e:
        print(f"❌ Location API error: {e}")
        return {
            "success": False,
            "error": f"Location API call failed: {str(e)}",
            "coordinates": None
        }

def process_image_location_with_api(image_data: str, image_format: str = "base64") -> Dict[str, Any]:
    """Process image location with fallback to location API."""
    try:
        print("📍 Processing image location...")
        
        # First try to extract GPS from EXIF data
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(__file__)))
        from utils.standalone_gps import process_image_location as extract_gps
        
        gps_result = extract_gps(image_data, image_format)
        
        if gps_result["success"]:
            coordinates = gps_result["coordinates"]
            lat = coordinates["lat"]
            lng = coordinates["lng"]
            
            print(f"✅ GPS coordinates extracted from EXIF: {lat}, {lng}")
            
            return {
                "success": True,
                "coordinates": coordinates,
                "method": "exif_gps",
                "error": None
            }
        else:
            print(f"⚠️ No GPS data in EXIF: {gps_result['error']}")
            print("🌐 Falling back to user location API...")
            
            # Fallback: Get user's current location from API
            location_result = get_user_location_from_api()
            
            if location_result["success"]:
                coordinates = location_result["coordinates"]
                lat = coordinates["lat"]
                lng = coordinates["lng"]
                
                print(f"✅ User location determined from API: {location_result['location']}")
                print(f"📍 Coordinates: {lat}, {lng}")
                
                return {
                    "success": True,
                    "coordinates": coordinates,
                    "method": "location_api",
                    "location_api": location_result,
                    "error": None
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not determine location: {location_result['error']}",
                    "gps_extraction": gps_result,
                    "location_api": location_result
                }
        
    except Exception as e:
        print(f"❌ Image location processing error: {e}")
        return {
            "success": False,
            "error": f"Image location processing failed: {str(e)}"
        }

if __name__ == "__main__":
    """Test the standalone location API."""
    import sys
    import base64
    
    if len(sys.argv) < 2:
        print("Usage: python utils/location_api_standalone.py <image_path>")
        print("Example: python utils/location_api_standalone.py tests/sample_images/image.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    
    try:
        # Read image file and encode to base64
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Process image location
        result = process_image_location_with_api(image_base64, "base64")
        
        print(f"\n🧪 Location API Standalone Test Results:")
        print(f"   Success: {result['success']}")
        if result['success']:
            coords = result['coordinates']
            method = result.get('method', 'unknown')
            print(f"   Method: {method}")
            print(f"   Latitude: {coords['lat']}")
            print(f"   Longitude: {coords['lng']}")
            
            if method == "location_api":
                api_data = result.get('location_api', {})
                print(f"   Location: {api_data.get('location', 'Unknown')}")
        else:
            print(f"   Error: {result['error']}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
