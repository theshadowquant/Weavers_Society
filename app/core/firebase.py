import os
import glob
import json
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_firebase_app = None
_firestore_db = None

def _find_service_account_path() -> Optional[str]:
    """Locates the Firebase service account JSON file."""
    # 1. Explicit env var
    env_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    if env_path and os.path.exists(env_path):
        return env_path
    
    # 2. Check workspace root for adminsdk JSON files
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    patterns = [
        os.path.join(project_root, "*firebase*.json"),
        os.path.join(project_root, "*-adminsdk-*.json"),
        os.path.join(project_root, "service-account*.json"),
    ]
    for pattern in patterns:
        matches = glob.glob(pattern)
        if matches:
            return matches[0]
            
    return None

def init_firebase():
    """Initializes Firebase Admin SDK if credentials are available."""
    global _firebase_app, _firestore_db
    if _firebase_app is not None:
        return _firebase_app
        
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
    except ImportError:
        logger.warning("firebase_admin library not installed.")
        return None

    # Check if app already initialized
    try:
        _firebase_app = firebase_admin.get_app()
        _firestore_db = firestore.client()
        return _firebase_app
    except ValueError:
        pass  # App not yet initialized

    cred = None

    # 1. Try JSON string from environment variable (standard for Vercel / serverless)
    raw_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
    if raw_json:
        try:
            cert_dict = json.loads(raw_json)
            cred = credentials.Certificate(cert_dict)
            logger.info("Firebase initialized using FIREBASE_CREDENTIALS_JSON environment variable.")
        except Exception as e:
            logger.error(f"Failed to parse FIREBASE_CREDENTIALS_JSON: {e}")

    # 2. Try file on disk
    if cred is None:
        cert_path = _find_service_account_path()
        if cert_path:
            try:
                cred = credentials.Certificate(cert_path)
                logger.info(f"Firebase initialized using service account file: {os.path.basename(cert_path)}")
            except Exception as e:
                logger.error(f"Failed to load Firebase credentials from {cert_path}: {e}")

    # 3. Try default application credentials
    if cred is None:
        try:
            cred = credentials.ApplicationDefault()
            logger.info("Firebase using ApplicationDefault credentials.")
        except Exception:
            cred = None

    if cred:
        try:
            _firebase_app = firebase_admin.initialize_app(cred)
            _firestore_db = firestore.client()
            logger.info("Firebase Admin and Firestore initialized successfully.")
            return _firebase_app
        except Exception as e:
            logger.error(f"Failed to initialize Firebase Admin app: {e}")
            return None

    logger.warning("Firebase credentials not found. Firebase features running in mock/disabled mode.")
    return None

def is_firebase_available() -> bool:
    """Returns True if Firebase is initialized and connected."""
    if _firebase_app is None:
        init_firebase()
    return _firebase_app is not None

def get_firestore_client():
    """Returns Firestore client instance if available."""
    if _firestore_db is None:
        init_firebase()
    return _firestore_db

def get_firebase_auth():
    """Returns Firebase Admin Auth module if initialized."""
    if not is_firebase_available():
        return None
    try:
        from firebase_admin import auth
        return auth
    except Exception as e:
        logger.error(f"Failed to load firebase_admin.auth: {e}")
        return None

def verify_firebase_id_token(id_token: str, check_revoked: bool = False) -> Dict[str, Any]:
    """
    Cryptographically verifies a Firebase ID Token issued by Firebase Auth client SDKs
    (e.g., Phone OTP, Google Sign-in, or Email authentication).
    Returns decoded token dictionary containing uid, phone_number, email, etc.
    """
    auth = get_firebase_auth()
    if not auth:
        raise RuntimeError("Firebase Auth is not available. Please verify credentials.")
    
    try:
        decoded_token = auth.verify_id_token(id_token, check_revoked=check_revoked)
        return decoded_token
    except Exception as e:
        logger.warning(f"Firebase ID token verification failed: {e}")
        raise ValueError(f"Invalid Firebase ID token: {str(e)}")

def create_firebase_custom_token(uid: str, additional_claims: Optional[Dict[str, Any]] = None) -> str:
    """
    Issues a cryptographically signed Firebase Custom Token containing custom tenant claims.
    Clients can pass this token to `signInWithCustomToken` to directly connect to Firebase
    with the cooperative tenant permissions.
    """
    auth = get_firebase_auth()
    if not auth:
        raise RuntimeError("Firebase Auth is not available. Please verify credentials.")
    
    raw_token = auth.create_custom_token(uid, developer_claims=additional_claims or {})
    if isinstance(raw_token, bytes):
        return raw_token.decode('utf-8')
    return str(raw_token)

def sync_user_to_firebase_auth(
    uid: str,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    display_name: Optional[str] = None
) -> Optional[Any]:
    """
    Creates or updates a user in Firebase Auth.
    Ensures user account exists in Firebase with phone / email credentials.
    """
    auth = get_firebase_auth()
    if not auth:
        return None
        
    try:
        # Check if user exists
        user_record = auth.get_user(uid)
        # Update user
        update_args = {}
        if email and user_record.email != email:
            update_args["email"] = email
        if display_name and user_record.display_name != display_name:
            update_args["display_name"] = display_name
        if update_args:
            user_record = auth.update_user(uid, **update_args)
        return user_record
    except Exception:
        # Create new user record
        try:
            create_args = {"uid": uid}
            if email:
                create_args["email"] = email
            if phone:
                # Format phone with international +91 if needed
                formatted_phone = phone if phone.startswith("+") else f"+91{phone}"
                create_args["phone_number"] = formatted_phone
            if display_name:
                create_args["display_name"] = display_name
            return auth.create_user(**create_args)
        except Exception as err:
            logger.warning(f"Failed to sync user {uid} to Firebase Auth: {err}")
            return None

def get_firebase_status() -> Dict[str, Any]:
    """Returns comprehensive status of Firebase Admin, Firestore, and Auth."""
    init_firebase()
    if not _firebase_app:
        return {
            "status": "disconnected",
            "connected": False,
            "project_id": None,
            "firestore_ready": False,
            "auth_ready": False,
            "message": "Firebase credentials not configured or initialized"
        }
    
    project_id = getattr(_firebase_app, "project_id", None)
    if not project_id:
        try:
            project_id = _firebase_app.options.get("projectId")
        except Exception:
            pass

    firestore_ready = False
    auth_ready = False
    error_msg = None

    # Check Firestore
    try:
        db = get_firestore_client()
        if db:
            firestore_ready = True
    except Exception as e:
        error_msg = f"Firestore: {e}"

    # Check Auth
    try:
        auth_module = get_firebase_auth()
        if auth_module:
            auth_ready = True
    except Exception as e:
        if error_msg:
            error_msg += f"; Auth: {e}"
        else:
            error_msg = f"Auth: {e}"

    is_all_ready = firestore_ready and auth_ready
    return {
        "status": "connected" if is_all_ready else ("partial" if (firestore_ready or auth_ready) else "error"),
        "connected": True,
        "project_id": project_id,
        "firestore_ready": firestore_ready,
        "auth_ready": auth_ready,
        "error": error_msg
    }
