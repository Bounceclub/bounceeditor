import json
import os
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse


ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "0.0.0.0")
PUBLIC_CONFIG_PATH = ROOT / "studio-config.json"
TIKTOK_TOKEN_PATH = ROOT / ".tiktok-token.json"
SECRETS_PATH = ROOT / ".studio-secrets.json"
SECRETS_EXAMPLE_PATH = ROOT / "studio-secrets.example.json"
TIKTOK_AUTH_URL = "https://www.tiktok.com/v2/auth/authorize/"
TIKTOK_TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"
TIKTOK_USER_INFO_URL = "https://open.tiktokapis.com/v2/user/info/"
TIKTOK_CREATOR_INFO_URL = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
TIKTOK_DIRECT_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/video/init/"
TIKTOK_UPLOAD_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/inbox/video/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
TIKTOK_SCOPES = ["user.info.basic", "video.upload", "video.publish"]
PUBLIC_CONFIG_DEFAULTS = {
    "teamName": "Bounce",
    "googleClientId": "",
    "driveFolder": "",
    "publicBaseUrl": "",
}
MAX_TITLE_LENGTH = 2200
CHUNK_SOFT_LIMIT = 64 * 1024 * 1024
MIN_CHUNK_SIZE = 5 * 1024 * 1024

# ── Drive shared library cache ─────────────────────────────────────────────
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
DRIVE_CACHE_TTL = 600  # seconds — refresh library every 10 min

_drive_cache: dict = {
    "files": [],
    "fetched_at": 0,
    "error": None,
}
_drive_access_token: dict = {
    "token": "",
    "expires_at": 0,
}


# ── Drive shared library helpers ───────────────────────────────────────────

def get_google_credentials() -> dict:
    """Read Google admin credentials from env variables."""
    return {
        "client_id": os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
        "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", "").strip(),
        "refresh_token": os.environ.get("GOOGLE_REFRESH_TOKEN", "").strip(),
    }


def get_google_access_token() -> str:
    """Get a fresh Google access token using the stored refresh token."""
    global _drive_access_token
    now = int(time.time())
    if _drive_access_token["token"] and _drive_access_token["expires_at"] > now + 60:
        return _drive_access_token["token"]

    creds = get_google_credentials()
    if not all(creds.values()):
        raise RuntimeError("Faltan credenciales de Google en variables de entorno (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN).")

    payload = http_request_json(
        GOOGLE_TOKEN_URL,
        method="POST",
        form_payload={
            "client_id": creds["client_id"],
            "client_secret": creds["client_secret"],
            "refresh_token": creds["refresh_token"],
            "grant_type": "refresh_token",
        },
    )
    token = payload.get("access_token", "")
    expires_in = int(payload.get("expires_in", 3600) or 3600)
    if not token:
        raise RuntimeError(f"Google no devolvió access_token: {payload}")

    _drive_access_token = {"token": token, "expires_at": now + expires_in}
    return token


def list_drive_folder(folder_id: str, token: str) -> list[dict]:
    """Recursively list all images and videos in a Drive folder."""
    results = []
    page_token = None

    while True:
        params: dict = {
            "q": f"'{folder_id}' in parents and trashed = false",
            "fields": "nextPageToken,files(id,name,mimeType,size,thumbnailLink,videoMediaMetadata,imageMediaMetadata,modifiedTime)",
            "pageSize": "200",
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token

        url = f"{GOOGLE_DRIVE_FILES_URL}?{urlencode(params)}"
        data = http_request_json(url, headers={"Authorization": f"Bearer {token}"})
        files = data.get("files", [])

        for f in files:
            mime = f.get("mimeType", "")
            if mime == "application/vnd.google-apps.folder":
                # Recurse into subfolder
                results.extend(list_drive_folder(f["id"], token))
            elif mime.startswith("video/") or mime.startswith("image/"):
                results.append({
                    "id": f["id"],
                    "name": f.get("name", ""),
                    "mimeType": mime,
                    "size": int(f.get("size", 0) or 0),
                    "thumbnailLink": f.get("thumbnailLink", ""),
                    "modifiedTime": f.get("modifiedTime", ""),
                    "type": "vid" if mime.startswith("video/") else "img",
                    "videoMeta": f.get("videoMediaMetadata", {}),
                    "imageMeta": f.get("imageMediaMetadata", {}),
                })

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return results


def get_drive_library(force: bool = False) -> dict:
    """Return cached library, refreshing if stale or forced."""
    global _drive_cache
    now = int(time.time())

    if not force and _drive_cache["files"] and (now - _drive_cache["fetched_at"]) < DRIVE_CACHE_TTL:
        return {"files": _drive_cache["files"], "cached": True, "error": None}

    config = get_public_config()
    folder_id = config.get("driveFolder", "").strip()
    if not folder_id:
        _drive_cache["error"] = "No hay carpeta de Drive configurada."
        return {"files": [], "cached": False, "error": _drive_cache["error"]}

    # Extract folder ID from URL if needed
    if "drive.google.com" in folder_id:
        parts = folder_id.split("/")
        for i, part in enumerate(parts):
            if part in ("folders", "d") and i + 1 < len(parts):
                folder_id = parts[i + 1].split("?")[0]
                break

    try:
        token = get_google_access_token()
        files = list_drive_folder(folder_id, token)
        _drive_cache = {"files": files, "fetched_at": now, "error": None}
        return {"files": files, "cached": False, "error": None}
    except Exception as e:  # noqa: BLE001
        _drive_cache["error"] = str(e)
        # Return stale cache if available
        if _drive_cache["files"]:
            return {"files": _drive_cache["files"], "cached": True, "error": str(e)}
        return {"files": [], "cached": False, "error": str(e)}


def ensure_files() -> None:
    if not SECRETS_EXAMPLE_PATH.exists():
        SECRETS_EXAMPLE_PATH.write_text(
            json.dumps(
                {
                    "tiktokClientKey": "paste-your-tiktok-client-key",
                    "tiktokClientSecret": "paste-your-tiktok-client-secret",
                    "tiktokRedirectUri": "https://your-domain.com/api/tiktok/callback",
                },
                indent=2,
            ),
            encoding="utf-8",
        )


def read_json(path: Path, default):
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def parse_json_body(handler: SimpleHTTPRequestHandler):
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8") or "{}")


def parse_multipart(content_type: str, body: bytes):
    envelope = (
        f"Content-Type: {content_type}\r\n"
        "MIME-Version: 1.0\r\n"
        "\r\n"
    ).encode("utf-8") + body
    message = BytesParser(policy=policy.default).parsebytes(envelope)

    fields = {}
    files = {}

    for part in message.iter_parts():
        disposition = part.get("Content-Disposition", "")
        if "form-data" not in disposition:
            continue

        name = part.get_param("name", header="content-disposition")
        filename = part.get_param("filename", header="content-disposition")
        payload = part.get_payload(decode=True) or b""

        if filename:
            files[name] = {
                "filename": filename,
                "content_type": part.get_content_type(),
                "data": payload,
            }
        else:
            charset = part.get_content_charset() or "utf-8"
            fields[name] = payload.decode(charset)

    return fields, files


def write_json_response(handler: SimpleHTTPRequestHandler, payload: dict, status: int = HTTPStatus.OK) -> None:
    raw = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(raw)))
    handler.end_headers()
    handler.wfile.write(raw)


def redirect(handler: SimpleHTTPRequestHandler, location: str, cookies: list[str] | None = None) -> None:
    handler.send_response(HTTPStatus.FOUND)
    handler.send_header("Location", location)
    for cookie in cookies or []:
        handler.send_header("Set-Cookie", cookie)
    handler.end_headers()


def parse_cookies(handler: SimpleHTTPRequestHandler) -> dict[str, str]:
    raw = handler.headers.get("Cookie", "")
    jar = SimpleCookie()
    jar.load(raw)
    return {key: morsel.value for key, morsel in jar.items()}


def get_public_config() -> dict:
    saved = read_json(PUBLIC_CONFIG_PATH, {})
    merged = dict(PUBLIC_CONFIG_DEFAULTS)
    merged.update({key: saved.get(key, value) for key, value in PUBLIC_CONFIG_DEFAULTS.items()})
    return merged


def save_public_config(payload: dict) -> dict:
    cleaned = {
        "teamName": str(payload.get("teamName", PUBLIC_CONFIG_DEFAULTS["teamName"])).strip() or "Bounce",
        "googleClientId": str(payload.get("googleClientId", "")).strip(),
        "driveFolder": str(payload.get("driveFolder", "")).strip(),
        "publicBaseUrl": str(payload.get("publicBaseUrl", "")).strip().rstrip("/"),
    }
    write_json(PUBLIC_CONFIG_PATH, cleaned)
    return cleaned


def get_secret_config() -> dict:
    file_payload = read_json(SECRETS_PATH, {})
    return {
        "tiktokClientKey": os.environ.get("TIKTOK_CLIENT_KEY", file_payload.get("tiktokClientKey", "")).strip(),
        "tiktokClientSecret": os.environ.get("TIKTOK_CLIENT_SECRET", file_payload.get("tiktokClientSecret", "")).strip(),
        "tiktokRedirectUri": os.environ.get("TIKTOK_REDIRECT_URI", file_payload.get("tiktokRedirectUri", "")).strip(),
    }


def get_effective_redirect_uri(handler: SimpleHTTPRequestHandler, public_config: dict, secret_config: dict) -> str:
    if secret_config["tiktokRedirectUri"]:
        return secret_config["tiktokRedirectUri"].rstrip("/")

    if public_config.get("publicBaseUrl"):
        return public_config["publicBaseUrl"].rstrip("/") + "/api/tiktok/callback"

    proto = handler.headers.get("X-Forwarded-Proto")
    if not proto:
        proto = "http"
    host = handler.headers.get("Host", f"127.0.0.1:{PORT}")
    return f"{proto}://{host}/api/tiktok/callback"


def get_tiktok_runtime(handler: SimpleHTTPRequestHandler) -> dict:
    public_config = get_public_config()
    secret_config = get_secret_config()
    redirect_uri = get_effective_redirect_uri(handler, public_config, secret_config)
    missing = []

    if not secret_config["tiktokClientKey"]:
        missing.append("tiktokClientKey")
    if not secret_config["tiktokClientSecret"]:
        missing.append("tiktokClientSecret")
    if not redirect_uri:
        missing.append("tiktokRedirectUri")

    return {
        "publicConfig": public_config,
        "secretConfig": secret_config,
        "redirectUri": redirect_uri,
        "scopes": TIKTOK_SCOPES,
        "configured": not missing,
        "missing": missing,
        "oauthReady": redirect_uri.startswith("https://"),
    }


def http_request_json(
    url: str,
    *,
    method: str = "GET",
    json_payload: dict | None = None,
    form_payload: dict | None = None,
    headers: dict | None = None,
    binary_payload: bytes | None = None,
):
    request_headers = dict(headers or {})
    data = None

    if json_payload is not None:
        data = json.dumps(json_payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json; charset=UTF-8")
    elif form_payload is not None:
        data = urlencode(form_payload).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
    elif binary_payload is not None:
        data = binary_payload

    request = urllib.request.Request(url, data=data, method=method, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"error": raw or error.reason}
        payload["http_status"] = error.code
        raise RuntimeError(json.dumps(payload))


def http_upload_binary(url: str, payload: bytes, mime_type: str) -> None:
    for start, end in build_chunks(len(payload)):
        chunk = payload[start:end]
        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(len(chunk)),
            "Content-Range": f"bytes {start}-{end - 1}/{len(payload)}",
        }
        request = urllib.request.Request(url, data=chunk, method="PUT", headers=headers)
        with urllib.request.urlopen(request, timeout=120):
            pass


def build_chunks(total_size: int) -> list[tuple[int, int]]:
    if total_size <= CHUNK_SOFT_LIMIT:
        return [(0, total_size)]

    chunks = []
    cursor = 0
    while cursor < total_size:
        end = min(cursor + CHUNK_SOFT_LIMIT, total_size)
        chunks.append((cursor, end))
        cursor = end

    if len(chunks) >= 2:
        last_start, last_end = chunks[-1]
        if (last_end - last_start) < MIN_CHUNK_SIZE:
            prev_start, _prev_end = chunks[-2]
            chunks[-2] = (prev_start, last_end)
            chunks.pop()

    return chunks


def normalize_token_bundle(bundle: dict) -> dict:
    now = int(time.time())
    return {
        "access_token": bundle.get("access_token", ""),
        "refresh_token": bundle.get("refresh_token", ""),
        "scope": bundle.get("scope", ""),
        "open_id": bundle.get("open_id", ""),
        "token_type": bundle.get("token_type", "Bearer"),
        "expires_in": int(bundle.get("expires_in", 0) or 0),
        "refresh_expires_in": int(bundle.get("refresh_expires_in", 0) or 0),
        "expires_at": now + int(bundle.get("expires_in", 0) or 0),
        "refresh_expires_at": now + int(bundle.get("refresh_expires_in", 0) or 0),
        "updated_at": now,
    }


def load_tiktok_token() -> dict:
    return read_json(TIKTOK_TOKEN_PATH, {})


def save_tiktok_token(payload: dict) -> dict:
    normalized = normalize_token_bundle(payload)
    write_json(TIKTOK_TOKEN_PATH, normalized)
    return normalized


def clear_tiktok_token() -> None:
    if TIKTOK_TOKEN_PATH.exists():
        TIKTOK_TOKEN_PATH.unlink()


def exchange_code_for_token(runtime: dict, code: str) -> dict:
    payload = http_request_json(
        TIKTOK_TOKEN_URL,
        method="POST",
        form_payload={
            "client_key": runtime["secretConfig"]["tiktokClientKey"],
            "client_secret": runtime["secretConfig"]["tiktokClientSecret"],
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": runtime["redirectUri"],
        },
        headers={"Cache-Control": "no-cache"},
    )
    return save_tiktok_token(payload)


def refresh_access_token(runtime: dict, token_bundle: dict) -> dict:
    if not token_bundle.get("refresh_token"):
        raise RuntimeError("No hay refresh token de TikTok guardado.")

    payload = http_request_json(
        TIKTOK_TOKEN_URL,
        method="POST",
        form_payload={
            "client_key": runtime["secretConfig"]["tiktokClientKey"],
            "client_secret": runtime["secretConfig"]["tiktokClientSecret"],
            "grant_type": "refresh_token",
            "refresh_token": token_bundle["refresh_token"],
        },
        headers={"Cache-Control": "no-cache"},
    )
    return save_tiktok_token(payload)


def ensure_access_token(runtime: dict) -> dict:
    token_bundle = load_tiktok_token()
    if not token_bundle:
        raise RuntimeError("La cuenta de TikTok todavía no está conectada.")

    now = int(time.time())
    if token_bundle.get("refresh_expires_at", 0) and token_bundle["refresh_expires_at"] <= now + 300:
        raise RuntimeError("El refresh token de TikTok venció. Hay que reconectar la cuenta.")

    if token_bundle.get("expires_at", 0) <= now + 300:
        token_bundle = refresh_access_token(runtime, token_bundle)

    return token_bundle


def tiktok_authorized_json(runtime: dict, token_bundle: dict, url: str, payload: dict | None = None, method: str = "POST") -> dict:
    return http_request_json(
        url,
        method=method,
        json_payload=payload,
        headers={
            "Authorization": f"Bearer {token_bundle['access_token']}",
        },
    )


def fetch_user_info(token_bundle: dict) -> dict:
    try:
        query = urlencode({"fields": "open_id,display_name,avatar_url,bio_description"})
        return http_request_json(
            f"{TIKTOK_USER_INFO_URL}?{query}",
            method="GET",
            headers={"Authorization": f"Bearer {token_bundle['access_token']}"},
        )
    except Exception:  # noqa: BLE001
        return {}


def fetch_creator_info(runtime: dict, token_bundle: dict) -> dict:
    return tiktok_authorized_json(runtime, token_bundle, TIKTOK_CREATOR_INFO_URL, {})


def fetch_publish_status(runtime: dict, token_bundle: dict, publish_id: str) -> dict:
    return tiktok_authorized_json(runtime, token_bundle, TIKTOK_STATUS_URL, {"publish_id": publish_id})


def build_authorize_url(runtime: dict, state_token: str) -> str:
    return (
        f"{TIKTOK_AUTH_URL}?"
        + urlencode(
            {
                "client_key": runtime["secretConfig"]["tiktokClientKey"],
                "response_type": "code",
                "scope": ",".join(runtime["scopes"]),
                "redirect_uri": runtime["redirectUri"],
                "state": state_token,
                "disable_auto_auth": "1",
            }
        )
    )


def serialize_cookie(name: str, value: str, *, max_age: int = 600) -> str:
    cookie = SimpleCookie()
    cookie[name] = value
    cookie[name]["path"] = "/"
    cookie[name]["httponly"] = True
    cookie[name]["samesite"] = "Lax"
    cookie[name]["max-age"] = str(max_age)
    return cookie.output(header="").strip()


def make_tiktok_status(handler: SimpleHTTPRequestHandler) -> dict:
    runtime = get_tiktok_runtime(handler)
    status = {
        "configured": runtime["configured"],
        "connected": False,
        "oauthReady": runtime["oauthReady"],
        "redirectUri": runtime["redirectUri"],
        "missingConfig": runtime["missing"],
        "scopes": runtime["scopes"],
        "creator": None,
        "privacyLevelOptions": [],
        "commentDisabled": False,
        "duetDisabled": False,
        "stitchDisabled": False,
        "maxVideoPostDurationSec": None,
        "notes": [],
    }

    if not runtime["configured"]:
        status["notes"].append("Faltan claves de TikTok en .studio-secrets.json o variables de entorno.")
        return status

    if not runtime["oauthReady"]:
        status["notes"].append("TikTok Login Kit web requiere redirect URI HTTPS.")

    token_bundle = load_tiktok_token()
    if not token_bundle:
        return status

    try:
        token_bundle = ensure_access_token(runtime)
        creator_payload = fetch_creator_info(runtime, token_bundle)
        creator_data = creator_payload.get("data", {})
        user_payload = fetch_user_info(token_bundle)
        user_data = user_payload.get("data", {}).get("user", {})

        status.update(
            {
                "connected": True,
                "creator": {
                    "username": creator_data.get("creator_username", ""),
                    "nickname": creator_data.get("creator_nickname", user_data.get("display_name", "")),
                    "avatarUrl": creator_data.get("creator_avatar_url", user_data.get("avatar_url", "")),
                    "bioDescription": user_data.get("bio_description", ""),
                    "openId": token_bundle.get("open_id", ""),
                },
                "privacyLevelOptions": creator_data.get("privacy_level_options", []),
                "commentDisabled": bool(creator_data.get("comment_disabled", False)),
                "duetDisabled": bool(creator_data.get("duet_disabled", False)),
                "stitchDisabled": bool(creator_data.get("stitch_disabled", False)),
                "maxVideoPostDurationSec": creator_data.get("max_video_post_duration_sec"),
            }
        )
    except Exception as error:  # noqa: BLE001
        status["notes"].append(f"No pude refrescar el estado de TikTok: {error}")

    return status


def normalize_title(payload: dict) -> str:
    title = str(payload.get("title", "")).strip()
    if len(title) > MAX_TITLE_LENGTH:
        return title[:MAX_TITLE_LENGTH]
    return title


def upload_video_to_tiktok(runtime: dict, token_bundle: dict, payload: dict, file_info: dict) -> dict:
    file_bytes = file_info["data"]
    file_size = len(file_bytes)
    if file_size <= 0:
        raise RuntimeError("El archivo a subir a TikTok está vacío.")

    mime_type = (file_info.get("content_type") or "video/webm").split(";")[0]
    chunks = build_chunks(file_size)
    source_info = {
        "source": "FILE_UPLOAD",
        "video_size": file_size,
        "chunk_size": chunks[0][1] - chunks[0][0],
        "total_chunk_count": len(chunks),
    }

    post_mode = str(payload.get("postMode", "DIRECT_POST")).upper()
    title = normalize_title(payload)

    if post_mode == "UPLOAD_TO_INBOX":
        init_url = TIKTOK_UPLOAD_INIT_URL
        init_payload = {"source_info": source_info}
    else:
        init_url = TIKTOK_DIRECT_INIT_URL
        privacy_level = str(payload.get("privacyLevel", "")).strip()
        if not privacy_level:
            raise RuntimeError("Para Direct Post necesitás elegir privacidad.")

        init_payload = {
            "post_info": {
                "title": title,
                "privacy_level": privacy_level,
                "disable_duet": not bool(payload.get("allowDuet", False)),
                "disable_comment": not bool(payload.get("allowComment", False)),
                "disable_stitch": not bool(payload.get("allowStitch", False)),
                "video_cover_timestamp_ms": int(payload.get("videoCoverTimestampMs", 0) or 0),
                "brand_content_toggle": bool(payload.get("brandContentToggle", False)),
                "brand_organic_toggle": bool(payload.get("brandOrganicToggle", False)),
            },
            "source_info": source_info,
        }

    init_response = tiktok_authorized_json(runtime, token_bundle, init_url, init_payload)
    upload_url = init_response.get("data", {}).get("upload_url", "")
    publish_id = init_response.get("data", {}).get("publish_id", "")
    if not upload_url or not publish_id:
        raise RuntimeError("TikTok no devolvió upload_url/publish_id.")

    http_upload_binary(upload_url, file_bytes, mime_type)

    status_payload = {}
    try:
        status_payload = fetch_publish_status(runtime, token_bundle, publish_id)
    except Exception:  # noqa: BLE001
        status_payload = {}

    return {
        "publishId": publish_id,
        "postMode": post_mode,
        "titleApplied": title if post_mode == "DIRECT_POST" else "",
        "status": status_payload.get("data", {}),
        "rawStatus": status_payload,
    }


class BounceHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/health":
            runtime = get_tiktok_runtime(self)
            write_json_response(
                self,
                {
                    "ok": True,
                    "publicConfigPath": str(PUBLIC_CONFIG_PATH),
                    "tiktokConfigured": runtime["configured"],
                    "redirectUri": runtime["redirectUri"],
                },
            )
            return

        if parsed.path == "/api/config":
            write_json_response(self, {"publicConfig": get_public_config()})
            return

        if parsed.path == "/api/drive/library":
            force = parse_qs(parsed.query).get("refresh", [""])[0] == "1"
            result = get_drive_library(force=force)
            write_json_response(self, result)
            return

        if parsed.path.startswith("/api/drive/proxy/"):
            self.handle_drive_proxy(parsed.path)
            return

        if parsed.path == "/api/tiktok/status":
            write_json_response(self, make_tiktok_status(self))
            return

        if parsed.path == "/api/tiktok/oauth/start":
            self.handle_tiktok_oauth_start()
            return

        if parsed.path == "/api/tiktok/callback":
            self.handle_tiktok_callback(parsed)
            return

        return super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        if parsed.path == "/api/config":
            self.handle_save_config()
            return

        if parsed.path == "/api/tiktok/disconnect":
            clear_tiktok_token()
            write_json_response(self, {"ok": True})
            return

        if parsed.path == "/api/tiktok/post":
            self.handle_tiktok_post()
            return

        write_json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def handle_drive_proxy(self, path: str):
        """Streaming proxy with Range support.
        - MP4/WebM/images: streamed directly with correct headers.
        - MOV/QuickTime/AVI/MKV: transcoded to MP4 via ffmpeg (if available).
        - If ffmpeg is missing and format is unsupported, returns a clear error.
        """
        CHUNK = 256 * 1024
        BROWSER_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg"}
        TRANSCODE_TYPES = {
            "video/quicktime", "video/x-msvideo", "video/x-ms-wmv",
            "video/x-matroska", "video/x-flv", "video/3gpp", "video/3gpp2",
        }

        file_id = path.removeprefix("/api/drive/proxy/").split("?")[0].strip()
        if not file_id:
            write_json_response(self, {"error": "File ID requerido."}, HTTPStatus.BAD_REQUEST)
            return

        try:
            token = get_google_access_token()
            drive_url = f"{GOOGLE_DRIVE_FILES_URL}/{file_id}?alt=media&supportsAllDrives=true"

            range_header = self.headers.get("Range", "")
            upstream_headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
            if range_header:
                upstream_headers["Range"] = range_header

            req = urllib.request.Request(drive_url, headers=upstream_headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "application/octet-stream").split(";")[0].strip()
                content_length = resp.headers.get("Content-Length", "")
                content_range = resp.headers.get("Content-Range", "")
                accept_ranges = resp.headers.get("Accept-Ranges", "bytes")

                needs_transcode = content_type in TRANSCODE_TYPES
                ffmpeg_bin = shutil.which("ffmpeg")

                if needs_transcode and ffmpeg_bin and not range_header:
                    # ── Transcode path ─────────────────────────────────────
                    tmp_in = tempfile.NamedTemporaryFile(suffix=".input", delete=False)
                    tmp_in_path = tmp_in.name
                    try:
                        while True:
                            chunk = resp.read(CHUNK)
                            if not chunk:
                                break
                            tmp_in.write(chunk)
                        tmp_in.close()

                        tmp_out_path = tmp_in_path + ".mp4"
                        result = subprocess.run(
                            [
                                ffmpeg_bin, "-y", "-i", tmp_in_path,
                                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                                "-c:a", "aac", "-movflags", "+faststart",
                                tmp_out_path,
                            ],
                            capture_output=True,
                            timeout=300,
                        )

                        if result.returncode != 0 or not os.path.exists(tmp_out_path):
                            write_json_response(
                                self,
                                {"error": f"ffmpeg falló: {result.stderr.decode('utf-8', errors='replace')[-400:]}"},
                                HTTPStatus.INTERNAL_SERVER_ERROR,
                            )
                            return

                        out_size = os.path.getsize(tmp_out_path)
                        self.send_response(HTTPStatus.OK)
                        self.send_header("Content-Type", "video/mp4")
                        self.send_header("Content-Disposition", "inline")
                        self.send_header("Content-Length", str(out_size))
                        self.send_header("Cache-Control", "private, max-age=600")
                        self.end_headers()

                        with open(tmp_out_path, "rb") as f:
                            while True:
                                chunk = f.read(CHUNK)
                                if not chunk:
                                    break
                                try:
                                    self.wfile.write(chunk)
                                except (BrokenPipeError, ConnectionResetError):
                                    break
                    finally:
                        for p in (tmp_in_path, tmp_in_path + ".mp4"):
                            try:
                                os.unlink(p)
                            except OSError:
                                pass
                    return

                if needs_transcode and not ffmpeg_bin:
                    # ffmpeg not installed — tell the client clearly
                    write_json_response(
                        self,
                        {"error": f"El archivo es {content_type} y ffmpeg no está instalado en el servidor. Instalá ffmpeg para convertir MOV/AVI/MKV a MP4."},
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                    )
                    return

                # ── Direct stream path (MP4, WebM, images, etc.) ──────────
                http_status = HTTPStatus.PARTIAL_CONTENT if status == 206 else HTTPStatus.OK
                self.send_response(http_status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Disposition", "inline")
                self.send_header("Accept-Ranges", accept_ranges or "bytes")
                self.send_header("Cache-Control", "private, max-age=300")
                if content_length:
                    self.send_header("Content-Length", content_length)
                if content_range:
                    self.send_header("Content-Range", content_range)
                self.end_headers()

                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    try:
                        self.wfile.write(chunk)
                    except (BrokenPipeError, ConnectionResetError):
                        break

        except urllib.error.HTTPError as e:
            write_json_response(self, {"error": f"Drive error {e.code}: {e.reason}"}, HTTPStatus.BAD_GATEWAY)
        except Exception as e:  # noqa: BLE001
            write_json_response(self, {"error": str(e)}, HTTPStatus.BAD_GATEWAY)

    def handle_save_config(self):
        payload = parse_json_body(self)
        saved = save_public_config(payload)
        write_json_response(self, {"publicConfig": saved})

    def handle_tiktok_oauth_start(self):
        runtime = get_tiktok_runtime(self)
        if not runtime["configured"]:
            redirect(self, "/?tiktok=missing-config")
            return

        if not runtime["oauthReady"]:
            redirect(self, "/?tiktok=https-required")
            return

        state_token = secrets.token_urlsafe(24)
        auth_url = build_authorize_url(runtime, state_token)
        redirect(self, auth_url, cookies=[serialize_cookie("tiktok_oauth_state", state_token)])

    def handle_tiktok_callback(self, parsed):
        query = parse_qs(parsed.query)
        error = query.get("error", [""])[0]
        error_description = query.get("error_description", [""])[0]
        code = query.get("code", [""])[0]
        returned_state = query.get("state", [""])[0]
        cookie_state = parse_cookies(self).get("tiktok_oauth_state", "")

        if error:
            redirect(
                self,
                "/?" + urlencode({"tiktok": "error", "message": error_description or error}),
                cookies=[serialize_cookie("tiktok_oauth_state", "", max_age=0)],
            )
            return

        if not code or not returned_state or returned_state != cookie_state:
            redirect(
                self,
                "/?" + urlencode({"tiktok": "error", "message": "OAuth state inválido o callback incompleto."}),
                cookies=[serialize_cookie("tiktok_oauth_state", "", max_age=0)],
            )
            return

        try:
            runtime = get_tiktok_runtime(self)
            exchange_code_for_token(runtime, code)
            redirect(
                self,
                "/?" + urlencode({"tiktok": "connected"}),
                cookies=[serialize_cookie("tiktok_oauth_state", "", max_age=0)],
            )
        except Exception as error_obj:  # noqa: BLE001
            redirect(
                self,
                "/?" + urlencode({"tiktok": "error", "message": str(error_obj)}),
                cookies=[serialize_cookie("tiktok_oauth_state", "", max_age=0)],
            )

    def handle_tiktok_post(self):
        runtime = get_tiktok_runtime(self)
        if not runtime["configured"]:
            write_json_response(
                self,
                {"error": "TikTok no está configurado todavía. Completá .studio-secrets.json primero."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", "0"))
        if "multipart/form-data" not in content_type:
            write_json_response(self, {"error": "Esperaba multipart/form-data."}, HTTPStatus.BAD_REQUEST)
            return

        body = self.rfile.read(content_length)
        fields, files = parse_multipart(content_type, body)
        if "payload" not in fields or "file" not in files:
            write_json_response(self, {"error": "Falta payload o file."}, HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = json.loads(fields["payload"])
        except json.JSONDecodeError:
            write_json_response(self, {"error": "Payload de TikTok inválido."}, HTTPStatus.BAD_REQUEST)
            return

        file_info = files["file"]
        mime_type = (file_info.get("content_type") or "").split(";")[0]
        if not mime_type.startswith("video/"):
            write_json_response(
                self,
                {"error": "La integración actual de TikTok desde esta web soporta video solamente."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        if not bool(payload.get("musicConsent", False)):
            write_json_response(
                self,
                {"error": 'TikTok exige consentimiento explícito. Marcá "Music Usage Confirmation".'},
                HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            token_bundle = ensure_access_token(runtime)
            result = upload_video_to_tiktok(runtime, token_bundle, payload, file_info)
            write_json_response(self, {"ok": True, "result": result})
        except Exception as error:  # noqa: BLE001
            write_json_response(self, {"error": str(error)}, HTTPStatus.BAD_REQUEST)


def main() -> None:
    ensure_files()
    server = ThreadingHTTPServer((HOST, PORT), BounceHandler)
    print(f"Bounce Drive Media Studio running on http://{HOST}:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
