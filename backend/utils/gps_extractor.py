# utils/gps_extractor.py
"""
Standalone GPS coordinate extraction from image EXIF data.
This module doesn't depend on ADK and can be used independently.
"""

import base64
from PIL import Image
from PIL.ExifTags import TAGS
from io import BytesIO
from typing import Dict, Any, Optional

def extract_gps_from_image(image_data: str, image_format: str = "base64") -> Dict[str, Any]:
    """
    Extract GPS coordinates from image EXIF data.
    
    Args:
        image_data: Image data as base64 string or raw bytes
        image_format: Format of image_data ("base64" or "bytes")
        
    Returns:
        Dictionary with success status, coordinates, and error info
    """
    try:
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
                "error": None
            }
        else:
            return {
                "success": False,
                "error": "GPS coordinates not found in EXIF data",
                "coordinates": None
            }
            
    except Exception as e:
        return {
            "success": False,
            "error": f"Error extracting GPS: {str(e)}",
            "coordinates": None
        }

def process_image_location(image_data: str, image_format: str = "base64") -> Dict[str, Any]:
    """
    Extract GPS coordinates from image and return simplified result.
    This is a standalone version that doesn't depend on ADK.
    
    Args:
        image_data: Image data as base64 string or raw bytes
        image_format: Format of image_data ("base64" or "bytes")
        
    Returns:
        Dictionary with success status, coordinates, and error info
    """
    try:
        print("📍 Extracting GPS coordinates from image...")
        
        # Extract GPS coordinates from image
        gps_result = extract_gps_from_image(image_data, image_format)
        
        if not gps_result["success"]:
            return {
                "success": False,
                "error": gps_result["error"],
                "coordinates": None
            }
        
        coordinates = gps_result["coordinates"]
        lat = coordinates["lat"]
        lng = coordinates["lng"]
        
        print(f"✅ GPS coordinates extracted: {lat}, {lng}")
        
        return {
            "success": True,
            "coordinates": coordinates,
            "error": None
        }
        
    except Exception as e:
        print(f"❌ GPS extraction error: {e}")
        return {
            "success": False,
            "error": f"GPS extraction failed: {str(e)}",
            "coordinates": None
        }

def test_gps_extraction(image_path: str) -> Dict[str, Any]:
    """
    Test GPS extraction with a local image file.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Dictionary with extraction results
    """
    try:
        # Read image file and encode to base64
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        
        # Extract GPS coordinates
        result = extract_gps_from_image(image_base64, "base64")
        
        print(f"🧪 GPS Extraction Test Results:")
        print(f"   Success: {result['success']}")
        if result['success']:
            coords = result['coordinates']
            print(f"   Latitude: {coords['lat']}")
            print(f"   Longitude: {coords['lng']}")
        else:
            print(f"   Error: {result['error']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return {
            "success": False,
            "error": f"Test failed: {str(e)}",
            "coordinates": None
        }

if __name__ == "__main__":
    """Test the GPS extraction with a sample image."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python utils/gps_extractor.py <image_path>")
        print("Example: python utils/gps_extractor.py tests/sample_images/image.png")
        sys.exit(1)
    
    image_path = sys.argv[1]
    test_gps_extraction(image_path)
