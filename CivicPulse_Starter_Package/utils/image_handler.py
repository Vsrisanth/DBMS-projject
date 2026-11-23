import os
import uuid
from werkzeug.utils import secure_filename
from config import Config

def allowed_file(filename):
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS

def save_complaint_image(file):
    """
    Validates and securely stores an uploaded complaint image.
    Returns the saved filename, or None if no file or invalid.
    """
    if not file or file.filename == '':
        return None
    
    if not allowed_file(file.filename):
        raise ValueError("Invalid file format. Only PNG, JPG, JPEG, and WEBP images are supported.")
    
    # Ensure upload directory exists
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    
    original_name = secure_filename(file.filename)
    unique_prefix = uuid.uuid4().hex[:12]
    ext = original_name.rsplit('.', 1)[1].lower()
    safe_name = f"{unique_prefix}_{original_name}"
    
    # Save the file
    file_path = os.path.join(Config.UPLOAD_FOLDER, safe_name)
    file.save(file_path)
    
    return safe_name
