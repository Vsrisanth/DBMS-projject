import os

# Base directory
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Load environment variables from .env file if available
_env_file = os.path.join(BASE_DIR, '.env')
if os.path.isfile(_env_file):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env_file)
    except ImportError:
        # Fallback parser if python-dotenv is not installed
        with open(_env_file, 'r', encoding='utf-8') as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    _k = _k.strip()
                    _v = _v.strip().strip('"').strip("'")
                    if _k not in os.environ:
                        os.environ[_k] = _v

class Config:
    """Base application configuration."""

    # Environment & Production Detection
    ENV = os.environ.get('FLASK_ENV', 'production' if os.environ.get('RENDER') == 'true' else 'development')
    IS_PRODUCTION = (
        os.environ.get('FLASK_ENV', '').lower() == 'production' or
        os.environ.get('RENDER', '').lower() == 'true' or
        os.environ.get('ENV', '').lower() == 'production'
    )
    DEBUG = (os.environ.get('FLASK_DEBUG', '0') == '1') and not IS_PRODUCTION

    # Application Secret Key
    SECRET_KEY = os.environ.get('SECRET_KEY')
    if not SECRET_KEY:
        if IS_PRODUCTION:
            print("[SECURITY WARNING] SECRET_KEY environment variable is not set in production! "
                  "Please set a strong SECRET_KEY in your Render dashboard environment variables.")
            SECRET_KEY = 'civic-connects-default-production-key-please-override-in-render'
        else:
            SECRET_KEY = 'civic-connects-development-secret-key-2026'

    # Project paths & Upload limits
    BASE_DIR = BASE_DIR
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'complaints')
    AVATAR_UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'avatars')
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024  # 5MB Max upload limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

    # Database Mode & Configuration (Supports TiDB Cloud, MySQL, and local SQLite)
    # Options: 'tidb', 'mysql', 'sqlite', or 'auto'
    DB_MODE = os.environ.get('DB_MODE', os.environ.get('DB_ENGINE', 'auto')).lower()
    DB_ENGINE = DB_MODE  # Backward compatibility alias

    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    # Default port: 4000 for TiDB Cloud; 3306 for standard MySQL
    _default_port = 4000 if ('tidbcloud.com' in os.environ.get('DB_HOST', '').lower() or os.environ.get('DB_PORT') == '4000') else 3306
    DB_PORT = int(os.environ.get('DB_PORT', _default_port))
    DB_USER = os.environ.get('DB_USER', 'root')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', '')
    DB_NAME = os.environ.get('DB_NAME', 'civic_connects')
    DB_TIMEOUT = int(os.environ.get('DB_TIMEOUT', 10))  # seconds
    DB_POOL_SIZE = int(os.environ.get('DB_POOL_SIZE', 5))

    # TLS / SSL Settings for Cloud Database Connections (TiDB Cloud)
    DB_SSL = os.environ.get('DB_SSL', '').lower() in ('true', '1', 'yes')
    DB_SSL_CA = os.environ.get('DB_SSL_CA', '')

    # Cloudinary Cloud Storage Configuration
    CLOUDINARY_CLOUD_NAME = os.environ.get('CLOUDINARY_CLOUD_NAME', '')
    CLOUDINARY_API_KEY = os.environ.get('CLOUDINARY_API_KEY', '')
    CLOUDINARY_API_SECRET = os.environ.get('CLOUDINARY_API_SECRET', '')
    CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL', '')

    # Security & Session Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = IS_PRODUCTION  # Send cookies only over HTTPS in production
    PERMANENT_SESSION_LIFETIME = 86400  # 24 Hours
