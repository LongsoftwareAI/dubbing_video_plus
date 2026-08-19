"""
YouTube, Douyin, TikTok, Bilibili & Web Video Downloader Service.
Supports unshortening links (v.douyin.com, vt.tiktok.com, b23.tv), custom headers,
cookie authentication, and fallback extraction.
"""
import os
import json
import glob
import time
import re
import urllib.request
import logging
from test_mini_tool.config import DOWNLOADS_DIR, CACHE_DIR, FFMPEG_PATH

logger = logging.getLogger("mini_dubber.youtube")

# Player clients to escalate through on 403
_YT_PLAYER_CLIENTS = ["android", "ios", "web_safari", "mweb"]
_YT_DOWNLOAD_RETRIES = 3


def _resolve_short_url(url: str) -> str:
    """Unshortens redirect links (e.g., v.douyin.com, vt.tiktok.com, b23.tv, bit.ly)."""
    url = url.strip()
    if any(domain in url for domain in ("v.douyin.com", "vt.tiktok.com", "vm.tiktok.com", "b23.tv", "youtu.be", "shorturl")):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            })
            with urllib.request.urlopen(req, timeout=10) as response:
                resolved = response.geturl()
                logger.info(f"Unshortened URL: {url} -> {resolved}")
                return resolved
        except Exception as e:
            logger.warning(f"URL unshortening failed for {url}: {e}")
    return url


def _is_forbidden_download_error(exc: BaseException) -> bool:
    s = str(exc)
    if "403" in s or "Forbidden" in s:
        return True
    low = s.lower()
    return "drm protected" in low or "drm-protected" in low


def _is_transient_download_error(exc: BaseException) -> bool:
    s = str(exc).lower()
    for kw in ("broken pipe", "connection reset", "timed out", "timeout",
               "urlopen error", "incomplete read", "did not get any data"):
        if kw in s:
            return True
    return False


def _is_bot_detection_error(exc: BaseException) -> bool:
    s = str(exc)
    return "Sign in to confirm" in s or "confirm you're not a bot" in s.lower()


def _cleanup_partial_download(output_dir: str) -> None:
    for pattern in ("*.part*", "*.ytdl", "original.*"):
        for stale in glob.glob(os.path.join(output_dir, pattern)):
            try:
                os.remove(stale)
            except OSError:
                pass


def _ensure_netscape_cookie_file(cookie_file_path: str) -> str:
    """Convert Cookie-Editor JSON export to Netscape cookies.txt if needed."""
    if not cookie_file_path or not os.path.exists(cookie_file_path):
        return cookie_file_path
    try:
        with open(cookie_file_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content.startswith("[") and content.endswith("]"):
            cookies_json = json.loads(content)
            netscape_path = os.path.join(CACHE_DIR, "converted_cookies.txt")
            lines = [
                "# Netscape HTTP Cookie File",
                "# http://curl.haxx.se/rfc/cookie_spec.html",
                "# This is a generated file! Do not edit.",
                "",
            ]
            for c in cookies_json:
                domain = c.get("domain", ".youtube.com")
                include_sub = "TRUE" if domain.startswith(".") else "FALSE"
                path = c.get("path", "/")
                secure = "TRUE" if c.get("secure", False) else "FALSE"
                expiration = int(c.get("expirationDate", c.get("expiry", 2147483647)))
                name = c.get("name", "")
                value = c.get("value", "")
                if name:
                    lines.append(f"{domain}\t{include_sub}\t{path}\t{secure}\t{expiration}\t{name}\t{value}")
            with open(netscape_path, "w", encoding="utf-8") as f_out:
                f_out.write("\n".join(lines) + "\n")
            logger.info("Converted Cookie-Editor JSON -> Netscape: %s", netscape_path)
            return netscape_path
    except Exception as e:
        logger.warning("Cookie conversion skipped: %s", e)
    return cookie_file_path


def _build_base_opts(output_dir: str, is_douyin: bool = False) -> dict:
    """Build the base yt-dlp options dict for YouTube, Douyin, Bilibili, TikTok."""
    import shutil
    outtmpl = os.path.join(output_dir, "%(id)s.%(ext)s")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }
    if is_douyin:
        headers["Referer"] = "https://www.douyin.com/"

    # Exact format cascade from OmniVoice backend/services/dub_pipeline.py
    # Prefers H.264/AAC for clean direct decodability, falls back seamlessly to any combination
    opts: dict = {
        "outtmpl": outtmpl,
        "format": (
            "bv*[vcodec^=avc1][ext=mp4]+ba[acodec^=mp4a][ext=m4a]/"
            "bv*[vcodec^=avc1]+ba[acodec^=mp4a]/"
            "b[vcodec^=avc1][acodec^=mp4a]/"
            "bv*[vcodec^=avc1]+ba/"
            "b[vcodec^=avc1]/"
            "bv*+ba/b"
        ),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "restrictfilenames": True,
        "updatetime": False,
        "socket_timeout": 30,
        "fragment_retries": 10,
        "retries": 10,
        "extractor_retries": 5,
        "skip_unavailable_fragments": True,
        "http_headers": headers,
    }
    if FFMPEG_PATH and os.path.exists(FFMPEG_PATH):
        opts["ffmpeg_location"] = FFMPEG_PATH

    available_runtimes = []
    for rt in ("deno", "node", "bun"):
        if shutil.which(rt):
            available_runtimes.append(rt)

    yt_extractor_args = {
        "player_client": ["android", "web"]
    }
    if available_runtimes:
        yt_extractor_args["js_runtimes"] = available_runtimes

    opts["extractor_args"] = {"youtube": yt_extractor_args}
    return opts


def _try_download(url: str, ydl_opts: dict, output_dir: str) -> str:
    """Attempt download with retry loop (403 escalation + transient retries)."""
    import yt_dlp

    info = None
    path = None
    transient_used = 0
    client_idx = 0
    opts = dict(ydl_opts)

    while True:
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                path = ydl.prepare_filename(info)
            break
        except Exception as exc:
            _cleanup_partial_download(output_dir)

            if _is_forbidden_download_error(exc) and client_idx < len(_YT_PLAYER_CLIENTS):
                client = _YT_PLAYER_CLIENTS[client_idx]
                client_idx += 1
                # Safely update player_client without losing js_runtimes
                yt_args = dict(opts.get("extractor_args", {}).get("youtube", {}))
                yt_args["player_client"] = [client]
                opts["extractor_args"] = {**opts.get("extractor_args", {}), "youtube": yt_args}
                logger.warning("Download 403 — retrying with player_client=%s", client)
                continue

            if (transient_used < _YT_DOWNLOAD_RETRIES
                    and _is_transient_download_error(exc)
                    and not _is_forbidden_download_error(exc)):
                transient_used += 1
                logger.warning("Transient failure (attempt %d/%d) — retrying", transient_used, _YT_DOWNLOAD_RETRIES)
                time.sleep(2 * transient_used)
                continue

            raise

    # Resolve final mp4 path
    root, _ = os.path.splitext(path)
    mp4 = root + ".mp4"
    if os.path.exists(mp4):
        return mp4
    if os.path.exists(path):
        return path

    for f in sorted(os.listdir(output_dir), key=lambda x: os.path.getmtime(os.path.join(output_dir, x)), reverse=True):
        if f.endswith(".mp4"):
            return os.path.join(output_dir, f)

    raise RuntimeError(f"Download completed but no output file found in {output_dir}")


def download_youtube_video(url: str, output_dir: str = None, cookie_file: str = None) -> str:
    """
    Downloads video from YouTube, Douyin, TikTok, Bilibili, or web link.
    Supports short-url redirects (v.douyin.com, vt.tiktok.com, b23.tv).
    Returns the absolute path to the downloaded .mp4 file.
    """
    if not url or not url.strip().startswith("http"):
        raise ValueError("URL không hợp lệ. Vui lòng nhập đường dẫn HTTP/HTTPS.")

    # 1. Unshorten URL if needed (Douyin v.douyin.com / TikTok vt.tiktok.com)
    resolved_url = _resolve_short_url(url)
    is_douyin = "douyin.com" in resolved_url

    if output_dir is None:
        output_dir = DOWNLOADS_DIR
    os.makedirs(output_dir, exist_ok=True)

    base_opts = _build_base_opts(output_dir, is_douyin=is_douyin)

    # Resolve cookie file path
    raw_cookie = cookie_file or os.environ.get("YOUTUBE_COOKIE_FILE", "")
    effective_cookie = _ensure_netscape_cookie_file(raw_cookie)
    has_cookie = bool(effective_cookie and os.path.exists(effective_cookie))

    if has_cookie:
        base_opts["cookiefile"] = effective_cookie

    logger.info(f"Downloading web video from: {resolved_url}")
    try:
        return _try_download(resolved_url, base_opts, output_dir)
    except Exception as exc1:
        clean1 = re.sub(r'\x1b\[[0-9;]*m', '', str(exc1))
        logger.warning("Attempt 1 failed: %s", clean1[:200])

        if _is_bot_detection_error(exc1) and has_cookie:
            logger.info("Attempt 2: with cookies")
            opts_with_cookie = dict(base_opts)
            opts_with_cookie["cookiefile"] = effective_cookie
            try:
                return _try_download(resolved_url, opts_with_cookie, output_dir)
            except Exception as exc2:
                clean2 = re.sub(r'\x1b\[[0-9;]*m', '', str(exc2))
                raise RuntimeError(f"Không thể tải video tu URL: {resolved_url}\nChi tiết: {clean2}") from exc2

        raise RuntimeError(f"Không thể tải video từ URL: {resolved_url}\nChi tiết: {clean1}") from exc1
