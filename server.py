import json
import logging
import os
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import io
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


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
TIKTOK_IMAGE_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/image/init/"
TIKTOK_STATUS_URL = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
TIKTOK_SCOPES = ["user.info.basic", "video.upload", "video.publish", "image.upload", "image.publish"]
PUBLIC_CONFIG_DEFAULTS = {
    "teamName": "Bounce",
    "googleClientId": "",
    "driveFolder": "",
    "publicBaseUrl": "",
}
MAX_TITLE_LENGTH = 2200
CHUNK_SOFT_LIMIT = 64 * 1024 * 1024
MIN_CHUNK_SIZE = 5 * 1024 * 1024
FFMPEG_PATH = None
TEMP_DIR = None


def detect_ffmpeg() -> str | None:
    """Detect if ffmpeg is available and return its path."""
    global FFMPEG_PATH
    if FFMPEG_PATH is not None:
        return FFMPEG_PATH

    # Try to find ffmpeg in common locations
    ffmpeg_names = ['ffmpeg', 'ffmpeg.exe']
    common_paths = [
        r'C:\ffmpeg\ffmpeg.exe',
        r'C:\Program Files\ffmpeg\bin\ffmpeg.exe',
        r'C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe',
        r'C:\Users\lucas\AppData\Local\Microsoft\WinGet\Packages\yt-dlp.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-N-120858-gae448e00af-win64-gpl\bin\ffmpeg.exe',
        '/usr/bin/ffmpeg',
        '/usr/local/bin/ffmpeg',
        '/opt/homebrew/bin/ffmpeg',
    ]

    # First try PATH
    for name in ffmpeg_names:
        ffmpeg_path = shutil.which(name)
        if ffmpeg_path:
            # Test if it actually works
            try:
                result = subprocess.run(
                    [ffmpeg_path, '-version'],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if result.returncode == 0 and 'ffmpeg' in result.stdout.lower():
                    FFMPEG_PATH = ffmpeg_path
                    print(f"[FFMPEG] Found ffmpeg in PATH at: {FFMPEG_PATH}")
                    return FFMPEG_PATH
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                print(f"[FFMPEG] Error testing ffmpeg at {ffmpeg_path}: {e}")
                continue

    # Try common paths
    for path in common_paths:
        if Path(path).exists():
            try:
                result = subprocess.run(
                    [path, '-version'],
                    capture_output=True,
                    timeout=5,
                    text=True
                )
                if result.returncode == 0 and 'ffmpeg' in result.stdout.lower():
                    FFMPEG_PATH = path
                    print(f"[FFMPEG] Found ffmpeg at common path: {FFMPEG_PATH}")
                    return FFMPEG_PATH
            except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
                print(f"[FFMPEG] Error testing ffmpeg at {path}: {e}")
                continue

    print("[FFMPEG] ffmpeg not found in system PATH or common locations")
    FFMPEG_PATH = None
    return None


def get_temp_dir() -> Path:
    """Get or create temporary directory for transcoding."""
    global TEMP_DIR
    if TEMP_DIR is None:
        TEMP_DIR = Path(tempfile.mkdtemp(prefix='bounce_transcode_'))
        print(f"[FFMPEG] Created temp directory: {TEMP_DIR}")
    return TEMP_DIR


def cleanup_temp_dir() -> None:
    """Clean up temporary directory."""
    global TEMP_DIR
    if TEMP_DIR is not None and TEMP_DIR.exists():
        try:
            shutil.rmtree(TEMP_DIR)
            print(f"[FFMPEG] Cleaned up temp directory: {TEMP_DIR}")
        except Exception as e:
            print(f"[FFMPEG] Error cleaning up temp directory: {e}")
        finally:
            TEMP_DIR = None


def generate_placeholder_thumbnail(file_type: str = "VID") -> bytes:
    """Generate a placeholder thumbnail image.

    Args:
        file_type: File type to display on the thumbnail (VID, IMG, etc.)

    Returns:
        PNG image bytes
    """
    if PIL_AVAILABLE:
        try:
            # Create a dark placeholder image
            img = Image.new('RGB', (320, 180), color='#1a1a2e')
            draw = ImageDraw.Draw(img)

            # Add a simple movie icon (rectangle with play triangle)
            # Background rectangle
            draw.rectangle([100, 50, 220, 130], fill='#16213e', outline='#0f3460', width=2)

            # Play triangle
            draw.polygon([(145, 70), (145, 110), (185, 90)], fill='#e94560')

            # Add file type text
            text_color = '#ffffff'
            try:
                # Try to use a default font
                font = ImageFont.load_default()
                draw.text((10, 155), file_type.upper(), fill=text_color, font=font)
            except:
                # If font loading fails, skip text
                pass

            # Convert to PNG bytes
            img_io = io.BytesIO()
            img.save(img_io, 'PNG')
            return img_io.getvalue()

        except Exception as e:
            logger.error(f"Error generating placeholder thumbnail: {e}")

    # Fallback to simple 1x1 PNG if PIL is not available or on error
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\x0d\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'


def transcode_video_to_mp4(input_data: bytes, max_duration: int = 30) -> bytes:
    """
    Transcode video to MP4 format using ffmpeg.

    Args:
        input_data: Input video data as bytes
        max_duration: Maximum duration in seconds for preview transcoding

    Returns:
        Transcoded video data as bytes

    Raises:
        RuntimeError: If ffmpeg is not available or transcoding fails
    """
    ffmpeg_path = detect_ffmpeg()
    if not ffmpeg_path:
        raise RuntimeError("ffmpeg no está disponible en el servidor")

    temp_dir = get_temp_dir()
    input_path = temp_dir / f"input_{secrets.token_hex(8)}.mp4"
    output_path = temp_dir / f"output_{secrets.token_hex(8)}.mp4"

    try:
        # Write input data to temporary file
        input_path.write_bytes(input_data)
        print(f"[FFMPEG] Input file size: {len(input_data)} bytes")

        # Build ffmpeg command for preview transcoding
        # -t: limit duration for preview
        # -c:v libx264: video codec
        # -c:a aac: audio codec
        # -movflags +faststart: optimize for web streaming
        # -y: overwrite output file
        cmd = [
            ffmpeg_path,
            '-i', str(input_path),
            '-t', str(max_duration),
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-movflags', '+faststart',
            '-y',
            str(output_path)
        ]

        print(f"[FFMPEG] Running transcoding command: {' '.join(cmd)}")

        # Run ffmpeg with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=120,  # 2 minute timeout
            text=True
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout or "Unknown error"
            print(f"[FFMPEG] Transcoding failed: {error_msg}")
            raise RuntimeError(f"Error en ffmpeg: {error_msg}")

        if not output_path.exists():
            raise RuntimeError("ffmpeg no generó archivo de salida")

        # Read transcoded output
        output_data = output_path.read_bytes()
        print(f"[FFMPEG] Output file size: {len(output_data)} bytes")

        if len(output_data) == 0:
            raise RuntimeError("Archivo de salida vacío después de transcoding")

        return output_data

    except subprocess.TimeoutExpired:
        raise RuntimeError("Transcoding timeout - ffmpeg tomó demasiado tiempo")
    except Exception as e:
        print(f"[FFMPEG] Transcoding error: {e}")
        raise RuntimeError(f"Error durante transcoding: {str(e)}")
    finally:
        # Clean up temporary files
        try:
            if input_path.exists():
                input_path.unlink()
            if output_path.exists():
                output_path.unlink()
        except Exception as e:
            print(f"[FFMPEG] Error cleaning up temp files: {e}")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)
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
            file_name = f.get("name", "").lower()

            # Log ALL files for debugging F4V detection
            print(f"[DRIVE] File: {f.get('name')}, mimeType: {mime}, size: {f.get('size')}", flush=True)

            if mime == "application/vnd.google-apps.folder":
                # Recurse into subfolder
                results.extend(list_drive_folder(f["id"], token))
            elif (mime.startswith("video/") or mime.startswith("image/") or
                  mime in ["video/x-f4v", "video/f4v", "application/f4v"] or
                  file_name.endswith(".f4v")):

                # Determine file type - F4V should always be 'vid'
                if mime.startswith("video/") or mime in ["video/x-f4v", "video/f4v", "application/f4v"] or file_name.endswith(".f4v"):
                    file_type = "vid"
                else:
                    file_type = "img"

                # Extract video metadata
                video_meta = f.get("videoMediaMetadata", {})
                image_meta = f.get("imageMediaMetadata", {})

                # For F4V files, Drive might not provide videoMediaMetadata
                # Try to extract basic info from the file itself
                if not video_meta and file_type == "vid":
                    # Create minimal metadata for F4V files
                    file_size = int(f.get("size", 0) or 0)
                    # Estimate duration based on file size (rough estimate: 1MB ≈ 5 seconds for standard quality)
                    estimated_duration_ms = max(1000, int(file_size / (1024 * 1024) * 5000)) if file_size > 0 else 0

                    video_meta = {
                        "durationMillis": estimated_duration_ms,
                        "height": 1080,  # Default assumption
                        "width": 1920,   # Default assumption
                    }
                    print(f"[DRIVE] F4V file {f.get('name')}: estimated duration {estimated_duration_ms}ms from size {file_size}", flush=True)

                print(f"[DRIVE] Including file: {f.get('name')}, type: {file_type}, mimeType: {mime}, videoMeta: {video_meta}", flush=True)

                results.append({
                    "id": f["id"],
                    "name": f.get("name", ""),
                    "mimeType": mime,
                    "size": int(f.get("size", 0) or 0),
                    "thumbnailLink": f.get("thumbnailLink", ""),
                    "modifiedTime": f.get("modifiedTime", ""),
                    "type": file_type,
                    "videoMeta": video_meta,
                    "imageMeta": image_meta,
                })
            else:
                print(f"[DRIVE] Filtering out file: {f.get('name')}, mimeType: {mime}", flush=True)

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
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
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


def upload_image_to_tiktok(runtime: dict, token_bundle: dict, payload: dict, file_info: dict) -> dict:
    """Upload a single image to TikTok."""
    file_bytes = file_info["data"]
    file_size = len(file_bytes)
    if file_size <= 0:
        raise RuntimeError("El archivo de imagen está vacío.")

    mime_type = (file_info.get("content_type") or "image/jpeg").split(";")[0]

    # Initialize image upload
    init_payload = {
        "post_info": {
            "title": normalize_title(payload),
            "privacy_level": str(payload.get("privacyLevel", "")).strip(),
            "disable_duet": not bool(payload.get("allowDuet", False)),
            "disable_comment": not bool(payload.get("allowComment", False)),
            "disable_stitch": not bool(payload.get("allowStitch", False)),
            "brand_content_toggle": bool(payload.get("brandContentToggle", False)),
            "brand_organic_toggle": bool(payload.get("brandOrganicToggle", False)),
        }
    }

    init_response = tiktok_authorized_json(runtime, token_bundle, TIKTOK_IMAGE_INIT_URL, init_payload)
    upload_url = init_response.get("data", {}).get("upload_url", "")
    publish_id = init_response.get("data", {}).get("publish_id", "")

    if not upload_url or not publish_id:
        raise RuntimeError("TikTok no devolvió upload_url/publish_id para imagen.")

    # Upload the image
    http_upload_binary(upload_url, file_bytes, mime_type)

    # Check status
    status_payload = {}
    try:
        status_payload = fetch_publish_status(runtime, token_bundle, publish_id)
    except Exception:  # noqa: BLE001
        status_payload = {}

    return {
        "publishId": publish_id,
        "postMode": "DIRECT_POST",
        "titleApplied": normalize_title(payload),
        "status": status_payload.get("data", {}),
        "rawStatus": status_payload,
    }


def upload_carousel_to_tiktok(runtime: dict, token_bundle: dict, payload: dict, files_info: list) -> dict:
    """Upload a carousel (multiple images) to TikTok."""
    if not files_info or len(files_info) == 0:
        raise RuntimeError("No se proporcionaron imágenes para el carrusel.")

    if len(files_info) > 5:
        raise RuntimeError("Máximo 5 imágenes permitidas para carrusel de TikTok.")

    # Initialize carousel upload
    carousel_images = []
    for i, file_info in enumerate(files_info):
        file_bytes = file_info["data"]
        file_size = len(file_bytes)
        if file_size <= 0:
            raise RuntimeError(f"La imagen {i+1} está vacía.")

        mime_type = (file_info.get("content_type") or "image/jpeg").split(";")[0]

        # Initialize each image upload
        image_init_payload = {
            "post_info": {
                "title": normalize_title(payload),
                "privacy_level": str(payload.get("privacyLevel", "")).strip(),
                "disable_duet": not bool(payload.get("allowDuet", False)),
                "disable_comment": not bool(payload.get("allowComment", False)),
                "disable_stitch": not bool(payload.get("allowStitch", False)),
                "brand_content_toggle": bool(payload.get("brandContentToggle", False)),
                "brand_organic_toggle": bool(payload.get("brandOrganicToggle", False)),
            }
        }

        image_init_response = tiktok_authorized_json(runtime, token_bundle, TIKTOK_IMAGE_INIT_URL, image_init_payload)
        upload_url = image_init_response.get("data", {}).get("upload_url", "")
        image_publish_id = image_init_response.get("data", {}).get("publish_id", "")

        if not upload_url or not image_publish_id:
            raise RuntimeError(f"TikTok no devolvió upload_url/publish_id para imagen {i+1}.")

        # Upload the image
        http_upload_binary(upload_url, file_bytes, mime_type)

        carousel_images.append({
            "publish_id": image_publish_id,
            "index": i
        })

    # Use the first image's publish_id as the main publish_id
    main_publish_id = carousel_images[0]["publish_id"]

    # Check status
    status_payload = {}
    try:
        status_payload = fetch_publish_status(runtime, token_bundle, main_publish_id)
    except Exception:  # noqa: BLE001
        status_payload = {}

    return {
        "publishId": main_publish_id,
        "postMode": "DIRECT_POST",
        "titleApplied": normalize_title(payload),
        "carouselImages": len(carousel_images),
        "status": status_payload.get("data", {}),
        "rawStatus": status_payload,
    }


class BounceHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "86400")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/tiktokx4L5xZ76S1ZzjnUOyic3ZpIXKRYnmhlS.txt':
            content = b'tiktok-developers-site-verification=x4L5xZ76S1ZzjnUOyic3ZpIXKRYnmhlS'
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
            return

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

        if parsed.path.startswith("/api/drive/thumbnail/"):
            file_id = parsed.path.removeprefix("/api/drive/thumbnail/").split("?")[0].strip()
            if file_id:
                self.handle_drive_thumbnail(file_id)
            else:
                write_json_response(self, {"error": "File ID requerido."}, HTTPStatus.BAD_REQUEST)
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

        if parsed.path == "/api/ffmpeg/status":
            self.handle_ffmpeg_status()
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

        if parsed.path == "/api/transcode/video":
            self.handle_transcode_video()
            return

        write_json_response(self, {"error": "Not found"}, HTTPStatus.NOT_FOUND)

    def do_HEAD(self):
        """Handle HEAD requests - return headers only, no body.
        
        This is important for video elements that make HEAD requests before
        loading to check if the resource exists and get metadata.
        """
        parsed = urlparse(self.path)

        if parsed.path.startswith("/api/drive/proxy/"):
            # For proxy requests, we need to get the headers from Drive
            # but not stream the content
            file_id = parsed.path.removeprefix("/api/drive/proxy/").split("?")[0].strip()
            if not file_id:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.end_headers()
                return

            try:
                token = get_google_access_token()
                drive_url = f"{GOOGLE_DRIVE_FILES_URL}/{file_id}?alt=media&supportsAllDrives=true"

                req = urllib.request.Request(drive_url, method="HEAD", headers={"Authorization": f"Bearer {token}"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    content_type = resp.headers.get("Content-Type", "application/octet-stream").split(";")[0].strip()
                    content_length = resp.headers.get("Content-Length", "")
                    accept_ranges = resp.headers.get("Accept-Ranges", "bytes")

                    # Determine if we need to transcode (MOV to MP4)
                    TRANSCODE_TYPES = {
                        "video/quicktime", "video/x-msvideo", "video/x-ms-wmv",
                        "video/x-matroska", "video/x-flv", "video/3gpp", "video/3gpp2",
                        "video/x-f4v", "video/f4v", "application/f4v",  # Added F4V support
                    }
                    needs_transcode = content_type in TRANSCODE_TYPES

                    # If transcoding, we return MP4 headers
                    # Otherwise, return the original content-type
                    final_content_type = "video/mp4" if needs_transcode else content_type

                    self.send_response(HTTPStatus.OK)
                    self.send_header("Content-Type", final_content_type)
                    self.send_header("Content-Disposition", "inline")
                    self.send_header("Accept-Ranges", accept_ranges or "bytes")
                    self.send_header("Cache-Control", "private, max-age=300")
                    if content_length and not needs_transcode:
                        self.send_header("Content-Length", content_length)
                    self.end_headers()
                    return

            except urllib.error.HTTPError as e:
                logger.error(f"HTTPError in HEAD request for {file_id}: {e.code} - {e.reason}")
                self.send_response(e.code)
                self.end_headers()
                return
            except Exception as e:
                logger.error(f"Error in HEAD request for {file_id}: {str(e)}")
                self.send_response(HTTPStatus.INTERNAL_SERVER_ERROR)
                self.end_headers()
                return

        # For other endpoints, return 404 or handle as needed
        self.send_response(HTTPStatus.NOT_FOUND)
        self.end_headers()

    def handle_drive_proxy(self, path: str):
        """Streaming proxy with Range support.
        - MP4/WebM/images: streamed directly with correct headers.
        - MOV/QuickTime/AVI/MKV/F4V: transcoded to MP4 via ffmpeg (if available).
        - If ffmpeg is missing and format is unsupported, returns a clear error.
        """
        CHUNK = 256 * 1024
        BROWSER_VIDEO_TYPES = {"video/mp4", "video/webm", "video/ogg"}
        TRANSCODE_TYPES = {
            "video/quicktime", "video/x-msvideo", "video/x-ms-wmv",
            "video/x-matroska", "video/x-flv", "video/3gpp", "video/3gpp2",
            "video/x-f4v", "video/f4v", "application/f4v",  # Added F4V support
            "video/mp4",  # Also transcode MP4 to ensure compatibility
            "video/x-m4v", "video/x-m4p",  # Additional MOV variants
        }

        file_id = path.removeprefix("/api/drive/proxy/").split("?")[0].strip()
        if not file_id:
            write_json_response(self, {"error": "File ID requerido."}, HTTPStatus.BAD_REQUEST)
            return

        # Parse query parameters for preview mode
        parsed = urlparse(self.path)

        logger.info(f"[PROXY] file_id={file_id} starting proxy request")
        try:
            token = get_google_access_token()
            logger.info(f"[PROXY] file_id={file_id} Got Google access token")
            drive_url = f"{GOOGLE_DRIVE_FILES_URL}/{file_id}?alt=media&supportsAllDrives=true"

            range_header = self.headers.get("Range", "")
            upstream_headers: dict[str, str] = {"Authorization": f"Bearer {token}"}
            if range_header:
                upstream_headers["Range"] = range_header

            logger.info(f"[PROXY] file_id={file_id} Requesting from Drive: {drive_url}")
            req = urllib.request.Request(drive_url, headers=upstream_headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "application/octet-stream").split(";")[0].strip()
                content_length = resp.headers.get("Content-Length", "")
                logger.info(f"[PROXY] file_id={file_id} content_type={content_type} size={content_length}")
                content_range = resp.headers.get("Content-Range", "")
                accept_ranges = resp.headers.get("Accept-Ranges", "bytes")

                needs_transcode = content_type in TRANSCODE_TYPES
                logger.info(f"[PROXY] file_id={file_id} content_type={content_type} needs_transcode={needs_transcode} TRANSCODE_TYPES={TRANSCODE_TYPES}")

                # Try to get ffmpeg binary
                ffmpeg_bin = None
                try:
                    import imageio_ffmpeg
                    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
                    logger.info(f"[PROXY] file_id={file_id} ffmpeg from imageio_ffmpeg: {ffmpeg_bin}")
                except Exception as e:
                    logger.warning(f"[PROXY] file_id={file_id} imageio_ffmpeg failed: {e}")
                    ffmpeg_bin = shutil.which("ffmpeg")
                    logger.info(f"[PROXY] file_id={file_id} ffmpeg from shutil.which: {ffmpeg_bin}")

                logger.info(f"[PROXY] file_id={file_id} content_type={content_type} needs_transcode={needs_transcode} ffmpeg={ffmpeg_bin}")

                if needs_transcode and ffmpeg_bin:
                    # ── Transcode path ─────────────────────────────────────
                    # Note: We ignore range headers for transcoding since we need to process the entire file
                    # The browser will handle seeking on the transcoded output
                    logger.info(f"[PROXY] file_id={file_id} Starting transcoding path")
                    tmp_in = tempfile.NamedTemporaryFile(suffix=".input", delete=False)
                    tmp_in_path = tmp_in.name
                    tmp_out_path = None

                    try:
                        # Download entire file first
                        logger.info(f"[PROXY] file_id={file_id} Downloading file for transcoding")
                        downloaded_size = 0
                        while True:
                            chunk = resp.read(CHUNK)
                            if not chunk:
                                break
                            tmp_in.write(chunk)
                            downloaded_size += len(chunk)
                        tmp_in.close()

                        # Check file size for cloud environment limits
                        file_size_mb = downloaded_size / (1024 * 1024)
                        logger.info(f"[PROXY] file_id={file_id} Downloaded {file_size_mb:.2f} MB")

                        if is_preview and file_size_mb > 100:
                            logger.warning(f"[PROXY] file_id={file_id} File too large for preview ({file_size_mb:.2f} MB)")
                            write_json_response(
                                self,
                                {"error": f"Archivo muy grande para preview ({file_size_mb:.1f} MB). En Render, el preview funciona mejor con videos menores a 100 MB. Usá la exportación completa para videos grandes."},
                                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                            )
                            return

                        if not is_preview and file_size_mb > 500:
                            logger.warning(f"[PROXY] file_id={file_id} File too large for full export ({file_size_mb:.2f} MB)")
                            write_json_response(
                                self,
                                {"error": f"Archivo muy grande para exportación ({file_size_mb:.1f} MB). En Render, la exportación completa tiene un límite de 500 MB. Considerá comprimir el video antes de subirlo."},
                                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                            )
                            return

                        tmp_out_path = tmp_in_path + ".mp4"

                        # Check if this is a preview request (first 10 seconds only for faster preview on cloud services)
                        is_preview = "preview" in parsed.query  # Check for ?preview=1 in URL
                        if is_preview:
                            # For preview: transcode only first 10 seconds for speed (reduced from 60s for cloud services)
                            duration_limit = ["-ss", "0", "-t", "10"]
                            logger.info(f"[PROXY] file_id={file_id} Preview mode: transcoding first 10 seconds only")
                        else:
                            # For full export: transcode entire video
                            duration_limit = []
                            logger.info(f"[PROXY] file_id={file_id} Full mode: transcoding entire video")

                        logger.info(f"[PROXY] file_id={file_id} Starting ffmpeg transcode, preview={is_preview}")
                        logger.info(f"[PROXY] file_id={file_id} ffmpeg binary: {ffmpeg_bin}")
                        logger.info(f"[PROXY] file_id={file_id} Input file: {tmp_in_path}, Output file: {tmp_out_path}")

                        ffmpeg_cmd = [
                            ffmpeg_bin, "-y", "-i", tmp_in_path,
                            # Video codec settings optimized for speed
                            "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                            # Ensure proper pixel format for web compatibility
                            "-pix_fmt", "yuv420p",
                            # Ensure proper color space
                            "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                            # Audio codec optimized for speed
                            "-c:a", "aac", "-b:a", "96k",
                            # MP4 optimization for streaming
                            "-movflags", "+faststart",
                            # Ensure proper frame rate (use source frame rate if available)
                            "-r", "30",
                            # Additional optimizations for cloud environments
                            "-threads", "2",
                        ] + duration_limit + [tmp_out_path]

                        logger.info(f"[PROXY] file_id={file_id} Running ffmpeg command: {' '.join(ffmpeg_cmd)}")

                        result = subprocess.run(
                            ffmpeg_cmd,
                            capture_output=True,
                            timeout=120,  # Reduced timeout to 2 minutes for cloud services (was 10 minutes)
                        )

                        logger.info(f"[PROXY] file_id={file_id} ffmpeg completed: returncode={result.returncode}")
                        logger.info(f"[PROXY] file_id={file_id} ffmpeg stdout: {result.stdout.decode('utf-8', errors='replace')[-500:]}")
                        logger.info(f"[PROXY] file_id={file_id} ffmpeg stderr: {result.stderr.decode('utf-8', errors='replace')[-500:]}")
                        logger.info(f"[PROXY] file_id={file_id} Output file exists: {os.path.exists(tmp_out_path)}")

                        if result.returncode != 0:
                            error_msg = result.stderr.decode('utf-8', errors='replace')[-400:]
                            logger.error(f"[PROXY] file_id={file_id} ffmpeg transcode failed: {error_msg}")
                            write_json_response(
                                self,
                                {"error": f"ffmpeg falló: {error_msg}"},
                                HTTPStatus.INTERNAL_SERVER_ERROR,
                            )
                            return

                        if not os.path.exists(tmp_out_path):
                            logger.error(f"[PROXY] file_id={file_id} ffmpeg output file not found: {tmp_out_path}")
                            write_json_response(
                                self,
                                {"error": "ffmpeg no generó el archivo de salida"},
                                HTTPStatus.INTERNAL_SERVER_ERROR,
                            )
                            return

                        out_size = os.path.getsize(tmp_out_path)
                        if out_size == 0:
                            logger.error(f"[PROXY] file_id={file_id} ffmpeg output file is empty: {tmp_out_path}")
                            write_json_response(
                                self,
                                {"error": "ffmpeg generó un archivo vacío"},
                                HTTPStatus.INTERNAL_SERVER_ERROR,
                            )
                            return

                        logger.info(f"[PROXY] file_id={file_id} Transcoding completed successfully, output size: {out_size} bytes")
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

                    except subprocess.TimeoutExpired:
                        logger.error(f"[PROXY] file_id={file_id} ffmpeg transcode timeout (120s)")
                        write_json_response(
                            self,
                            {"error": "ffmpeg tomó demasiado tiempo (timeout > 2 minutos). En el entorno de Render, los videos grandes pueden fallar. Intenta con un video más pequeño o usa la exportación completa en lugar de preview."},
                            HTTPStatus.REQUEST_TIMEOUT,
                        )
                        return
                    except MemoryError:
                        logger.error(f"[PROXY] file_id={file_id} ffmpeg transcode out of memory")
                        write_json_response(
                            self,
                            {"error": "Sin memoria para procesar el video. El entorno de Render tiene límites de memoria. Intenta con un video más pequeño."},
                            HTTPStatus.INTERNAL_SERVER_ERROR,
                        )
                        return
                    except Exception as e:
                        logger.error(f"[PROXY] file_id={file_id} ffmpeg transcode exception: {e}")
                        # Check if it's a specific ffmpeg error
                        error_str = str(e).lower()
                        if "memory" in error_str:
                            write_json_response(
                                self,
                                {"error": "Sin memoria para procesar el video. Intenta con un video más pequeño."},
                                HTTPStatus.INTERNAL_SERVER_ERROR,
                            )
                        else:
                            write_json_response(
                                self,
                                {"error": f"Error durante transcodificación: {str(e)}"},
                                HTTPStatus.INTERNAL_SERVER_ERROR,
                            )
                        return
                    finally:
                        # Clean up temporary files
                        for p in (tmp_in_path, tmp_out_path):
                            if p and os.path.exists(p):
                                try:
                                    os.unlink(p)
                                except OSError:
                                    pass
                    return

                if needs_transcode and not ffmpeg_bin:
                    logger.warning(f"ffmpeg not available for {content_type} file")
                    # ffmpeg not installed — tell the client clearly
                    write_json_response(
                        self,
                        {"error": f"El archivo es {content_type} y ffmpeg no está instalado en el servidor. Instalá ffmpeg para convertir MOV/AVI/MKV a MP4."},
                        HTTPStatus.UNPROCESSABLE_ENTITY,
                    )
                    return

                # ── Direct stream path (MP4, WebM, images, etc.) ──────────
                logger.info(f"Direct streaming: {content_type}, status: {status}")
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

                try:
                    while True:
                        chunk = resp.read(CHUNK)
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except (BrokenPipeError, ConnectionResetError):
                            break
                except Exception as stream_error:
                    logger.error(f"Error during streaming: {stream_error}")
                    # Can't send error response after headers sent
                    return

        except urllib.error.HTTPError as e:
            logger.error(f"HTTPError proxying {file_id}: {e.code} - {e.reason}")
            # Return more specific error codes instead of generic 502
            if e.code == 404:
                write_json_response(self, {"error": f"Archivo no encontrado en Drive: {e.reason}"}, HTTPStatus.NOT_FOUND)
            elif e.code == 403:
                write_json_response(self, {"error": f"No tenés permiso para acceder a este archivo: {e.reason}"}, HTTPStatus.FORBIDDEN)
            elif e.code == 401:
                write_json_response(self, {"error": f"Error de autenticación con Google: {e.reason}"}, HTTPStatus.UNAUTHORIZED)
            else:
                write_json_response(self, {"error": f"Drive error {e.code}: {e.reason}"}, HTTPStatus.BAD_GATEWAY)
        except urllib.error.URLError as e:
            logger.error(f"URLError proxying {file_id}: {e.reason}")
            write_json_response(self, {"error": f"Error de conexión con Drive: {e.reason}"}, HTTPStatus.SERVICE_UNAVAILABLE)
        except TimeoutError as e:
            logger.error(f"Timeout proxying {file_id}: {str(e)}")
            write_json_response(self, {"error": "Timeout al conectar con Drive. El archivo puede ser muy grande o hay problemas de conexión."}, HTTPStatus.REQUEST_TIMEOUT)
        except Exception as e:  # noqa: BLE001
            logger.error(f"Error proxying {file_id}: {str(e)}")
            write_json_response(self, {"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)

    def handle_drive_thumbnail(self, file_id: str):
        """Serve Drive thumbnails with proper CORS headers."""
        CHUNK = 64 * 1024  # 64KB chunks for thumbnails

        logger.info(f"Thumbnail request for file_id: {file_id}")

        # Get thumbnail link from cached library
        file_data = None
        for file in _drive_cache.get("files", []):
            if file.get("id") == file_id:
                file_data = file
                break

        if not file_data:
            logger.warning(f"File {file_id} not found in cache")
            write_json_response(self, {"error": "File not found in library cache"}, HTTPStatus.NOT_FOUND)
            return

        thumbnail_link = file_data.get("thumbnailLink", "")
        if not thumbnail_link:
            logger.warning(f"No thumbnail link for file {file_id}, generating placeholder")

            # Generate placeholder thumbnail
            file_type = file_data.get('type', 'VID')
            placeholder_png = generate_placeholder_thumbnail(file_type)
            logger.info(f"Generated placeholder thumbnail for file {file_id}, size: {len(placeholder_png)} bytes")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(placeholder_png)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(placeholder_png)
            return

        try:
            # Download thumbnail from Drive
            token = get_google_access_token()
            req = urllib.request.Request(thumbnail_link, headers={"Authorization": f"Bearer {token}"})

            with urllib.request.urlopen(req, timeout=60) as resp:
                content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
                content_length = resp.headers.get("Content-Length", "")

                logger.info(f"Thumbnail content-type: {content_type}, size: {content_length}")

                # Stream the thumbnail with proper CORS headers
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "public, max-age=3600")  # Cache for 1 hour
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET")
                if content_length:
                    self.send_header("Content-Length", content_length)
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
            logger.error(f"HTTPError fetching thumbnail {file_id}: {e.code} - {e.reason}")
            # Return placeholder on HTTP error
            placeholder_png = generate_placeholder_thumbnail("ERROR")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(placeholder_png)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(placeholder_png)
        except urllib.error.URLError as e:
            logger.error(f"URLError fetching thumbnail {file_id}: {e.reason}")
            # Return placeholder on URL error
            placeholder_png = generate_placeholder_thumbnail("URL")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(placeholder_png)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(placeholder_png)
        except TimeoutError as e:
            logger.error(f"Timeout fetching thumbnail {file_id}: {str(e)}")
            # Return placeholder on timeout
            placeholder_png = generate_placeholder_thumbnail("TIMEOUT")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(placeholder_png)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(placeholder_png)
        except Exception as e:
            logger.error(f"Error fetching thumbnail {file_id}: {str(e)}")
            # Return placeholder on any other error
            placeholder_png = generate_placeholder_thumbnail("ERROR")

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(placeholder_png)))
            self.send_header("Cache-Control", "public, max-age=3600")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(placeholder_png)

    def handle_save_config(self):
        try:
            payload = parse_json_body(self)
            saved = save_public_config(payload)
            write_json_response(self, {"publicConfig": saved})
        except json.JSONDecodeError as e:
            write_json_response(self, {"error": f"Invalid JSON: {str(e)}"}, HTTPStatus.BAD_REQUEST)
            return
        except Exception as e:  # noqa: BLE001
            write_json_response(self, {"error": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR)
            return

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

    def handle_ffmpeg_status(self):
        """Handle ffmpeg status check requests."""
        ffmpeg_path = detect_ffmpeg()
        status = {
            "available": ffmpeg_path is not None,
            "path": ffmpeg_path or "",
            "temp_dir": str(TEMP_DIR) if TEMP_DIR else ""
        }
        write_json_response(self, status)

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

        if "payload" not in fields:
            write_json_response(self, {"error": "Falta payload."}, HTTPStatus.BAD_REQUEST)
            return

        try:
            payload = json.loads(fields["payload"])
        except json.JSONDecodeError:
            write_json_response(self, {"error": "Payload de TikTok inválido."}, HTTPStatus.BAD_REQUEST)
            return

        # Determine content type
        content_type_mode = payload.get("contentType", "video").lower()

        # Handle different content types
        if content_type_mode == "video":
            if "file" not in files:
                write_json_response(self, {"error": "Falta archivo de video."}, HTTPStatus.BAD_REQUEST)
                return

            file_info = files["file"]
            mime_type = (file_info.get("content_type") or "").split(";")[0]
            if not mime_type.startswith("video/"):
                write_json_response(
                    self,
                    {"error": "El archivo debe ser un video para el modo video."},
                    HTTPStatus.BAD_REQUEST,
                )
                return

        elif content_type_mode == "image":
            if "file" not in files:
                write_json_response(self, {"error": "Falta archivo de imagen."}, HTTPStatus.BAD_REQUEST)
                return

            file_info = files["file"]
            mime_type = (file_info.get("content_type") or "").split(";")[0]
            if not mime_type.startswith("image/"):
                write_json_response(
                    self,
                    {"error": "El archivo debe ser una imagen para el modo imagen."},
                    HTTPStatus.BAD_REQUEST,
                )
                return

        elif content_type_mode == "carousel":
            # For carousel, we expect multiple files named "file_0", "file_1", etc.
            carousel_files = []
            for i in range(5):  # Maximum 5 images
                file_key = f"file_{i}"
                if file_key in files:
                    file_info = files[file_key]
                    mime_type = (file_info.get("content_type") or "").split(";")[0]
                    if not mime_type.startswith("image/"):
                        write_json_response(
                            self,
                            {"error": f"El archivo {i+1} debe ser una imagen para carrusel."},
                            HTTPStatus.BAD_REQUEST,
                        )
                        return
                    carousel_files.append(file_info)

            if len(carousel_files) < 2:
                write_json_response(
                    self,
                    {"error": "Un carrusel necesita al menos 2 imágenes (máximo 5)."},
                    HTTPStatus.BAD_REQUEST,
                )
                return

        else:
            write_json_response(
                self,
                {"error": f"Tipo de contenido no válido: {content_type_mode}. Debe ser 'video', 'image' o 'carousel'."},
                HTTPStatus.BAD_REQUEST,
            )
            return

        # Music consent is only required for videos
        if content_type_mode == "video" and not bool(payload.get("musicConsent", False)):
            write_json_response(
                self,
                {"error": 'TikTok exige consentimiento explícito para videos. Marcá "Music Usage Confirmation".'},
                HTTPStatus.BAD_REQUEST,
            )
            return

        try:
            token_bundle = ensure_access_token(runtime)

            # Call appropriate upload function based on content type
            if content_type_mode == "video":
                result = upload_video_to_tiktok(runtime, token_bundle, payload, file_info)
            elif content_type_mode == "image":
                result = upload_image_to_tiktok(runtime, token_bundle, payload, file_info)
            elif content_type_mode == "carousel":
                result = upload_carousel_to_tiktok(runtime, token_bundle, payload, carousel_files)
            else:
                raise RuntimeError(f"Tipo de contenido no soportado: {content_type_mode}")

            write_json_response(self, {"ok": True, "result": result})
        except Exception as error:  # noqa: BLE001
            write_json_response(self, {"error": str(error)}, HTTPStatus.BAD_REQUEST)

    def handle_transcode_video(self):
        """Handle video transcoding requests."""
        content_type = self.headers.get("Content-Type", "")
        content_length = int(self.headers.get("Content-Length", "0"))

        if content_length == 0:
            write_json_response(
                self,
                {"error": "No se recibieron datos de video"},
                HTTPStatus.BAD_REQUEST
            )
            return

        try:
            # Read video data
            video_data = self.rfile.read(content_length)
            print(f"[TRANSCODE] Received {len(video_data)} bytes for transcoding")

            # Parse max duration from query parameter (default 30 seconds for preview)
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            max_duration = int(query_params.get("max_duration", ["30"])[0])

            # Transcode video
            print(f"[TRANSCODE] Starting transcoding with max_duration={max_duration}")
            transcoded_data = transcode_video_to_mp4(video_data, max_duration)

            # Send transcoded video back
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", str(len(transcoded_data)))
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(transcoded_data)

            print(f"[TRANSCODE] Successfully transcoded and sent {len(transcoded_data)} bytes")

        except RuntimeError as error:
            print(f"[TRANSCODE] RuntimeError: {error}")
            write_json_response(self, {"error": str(error)}, HTTPStatus.BAD_REQUEST)
        except Exception as error:
            print(f"[TRANSCODE] Unexpected error: {error}")
            write_json_response(self, {"error": f"Error inesperado: {str(error)}"}, HTTPStatus.INTERNAL_SERVER_ERROR)


def main() -> None:
    ensure_files()

    # Cleanup temp directory on exit
    import atexit
    atexit.register(cleanup_temp_dir)

    server = ThreadingHTTPServer((HOST, PORT), BounceHandler)
    print(f"Bounce Drive Media Studio running on http://{HOST}:{PORT}")

    # Check ffmpeg availability on startup
    ffmpeg_path = detect_ffmpeg()
    if ffmpeg_path:
        print(f"[FFMPEG] ffmpeg detected at: {ffmpeg_path}")
    else:
        print("[FFMPEG] WARNING: ffmpeg not detected. Video transcoding will not be available.")

    try:
        server.serve_forever()
    finally:
        cleanup_temp_dir()


if __name__ == "__main__":
    main()
