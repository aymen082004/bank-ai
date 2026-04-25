"""
MCP Handler — MongoDB interface for the Bank Complaint AI system.
Manages: customers (read-only), complaints (read/write), bookings and Google Calendar events.

Google Calendar configuration:
- GOOGLE_OAUTH_AUTHORIZED_USER_FILE: path to OAuth2 authorized user credentials JSON
- GOOGLE_OAUTH_AUTHORIZED_USER_JSON: OAuth2 authorized user credentials JSON string
- GOOGLE_OAUTH_CLIENT_SECRETS_FILE: path to OAuth2 client secrets JSON
- GOOGLE_OAUTH_CLIENT_SECRETS_JSON: OAuth2 client secrets JSON string
- GOOGLE_OAUTH_TOKEN_FILE: path to save/load OAuth2 credentials (default: google_oauth_token.json)
- GOOGLE_OAUTH_ACCESS_TOKEN: OAuth2 access token
- GOOGLE_OAUTH_REFRESH_TOKEN: OAuth2 refresh token
- GOOGLE_OAUTH_CLIENT_ID: OAuth2 client ID
- GOOGLE_OAUTH_CLIENT_SECRET: OAuth2 client secret
- GOOGLE_OAUTH_TOKEN_URI: OAuth2 token URI (default: https://oauth2.googleapis.com/token)
- GOOGLE_CALENDAR_ID: target calendar id (default: primary)
- GOOGLE_CALENDAR_TIMEZONE: calendar timezone (default: UTC)
"""

import json
import os
import urllib.request
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv

dotenv_path = Path(__file__).resolve().parents[1] / ".env"
if not dotenv_path.exists():
    dotenv_path = Path(__file__).resolve().parents[2] / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    load_dotenv()

ROOT_DIR = Path(__file__).resolve().parents[1]

GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_TOKEN_URI = os.getenv("GOOGLE_OAUTH_TOKEN_URI", "https://oauth2.googleapis.com/token")

if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
    from pathlib import Path
    backend_dotenv = Path(__file__).resolve().parents[2] / ".env"
    if backend_dotenv.exists():
        load_dotenv(backend_dotenv)
        GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
        GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")


def _resolve_env_path(value: str | None) -> str | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str((ROOT_DIR / path).resolve())


GOOGLE_OAUTH_AUTHORIZED_USER_FILE = _resolve_env_path(
    os.getenv("GOOGLE_OAUTH_AUTHORIZED_USER_FILE")
)
GOOGLE_OAUTH_AUTHORIZED_USER_JSON = os.getenv("GOOGLE_OAUTH_AUTHORIZED_USER_JSON")
GOOGLE_OAUTH_CLIENT_SECRETS_FILE = _resolve_env_path(
    os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS_FILE")
)
GOOGLE_OAUTH_CLIENT_SECRETS_JSON = os.getenv("GOOGLE_OAUTH_CLIENT_SECRETS_JSON")
GOOGLE_OAUTH_TOKEN_FILE = _resolve_env_path(
    os.getenv("GOOGLE_OAUTH_TOKEN_FILE", "google_oauth_token.json")
)
GOOGLE_OAUTH_ACCESS_TOKEN = os.getenv("GOOGLE_OAUTH_ACCESS_TOKEN")
GOOGLE_OAUTH_REFRESH_TOKEN = os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN")
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
GOOGLE_OAUTH_TOKEN_URI = os.getenv(
    "GOOGLE_OAUTH_TOKEN_URI", "https://oauth2.googleapis.com/token"
)
try:
    GOOGLE_OAUTH_LOCAL_SERVER_PORT = int(
        os.getenv("GOOGLE_OAUTH_LOCAL_SERVER_PORT", "8080")
    )
except ValueError:
    GOOGLE_OAUTH_LOCAL_SERVER_PORT = 8080
GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI", f"http://localhost:{GOOGLE_OAUTH_LOCAL_SERVER_PORT}/"
)
GOOGLE_CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_CALENDAR_TIMEZONE = os.getenv("GOOGLE_CALENDAR_TIMEZONE", "UTC")

GOOGLE_OAUTH_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/calendar",
]

APP_MONGO_URI = os.getenv(
    "APP_MONGO_URI",
    "mongodb+srv://alexhunter2020111_db_user:HUrHSfVkpCL1CrAb@cluster0.0rav9u6.mongodb.net/?appName=Cluster0",
)
APP_MONGO_DB_NAME = os.getenv("APP_MONGO_DB_NAME", "bank_ai")

app_client = MongoClient(APP_MONGO_URI, tls=True, tlsAllowInvalidCertificates=True)
db = app_client[APP_MONGO_DB_NAME]

customers_collection = db["customers"]
complaints_collection = db["complaints"]


def _load_json_string(json_string: str) -> dict | None:
    try:
        return json.loads(json_string)
    except Exception:
        return None


def _normalize_google_oauth_client_config(config: dict) -> dict | None:
    if not isinstance(config, dict):
        return None

    if "installed" in config:
        installed = dict(config.get("installed", {}))
        redirect_uris = installed.get("redirect_uris")
        if not isinstance(redirect_uris, list):
            installed["redirect_uris"] = [GOOGLE_OAUTH_REDIRECT_URI]
        elif GOOGLE_OAUTH_REDIRECT_URI not in redirect_uris:
            installed["redirect_uris"].append(GOOGLE_OAUTH_REDIRECT_URI)
        installed.setdefault("auth_uri", "https://accounts.google.com/o/oauth2/auth")
        installed.setdefault("token_uri", GOOGLE_OAUTH_TOKEN_URI)
        return {"installed": installed}

    if "web" in config:
        web = config.get("web", {})
        return {
            "installed": {
                "client_id": web.get("client_id"),
                "client_secret": web.get("client_secret"),
                "auth_uri": web.get(
                    "auth_uri", "https://accounts.google.com/o/oauth2/auth"
                ),
                "token_uri": web.get("token_uri", GOOGLE_OAUTH_TOKEN_URI),
                "redirect_uris": [GOOGLE_OAUTH_REDIRECT_URI],
            }
        }

    return None


def _run_local_server_flow(flow):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return flow.run_local_server(
                port=GOOGLE_OAUTH_LOCAL_SERVER_PORT,
                prompt="consent",
                access_type="offline",
                success_message="The authentication flow has completed. You may close this window.",
            )
    except Exception as exc:
        print(
            f"[{datetime.now().isoformat()}] Google local server OAuth flow failed: {type(exc).__name__}: {exc}"
        )
        return None


def _get_google_user_info(credentials) -> dict | None:
    if not credentials:
        return None

    token = getattr(credentials, "token", None)
    if not token:
        return None

    try:
        request = urllib.request.Request(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            if isinstance(data, dict):
                return data
    except Exception as exc:
        print(f"[{datetime.now().isoformat()}] Google user info fetch failed: {exc}")

    id_token_value = getattr(credentials, "id_token", None)
    if id_token_value:
        try:
            from google.auth.transport.requests import Request as AuthRequest
            from google.oauth2 import id_token as oauth2_id_token

            request = AuthRequest()
            audience = GOOGLE_OAUTH_CLIENT_ID or None
            claims = oauth2_id_token.verify_oauth2_token(
                id_token_value,
                request,
                audience,
            )
            if isinstance(claims, dict):
                return claims
        except Exception as exc:
            print(
                f"[{datetime.now().isoformat()}] Google id_token decode failed: {exc}"
            )

    return None


def _upsert_google_user(user_info: dict, credentials) -> dict | None:
    if not user_info:
        return None
    google_id = user_info.get("sub") or user_info.get("email")
    if not google_id:
        return None

    token_data = {
        "access_token": getattr(credentials, "token", None),
        "refresh_token": getattr(credentials, "refresh_token", None),
        "id_token": getattr(credentials, "id_token", None),
        "token_uri": getattr(credentials, "token_uri", None),
        "client_id": getattr(credentials, "client_id", None),
        "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
        "scopes": getattr(credentials, "scopes", None),
        "expiry": getattr(credentials, "expiry", None),
    }

    user_doc = {
        "google_id": google_id,
        "email": user_info.get("email"),
        "name": user_info.get("name"),
        "picture": user_info.get("picture"),
        "locale": user_info.get("locale"),
        "tokens": token_data,
        "token": getattr(credentials, "token", None),  # Add token field
        "updated_at": datetime.utcnow(),
    }

    users_collection.update_one(
        {"google_id": google_id},
        {"$set": user_doc},
        upsert=True,
    )
    return user_doc


def _load_google_credentials(scopes: list[str] | None = None):
    if scopes is None:
        scopes = GOOGLE_OAUTH_SCOPES

    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import credentials as oauth2_credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError as exc:
        print(
            f"[{datetime.now().isoformat()}] Google auth libs unavailable: {type(exc).__name__}: {exc}"
        )
        return None

    def _log_branch_error(branch: str, exc: Exception) -> None:
        print(
            f"[{datetime.now().isoformat()}] Google auth branch {branch} failed: {type(exc).__name__}: {exc}"
        )

    creds = None

    if GOOGLE_OAUTH_AUTHORIZED_USER_FILE and os.path.exists(
        GOOGLE_OAUTH_AUTHORIZED_USER_FILE
    ):
        try:
            creds = oauth2_credentials.Credentials.from_authorized_user_file(
                GOOGLE_OAUTH_AUTHORIZED_USER_FILE,
                scopes=scopes,
            )
            print(
                f"[{datetime.now().isoformat()}] Loaded credentials from authorized user file: {GOOGLE_OAUTH_AUTHORIZED_USER_FILE}"
            )
        except Exception as exc:
            _log_branch_error("authorized_user_file", exc)
            creds = None

    if (
        not creds
        and GOOGLE_OAUTH_TOKEN_FILE
        and os.path.exists(GOOGLE_OAUTH_TOKEN_FILE)
    ):
        try:
            creds = oauth2_credentials.Credentials.from_authorized_user_file(
                GOOGLE_OAUTH_TOKEN_FILE,
                scopes=scopes,
            )
            print(
                f"[{datetime.now().isoformat()}] Loaded credentials from token file: {GOOGLE_OAUTH_TOKEN_FILE}"
            )
        except Exception as exc:
            _log_branch_error("token_file", exc)
            creds = None

    if not creds and GOOGLE_OAUTH_AUTHORIZED_USER_JSON:
        auth_info = _load_json_string(GOOGLE_OAUTH_AUTHORIZED_USER_JSON)
        if isinstance(auth_info, dict):
            try:
                creds = oauth2_credentials.Credentials.from_authorized_user_info(
                    auth_info,
                    scopes=scopes,
                )
                print(
                    f"[{datetime.now().isoformat()}] Loaded credentials from authorized user JSON"
                )
            except Exception as exc:
                _log_branch_error("authorized_user_json", exc)
                creds = None
        else:
            print(
                f"[{datetime.now().isoformat()}] GOOGLE_OAUTH_AUTHORIZED_USER_JSON is not valid JSON"
            )

    if not creds and (
        GOOGLE_OAUTH_ACCESS_TOKEN
        and GOOGLE_OAUTH_REFRESH_TOKEN
        and GOOGLE_OAUTH_CLIENT_ID
        and GOOGLE_OAUTH_CLIENT_SECRET
    ):
        try:
            creds = oauth2_credentials.Credentials(
                token=GOOGLE_OAUTH_ACCESS_TOKEN,
                refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
                token_uri=GOOGLE_OAUTH_TOKEN_URI,
                client_id=GOOGLE_OAUTH_CLIENT_ID,
                client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
                scopes=scopes,
            )
            print(
                f"[{datetime.now().isoformat()}] Loaded credentials from OAuth env vars"
            )
        except Exception as exc:
            _log_branch_error("env_token_vars", exc)
            creds = None

    if (
        not creds
        and GOOGLE_OAUTH_CLIENT_SECRETS_FILE
        and os.path.exists(GOOGLE_OAUTH_CLIENT_SECRETS_FILE)
    ):
        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                GOOGLE_OAUTH_CLIENT_SECRETS_FILE,
                scopes=scopes,
            )
            creds = _run_local_server_flow(flow)
            if creds:
                print(
                    f"[{datetime.now().isoformat()}] Obtained credentials via client secrets file"
                )
        except Exception as exc:
            _log_branch_error("client_secrets_file", exc)
            creds = None

    if not creds and GOOGLE_OAUTH_CLIENT_SECRETS_JSON:
        client_config = _load_json_string(GOOGLE_OAUTH_CLIENT_SECRETS_JSON)
        if isinstance(client_config, dict):
            try:
                client_config = _normalize_google_oauth_client_config(client_config)
                if client_config:
                    flow = InstalledAppFlow.from_client_config(
                        client_config,
                        scopes=scopes,
                    )
                    creds = _run_local_server_flow(flow)
                    if creds:
                        print(
                            f"[{datetime.now().isoformat()}] Obtained credentials via client secrets JSON"
                        )
            except Exception as exc:
                _log_branch_error("client_secrets_json", exc)
                creds = None
        else:
            print(
                f"[{datetime.now().isoformat()}] GOOGLE_OAUTH_CLIENT_SECRETS_JSON is not valid JSON"
            )

    if not creds and (
        GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET and GOOGLE_OAUTH_TOKEN_URI
    ):
        try:
            client_config = {
                "installed": {
                    "client_id": GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": GOOGLE_OAUTH_TOKEN_URI,
                    "redirect_uris": [GOOGLE_OAUTH_REDIRECT_URI],
                },
                "web": {
                    "client_id": GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": GOOGLE_OAUTH_TOKEN_URI,
                    "redirect_uris": [GOOGLE_OAUTH_REDIRECT_URI],
                },
            }
            flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
            creds = _run_local_server_flow(flow)
            if creds:
                print(
                    f"[{datetime.now().isoformat()}] Obtained credentials via env client config"
                )
        except Exception as exc:
            _log_branch_error("env_client_config", exc)
            creds = None

    if creds:
        print(
            f"[{datetime.now().isoformat()}] Raw Google credentials loaded: valid={getattr(creds, 'valid', None)}, "
            f"expired={getattr(creds, 'expired', None)}, token_present={bool(getattr(creds, 'token', None))}, "
            f"refresh_token_present={bool(getattr(creds, 'refresh_token', None))}"
        )
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    print(
                        f"[{datetime.now().isoformat()}] Refreshed expired Google credentials"
                    )
                except Exception as exc:
                    _log_branch_error("refresh_credentials", exc)
                    creds = None
            else:
                print(
                    f"[{datetime.now().isoformat()}] Credentials are invalid and cannot be refreshed"
                )
                creds = None

    if creds and GOOGLE_OAUTH_TOKEN_FILE:
        try:
            with open(GOOGLE_OAUTH_TOKEN_FILE, "w", encoding="utf-8") as token_file:
                token_file.write(creds.to_json())
            print(
                f"[{datetime.now().isoformat()}] Saved Google credentials to token file: {GOOGLE_OAUTH_TOKEN_FILE}"
            )
        except Exception as exc:
            print(
                f"[{datetime.now().isoformat()}] Failed to save Google token file: {type(exc).__name__}: {exc}"
            )

    return creds


def authenticate_google_user() -> dict | None:
    creds = _load_google_credentials()
    if not creds:
        print(
            f"[{datetime.now().isoformat()}] Google authentication failed: no credentials loaded"
        )
        return None

    print(
        f"[{datetime.now().isoformat()}] Google credentials obtained: "
        f"token_present={bool(getattr(creds, 'token', None))}, "
        f"refresh_token_present={bool(getattr(creds, 'refresh_token', None))}, "
        f"expiry={getattr(creds, 'expiry', None)}"
    )

    user_info = _get_google_user_info(creds)
    if not user_info:
        print(
            f"[{datetime.now().isoformat()}] Google authentication failed: unable to retrieve user info"
        )
        return None

    # Add google_id for compatibility
    user_info["google_id"] = user_info.get("sub") or user_info.get("email")

    # Removed MongoDB upsert, keeping token local only
    return user_info


def save_followup_session(
    google_id: str,
    complaint_id: str,
    suggested_slots: list[dict[str, Any]],
    follow_up_note: str,
) -> None:
    # Disabled MongoDB usage to avoid SSL issues
    pass


def get_followup_session(google_id: str) -> dict[str, Any] | None:
    # Disabled MongoDB usage to avoid SSL issues
    return None


def clear_followup_session(google_id: str) -> None:
    # Disabled MongoDB usage to avoid SSL issues
    pass


def save_conversation_memory(
    google_id: str,
    complaint_id: str,
    selected_slot: dict[str, Any],
    user_reply: str,
    confirmation_message: str,
) -> None:
    # Disabled MongoDB usage to avoid SSL issues
    pass


def _init_google_calendar_service(
    google_access_token: str | None = None,
    google_refresh_token: str | None = None,
):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import credentials as oauth2_credentials
        from googleapiclient.discovery import build
    except ImportError:
        return None

    scopes = GOOGLE_OAUTH_SCOPES
    creds = None

    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    
    is_refresh = google_access_token and google_access_token.startswith("ya29.")
    if is_refresh:
        google_refresh_token = google_access_token
        google_access_token = None
    
    if google_refresh_token and client_id and client_secret:
        try:
            creds = oauth2_credentials.Credentials(
                token=None,
                refresh_token=google_refresh_token,
                token_uri=GOOGLE_OAUTH_TOKEN_URI,
                client_id=client_id,
                client_secret=client_secret,
                scopes=scopes,
            )
            try:
                creds.refresh(Request())
            except Exception as refresh_err:
                print(f"[{datetime.now().isoformat()}] Token refresh failed: {refresh_err}")
                creds = None
        except Exception as exc:
            print(
                f"[{datetime.now().isoformat()}] Failed to init creds from refresh_token: {exc}"
            )
            creds = None
    elif google_access_token:
        try:
            if client_id and client_secret:
                creds = oauth2_credentials.Credentials(
                    token=google_access_token,
                    client_id=client_id,
                    client_secret=client_secret,
                    token_uri=GOOGLE_OAUTH_TOKEN_URI,
                    scopes=scopes,
                )
            else:
                creds = oauth2_credentials.Credentials(
                    token=google_access_token,
                    scopes=scopes,
                )
        except Exception as exc:
            print(
                f"[{datetime.now().isoformat()}] Failed to init creds from access_token: {exc}"
            )
            creds = None

    def _load_json_string(json_string: str) -> dict | None:
        try:
            return json.loads(json_string)
        except Exception:
            return None

    def _save_credentials(credentials, path: str) -> None:
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as token_file:
                token_file.write(credentials.to_json())
        except Exception:
            pass

    def _run_oauth_flow_from_client_secrets(path: str) -> object | None:
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            flow = InstalledAppFlow.from_client_secrets_file(
                path,
                scopes=scopes,
            )
            return flow.run_local_server(
                port=GOOGLE_OAUTH_LOCAL_SERVER_PORT,
                prompt="consent",
                access_type="offline",
            )
        except Exception as exc:
            print(
                f"[{datetime.now().isoformat()}] Google OAuth client secrets auth failed: {exc}"
            )
            return None

    def _run_oauth_flow_from_client_config(config: dict) -> object | None:
        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            client_config = _normalize_google_oauth_client_config(config)
            if not client_config:
                return None
            flow = InstalledAppFlow.from_client_config(
                client_config,
                scopes=scopes,
            )
            return flow.run_local_server(
                port=GOOGLE_OAUTH_LOCAL_SERVER_PORT,
                prompt="consent",
                access_type="offline",
            )
        except Exception as exc:
            print(
                f"[{datetime.now().isoformat()}] Google OAuth client config auth failed: {exc}"
            )
            return None

    def _run_oauth_flow_from_env_client_config() -> object | None:
        if not (
            GOOGLE_OAUTH_CLIENT_ID
            and GOOGLE_OAUTH_CLIENT_SECRET
            and GOOGLE_OAUTH_TOKEN_URI
        ):
            return None

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow

            client_config = {
                "installed": {
                    "client_id": GOOGLE_OAUTH_CLIENT_ID,
                    "client_secret": GOOGLE_OAUTH_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": GOOGLE_OAUTH_TOKEN_URI,
                    "redirect_uris": [GOOGLE_OAUTH_REDIRECT_URI],
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, scopes=scopes)
            return flow.run_local_server(
                port=GOOGLE_OAUTH_LOCAL_SERVER_PORT,
                prompt="consent",
                access_type="offline",
            )
        except Exception as exc:
            print(
                f"[{datetime.now().isoformat()}] Google OAuth env client config auth failed: {exc}"
            )
            return None

    if GOOGLE_OAUTH_AUTHORIZED_USER_FILE and os.path.exists(
        GOOGLE_OAUTH_AUTHORIZED_USER_FILE
    ):
        try:
            creds = oauth2_credentials.Credentials.from_authorized_user_file(
                GOOGLE_OAUTH_AUTHORIZED_USER_FILE,
                scopes=scopes,
            )
        except Exception:
            creds = None

    if (
        not creds
        and GOOGLE_OAUTH_TOKEN_FILE
        and os.path.exists(GOOGLE_OAUTH_TOKEN_FILE)
    ):
        try:
            creds = oauth2_credentials.Credentials.from_authorized_user_file(
                GOOGLE_OAUTH_TOKEN_FILE,
                scopes=scopes,
            )
        except Exception:
            creds = None

    if not creds and GOOGLE_OAUTH_AUTHORIZED_USER_JSON:
        auth_info = _load_json_string(GOOGLE_OAUTH_AUTHORIZED_USER_JSON)
        if isinstance(auth_info, dict):
            try:
                creds = oauth2_credentials.Credentials.from_authorized_user_info(
                    auth_info,
                    scopes=scopes,
                )
            except Exception:
                creds = None

    if not creds and (
        GOOGLE_OAUTH_ACCESS_TOKEN
        and GOOGLE_OAUTH_REFRESH_TOKEN
        and GOOGLE_OAUTH_CLIENT_ID
        and GOOGLE_OAUTH_CLIENT_SECRET
    ):
        creds = oauth2_credentials.Credentials(
            token=GOOGLE_OAUTH_ACCESS_TOKEN,
            refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
            token_uri=GOOGLE_OAUTH_TOKEN_URI,
            client_id=GOOGLE_OAUTH_CLIENT_ID,
            client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=scopes,
        )

    if (
        not creds
        and GOOGLE_OAUTH_CLIENT_SECRETS_FILE
        and os.path.exists(GOOGLE_OAUTH_CLIENT_SECRETS_FILE)
    ):
        creds = _run_oauth_flow_from_client_secrets(GOOGLE_OAUTH_CLIENT_SECRETS_FILE)
        if creds and GOOGLE_OAUTH_TOKEN_FILE:
            _save_credentials(creds, GOOGLE_OAUTH_TOKEN_FILE)

    if not creds and GOOGLE_OAUTH_CLIENT_SECRETS_JSON:
        client_config = _load_json_string(GOOGLE_OAUTH_CLIENT_SECRETS_JSON)
        if isinstance(client_config, dict):
            creds = _run_oauth_flow_from_client_config(client_config)
            if creds and GOOGLE_OAUTH_TOKEN_FILE:
                _save_credentials(creds, GOOGLE_OAUTH_TOKEN_FILE)

    if not creds:
        creds = _run_oauth_flow_from_env_client_config()
        if creds and GOOGLE_OAUTH_TOKEN_FILE:
            _save_credentials(creds, GOOGLE_OAUTH_TOKEN_FILE)

    if creds and not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None
        else:
            creds = None

    if not creds:
        print(
            f"[{datetime.now().isoformat()}] Google Calendar auth failed: "
            f"oauth_file_set={bool(GOOGLE_OAUTH_AUTHORIZED_USER_FILE)}, "
            f"oauth_token_file_set={bool(GOOGLE_OAUTH_TOKEN_FILE and os.path.exists(GOOGLE_OAUTH_TOKEN_FILE))}, "
            f"oauth_json_set={bool(GOOGLE_OAUTH_AUTHORIZED_USER_JSON)}, "
            f"client_secrets_file_set={bool(GOOGLE_OAUTH_CLIENT_SECRETS_FILE and os.path.exists(GOOGLE_OAUTH_CLIENT_SECRETS_FILE))}, "
            f"client_secrets_json_set={bool(GOOGLE_OAUTH_CLIENT_SECRETS_JSON)}"
        )
        return None

    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception:
        return None


def _create_google_calendar_event(
    event_data: dict, google_access_token: str | None = None, google_refresh_token: str | None = None
) -> dict | None:
    
    service = _init_google_calendar_service(
        google_access_token=google_access_token,
        google_refresh_token=google_refresh_token,
    )
    if service is None:
        return None
    
    start_time = event_data.get("start")
    end_time = event_data.get("end")
    
    if not start_time or not end_time:
        print(f"[{datetime.now().isoformat()}] Google Calendar event skipped: missing start/end time")
        return None

    body = {
        "summary": event_data.get("summary", "Bank visit appointment"),
        "description": event_data.get("description", ""),
        "location": event_data.get("location", ""),
        "start": {
            "dateTime": start_time,
            "timeZone": GOOGLE_CALENDAR_TIMEZONE,
        },
        "end": {
            "dateTime": end_time,
            "timeZone": GOOGLE_CALENDAR_TIMEZONE,
        },
    }

    try:
        created = (
            service.events()
            .insert(
                calendarId=GOOGLE_CALENDAR_ID,
                body=body,
                sendUpdates="none",
            )
            .execute()
        )
        return created
    except Exception as exc:
        print(
            f"[{datetime.now().isoformat()}] Google Calendar event creation failed: {exc}"
        )
        print(
            f"[{datetime.now().isoformat()}] Event body: {json.dumps(body, ensure_ascii=False)}"
        )
        return None


def _serialize(doc: dict) -> dict:
    """Convert ObjectId fields to str for JSON safety."""
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def mcp_handle(message: dict) -> dict:
    """
    Unified MCP gateway.

    message = {
        "action":     "fetch" | "update" | "insert",
        "collection": "customers" | "complaints",
        "filter":     {...},   # for fetch / update
        "data":       {...},   # for insert / update ($set payload)
    }
    """
    response: dict = {"status": "error", "data": None}

    try:
        action = message.get("action")
        collection_name = message.get("collection", "complaints")
        collection = db[collection_name]
        google_access_token = message.get("google_access_token")

        if action == "fetch":
            results = list(collection.find(message.get("filter", {})))
            response = {
                "status": "success",
                "data": [_serialize(r) for r in results],
            }

        elif action == "update":
            update_data = message.get("data", {})
            update_data["updated_at"] = datetime.utcnow()
            result = collection.update_many(
                message.get("filter", {}),
                {"$set": update_data},
            )
            response = {
                "status": "success",
                "data": {
                    "matched": result.matched_count,
                    "modified": result.modified_count,
                },
            }

        elif action == "insert":
            data = message.get("data", {})
            now = datetime.now()
            data.setdefault("_id", str(ObjectId()))
            data.setdefault("created_at", now)
            data.setdefault("updated_at", now)

            collection.insert_one(data)
            response = {"status": "success", "data": {"_id": data["_id"]}}

        else:
            response = {"status": "error", "message": f"Unknown action: {action}"}

        print(
            f"[{datetime.now().isoformat()}] MCP:{action} "
            f"on '{collection_name}' | filter={message.get('filter')} "
            f"data_keys={list(message.get('data', {}).keys())}"
        )

    except Exception as exc:
        response = {"status": "error", "message": str(exc)}

    return response
