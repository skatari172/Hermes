"""
Firebase Storage client for handling image uploads and retrieval.
Provides blob storage functionality for user-uploaded images.
"""

import uuid
import os
from datetime import datetime
from typing import Optional, Dict, Any
import io
from PIL import Image
import base64

from firebase_admin import storage
from config.logger import get_logger

logger = get_logger(__name__)

class StorageClient:
    """Firebase Storage client for image handling with local fallback."""
    
    def __init__(self):
        """Initialize storage client."""
        # Try different bucket name formats
        possible_bucket_names = [
            "hermes-521f9.appspot.com",  # Standard format
            "hermes-521f9.firebasestorage.app",  # New format
            "hermes-521f9"  # Project ID only
        ]
        
        self.bucket = None
        self.bucket_name = None
        self.use_local_storage = False
        
        # Setup local storage directory as fallback
        self.local_storage_dir = os.path.join(os.getcwd(), "uploads")
        os.makedirs(self.local_storage_dir, exist_ok=True)
        
        for bucket_name in possible_bucket_names:
            try:
                self.bucket = storage.bucket(bucket_name)
                self.bucket_name = bucket_name
                logger.info(f"✅ Firebase Storage initialized with bucket: {bucket_name}")
                break
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize bucket {bucket_name}: {str(e)}")
                continue
        
        if not self.bucket:
            logger.error("❌ Failed to initialize Firebase Storage with any bucket name")
            # Try default bucket
            try:
                self.bucket = storage.bucket()
                self.bucket_name = "default"
                logger.info("✅ Using default Firebase Storage bucket")
            except Exception as e:
                logger.error(f"❌ Failed to initialize default Firebase Storage bucket: {str(e)}")
                logger.warning("🔄 Falling back to local storage")
                self.bucket = None
                self.use_local_storage = True
    
    def _save_image_locally(self, image_data: bytes, user_id: str, file_extension: str) -> str:
        """Save image locally and return URL."""
        try:
            # Create user directory
            user_dir = os.path.join(self.local_storage_dir, user_id)
            os.makedirs(user_dir, exist_ok=True)
            
            # Generate filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{unique_id}.{file_extension}"
            
            # Save file
            file_path = os.path.join(user_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # Return local URL (assuming backend serves static files)
            local_url = f"http://localhost:8000/uploads/{user_id}/{filename}"
            logger.info(f"💾 Image saved locally: {file_path}")
            return local_url
            
        except Exception as e:
            logger.error(f"❌ Local image save failed: {str(e)}")
            return None
    
    def _generate_image_path(self, user_id: str, file_extension: str) -> str:
        """Generate unique path for image storage."""
        timestamp = datetime.utcnow().strftime("%Y/%m/%d")
        unique_id = str(uuid.uuid4())
        return f"user_images/{user_id}/{timestamp}/{unique_id}.{file_extension}"
    
    def _process_image(self, image_data: bytes, max_size: tuple = (1920, 1080), quality: int = 85) -> bytes:
        """
        Process and optimize image for storage.
        
        Args:
            image_data: Raw image bytes
            max_size: Maximum dimensions (width, height)
            quality: JPEG quality (1-95)
            
        Returns:
            Processed image bytes
        """
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary (for JPEG compatibility)
            if image.mode in ("RGBA", "LA", "P"):
                image = image.convert("RGB")
            
            # Resize if image is too large
            if image.size[0] > max_size[0] or image.size[1] > max_size[1]:
                image.thumbnail(max_size, Image.Resampling.LANCZOS)
                logger.info(f"📏 Resized image to {image.size}")
            
            # Save as optimized JPEG
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality, optimize=True)
            processed_data = output.getvalue()
            
            logger.info(f"📸 Image processed: {len(image_data)} bytes → {len(processed_data)} bytes")
            return processed_data
            
        except Exception as e:
            logger.error(f"❌ Image processing failed: {str(e)}")
            return image_data  # Return original if processing fails
    
    async def upload_image(
        self, 
        image_data: bytes, 
        user_id: str, 
        content_type: str = "image/jpeg",
        process_image: bool = True
    ) -> Optional[str]:
        """
        Upload image to Firebase Storage or local storage as fallback.
        
        Args:
            image_data: Image bytes
            user_id: User identifier
            content_type: Image MIME type
            process_image: Whether to optimize image before upload
            
        Returns:
            Public URL of uploaded image or None if failed
        """
        try:
            logger.info(f"📸 Starting image upload for user {user_id}, size: {len(image_data)} bytes")
            
            # Process image if requested
            if process_image and content_type.startswith("image/"):
                logger.info("🔄 Processing image before upload")
                image_data = self._process_image(image_data)
                logger.info(f"✅ Image processed, new size: {len(image_data)} bytes")
            
            # Determine file extension
            # Determine file extension
            extension_map = {
                "image/jpeg": "jpg",
                "image/jpg": "jpg", 
                "image/png": "png",
                "image/webp": "webp"
            }
            file_extension = extension_map.get(content_type, "jpg")

            # Use a deterministic uploads path for chat images: uploads/{user_id}/{timestamp}_{uuid}.{ext}
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S%f")
            unique_id = str(uuid.uuid4())[:8]
            filename = f"{timestamp}_{unique_id}.{file_extension}"
            storage_path = f"uploads/{user_id}/{filename}"

            # Try Firebase Storage first
            if self.bucket and not self.use_local_storage:
                try:
                    logger.info(f"📁 Firebase storage path: {storage_path}")
                    
                    # Upload to Firebase Storage at the deterministic path
                    blob = self.bucket.blob(storage_path)
                    logger.info(f"🔄 Uploading to Firebase Storage...")
                    blob.upload_from_string(
                        image_data,
                        content_type=content_type
                    )
                    logger.info(f"✅ File uploaded successfully to {storage_path}")

                    # Make the blob publicly accessible if possible
                    try:
                        blob.make_public()
                    except Exception:
                        logger.warning("Could not make blob public; it may require signed URLs or bucket rules")

                    public_url = getattr(blob, 'public_url', None)
                    if public_url:
                        logger.info(f"✅ Firebase upload successful: {public_url}")
                        return public_url
                    else:
                        logger.info("🔗 Firebase upload returned no public_url; returning storage path")
                        return storage_path

                except Exception as firebase_error:
                    logger.error(f"❌ Firebase Storage upload failed: {str(firebase_error)}")
                    logger.warning("🔄 Falling back to local storage")
                    # Additional debugging hints
                    if "403" in str(firebase_error) or "Forbidden" in str(firebase_error):
                        logger.error("❌ Firebase Storage permission denied - check service account permissions")
                    elif "404" in str(firebase_error) or "not found" in str(firebase_error).lower():
                        logger.error("❌ Firebase Storage bucket not found - check bucket name configuration")
                    elif "401" in str(firebase_error) or "Unauthorized" in str(firebase_error):
                        logger.error("❌ Firebase Storage authentication failed - check service account key")
            
            # Use local storage as fallback
            logger.info("💾 Using local storage for image upload")
            local_url = self._save_image_locally(image_data, user_id, file_extension)
            
            if local_url:
                logger.info(f"✅ Local storage upload successful: {local_url}")
                return local_url
            else:
                logger.error("❌ Both Firebase and local storage failed")
                return None
            
        except Exception as e:
            logger.error(f"❌ Image upload completely failed: {str(e)}")
            import traceback
            logger.error(f"Upload error traceback: {traceback.format_exc()}")
            return None
    
    async def upload_image_base64(
        self, 
        base64_data: str, 
        user_id: str,
        process_image: bool = True
    ) -> Optional[str]:
        """
        Upload base64 encoded image to Firebase Storage.
        
        Args:
            base64_data: Base64 encoded image (with or without data URL prefix)
            user_id: User identifier
            process_image: Whether to optimize image before upload
            
        Returns:
            Public URL of uploaded image or None if failed
        """
        try:
            # Remove data URL prefix if present
            if base64_data.startswith("data:"):
                # Extract content type and base64 data
                header, base64_data = base64_data.split(",", 1)
                content_type = header.split(":")[1].split(";")[0]
            else:
                content_type = "image/jpeg"  # Default
            
            # Decode base64
            image_data = base64.b64decode(base64_data)
            
            # Upload using bytes method
            return await self.upload_image(
                image_data=image_data,
                user_id=user_id,
                content_type=content_type,
                process_image=process_image
            )
            
        except Exception as e:
            logger.error(f"❌ Base64 image upload failed: {str(e)}")
            return None
    
    def get_image_metadata(self, public_url: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for an uploaded image.
        
        Args:
            public_url: Public URL of the image
            
        Returns:
            Image metadata or None if not found
        """
        try:
            # Extract storage path from public URL
            if self.bucket_name not in public_url:
                return None
            
            # Parse the storage path from URL
            path_start = public_url.find(f"{self.bucket_name}/o/") + len(f"{self.bucket_name}/o/")
            path_end = public_url.find("?")
            if path_end == -1:
                path_end = len(public_url)
            
            storage_path = public_url[path_start:path_end].replace("%2F", "/")
            
            # Get blob metadata
            blob = self.bucket.blob(storage_path)
            if blob.exists():
                blob.reload()
                return {
                    "name": blob.name,
                    "size": blob.size,
                    "content_type": blob.content_type,
                    "created": blob.time_created.isoformat() if blob.time_created else None,
                    "updated": blob.updated.isoformat() if blob.updated else None,
                    "public_url": public_url
                }
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get image metadata: {str(e)}")
            return None

    async def upload_profile_image(
        self,
        image_data: bytes,
        user_id: str,
        content_type: str = "image/jpeg",
        process_image: bool = True
    ) -> Optional[str]:
        """
        Upload a user's profile image to a deterministic location.

        This stores the file at `profile/{user_id}.{ext}` in the Firebase bucket
        when available, or at `uploads/profile/{user_id}.{ext}` on local disk.

        Returns the public URL or None on failure.
        """
        try:
            logger.info(f"📸 Starting profile image upload for user {user_id} size={len(image_data)}")

            # Optionally process image
            if process_image and content_type.startswith("image/"):
                logger.info("🔄 Processing profile image before upload")
                image_data = self._process_image(image_data)

            extension_map = {
                "image/jpeg": "jpg",
                "image/jpg": "jpg",
                "image/png": "png",
                "image/webp": "webp"
            }
            file_extension = extension_map.get(content_type, "jpg")

            # Try Firebase Storage first
            if self.bucket and not self.use_local_storage:
                try:
                    storage_path = f"profile/{user_id}.{file_extension}"
                    logger.info(f"📁 Firebase profile storage path: {storage_path}")
                    blob = self.bucket.blob(storage_path)
                    blob.upload_from_string(image_data, content_type=content_type)
                    # Make public if possible
                    try:
                        blob.make_public()
                    except Exception:
                        logger.warning("Could not make profile blob public; relying on signed URLs or bucket rules")

                    public_url = getattr(blob, 'public_url', None)
                    if public_url:
                        logger.info(f"✅ Firebase profile upload successful: {public_url}")
                        return public_url
                    else:
                        # Construct a gs:// style or fallback URL
                        logger.info("🔗 Firebase upload returned no public_url; constructing path")
                        return f"{storage_path}"

                except Exception as firebase_error:
                    logger.error(f"❌ Firebase profile upload failed: {str(firebase_error)}")
                    logger.warning("🔄 Falling back to local profile storage")

            # Local storage fallback (deterministic filename)
            logger.info("💾 Using local storage for profile image")
            try:
                profile_dir = os.path.join(self.local_storage_dir, "profile")
                os.makedirs(profile_dir, exist_ok=True)
                filename = f"{user_id}.{file_extension}"
                file_path = os.path.join(profile_dir, filename)
                with open(file_path, 'wb') as f:
                    f.write(image_data)

                local_url = f"http://localhost:8000/uploads/profile/{filename}"
                logger.info(f"✅ Local profile image saved: {file_path} -> {local_url}")
                return local_url
            except Exception as e:
                logger.error(f"❌ Saving profile image locally failed: {e}")
                return None

        except Exception as e:
            logger.error(f"❌ upload_profile_image failed: {str(e)}")
            return None

# Global storage client instance
storage_client = StorageClient()
