import os
import uuid
from werkzeug.utils import secure_filename
from config import Config

def allowed_file(filename):
    """Verifies that the uploaded file has a permissible extension."""
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

def is_cloudinary_configured():
    """
    Checks whether Cloudinary is configured via environment variables
    and the cloudinary Python SDK is available.
    """
    has_credentials = bool(
        os.environ.get('CLOUDINARY_URL') or
        (Config.CLOUDINARY_CLOUD_NAME and Config.CLOUDINARY_API_KEY and Config.CLOUDINARY_API_SECRET)
    )
    if not has_credentials:
        return False

    try:
        import cloudinary
        import cloudinary.uploader
        return True
    except ImportError:
        print("[ImageHandler Warning] Cloudinary credentials set but 'cloudinary' library not installed. Falling back to local storage.")
        return False

def _configure_cloudinary():
    """Initializes Cloudinary configuration with provided credentials."""
    import cloudinary
    if os.environ.get('CLOUDINARY_URL'):
        cloudinary.config()
    else:
        cloudinary.config(
            cloud_name=Config.CLOUDINARY_CLOUD_NAME,
            api_key=Config.CLOUDINARY_API_KEY,
            api_secret=Config.CLOUDINARY_API_SECRET,
            secure=True
        )

def save_complaint_image(file):
    """
    Validates and stores an uploaded complaint evidence image.
    When Cloudinary is configured (e.g. on Render), uploads to Cloudinary and returns secure URL.
    Otherwise, securely saves to local static/uploads/complaints/ and returns the filename.
    """
    if not file or file.filename == '':
        return None

    if not allowed_file(file.filename):
        raise ValueError("Invalid file format. Only PNG, JPG, JPEG, and WEBP images are supported.")

    # 1. Cloudinary cloud storage upload
    if is_cloudinary_configured():
        try:
            _configure_cloudinary()
            import cloudinary.uploader
            upload_result = cloudinary.uploader.upload(
                file,
                folder="civic_connects/complaints",
                resource_type="image"
            )
            return upload_result.get('secure_url')
        except Exception as cloud_err:
            print(f"[ImageHandler Error] Cloudinary complaint upload failed: {cloud_err}. Falling back to local storage.")
            # Rewind file pointer if supported before attempting local save
            try:
                file.seek(0)
            except Exception:
                pass

    # 2. Local storage fallback
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    original_name = secure_filename(file.filename)
    unique_prefix = uuid.uuid4().hex[:12]
    safe_name = f"{unique_prefix}_{original_name}"

    file_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
    file.save(file_path)

    return safe_name

def save_avatar_image(file):
    """
    Validates and stores an uploaded user profile avatar image.
    When Cloudinary is configured (e.g. on Render), uploads to Cloudinary and returns secure URL.
    Otherwise, securely saves to local static/uploads/avatars/ and returns the filename.
    """
    if not file or file.filename == '':
        return None

    if not allowed_file(file.filename):
        raise ValueError("Invalid file format. Only PNG, JPG, JPEG, and WEBP images are supported.")

    # 1. Cloudinary cloud storage upload
    if is_cloudinary_configured():
        try:
            _configure_cloudinary()
            import cloudinary.uploader
            upload_result = cloudinary.uploader.upload(
                file,
                folder="civic_connects/avatars",
                resource_type="image"
            )
            return upload_result.get('secure_url')
        except Exception as cloud_err:
            print(f"[ImageHandler Error] Cloudinary avatar upload failed: {cloud_err}. Falling back to local storage.")
            try:
                file.seek(0)
            except Exception:
                pass

    # 2. Local storage fallback
    os.makedirs(Config.AVATAR_UPLOAD_FOLDER, exist_ok=True)
    original_name = secure_filename(file.filename)
    unique_prefix = uuid.uuid4().hex[:12]
    safe_name = f"avatar_{unique_prefix}_{original_name}"

    file_path = os.path.join(Config.AVATAR_UPLOAD_FOLDER, safe_name)
    file.save(file_path)

    return safe_name

def delete_image_file(image_ref, folder='complaints'):
    """
    Safely deletes an image file. If the reference is a local file, removes it from disk.
    If it is a Cloudinary URL, ignores local deletion or optionally removes from Cloudinary.
    """
    if not image_ref:
        return

    # If it is a remote cloud URL, no local file needs to be unlinked
    if image_ref.startswith('http://') or image_ref.startswith('https://'):
        return

    target_dir = Config.AVATAR_UPLOAD_FOLDER if folder == 'avatars' else Config.UPLOAD_FOLDER
    local_path = os.path.join(target_dir, image_ref)
    if os.path.exists(local_path):
        try:
            os.remove(local_path)
        except Exception as e:
            print(f"[ImageHandler Warning] Failed to delete local image {local_path}: {e}")
