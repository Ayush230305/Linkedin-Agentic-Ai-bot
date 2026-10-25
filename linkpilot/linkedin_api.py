import os
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

# Load environment variables from .env beside this file.
load_dotenv(override=True)

API = "https://api.linkedin.com/rest"

IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif"}
VIDEO_EXT = {".mp4"}


class LinkedInDefiniteError(RuntimeError):
    """The request was rejected or failed before publishing was attempted."""


class LinkedInUnknownError(RuntimeError):
    """The publishing result is uncertain. Check LinkedIn before retrying."""


def escape_commentary(text: str) -> str:
    """Escape special characters in LinkedIn post commentary."""
    return re.sub(r"([(){}\[\]<>@|\\~_*])", r"\\\1", text)


def _config():
    token = os.getenv("LINKEDIN_ACCESS_TOKEN", "").strip()
    author = os.getenv("LINKEDIN_MEMBER_URN", "").strip()
    version = os.getenv("LINKEDIN_VERSION", "").strip()

    missing = [
        name
        for name, value in (
            ("LINKEDIN_ACCESS_TOKEN", token),
            ("LINKEDIN_MEMBER_URN", author),
            ("LINKEDIN_VERSION", version),
        )
        if not value
    ]

    if missing:
        raise LinkedInDefiniteError(
            "Missing in .env: " + ", ".join(missing)
        )

    if not re.fullmatch(r"\d{6}", version):
        raise LinkedInDefiniteError(
            "LINKEDIN_VERSION must use YYYYMM format, for example 202610. "
            "Use a version currently supported by your LinkedIn API access."
        )

    if not author.startswith("urn:li:person:"):
        raise LinkedInDefiniteError(
            "LINKEDIN_MEMBER_URN must start with urn:li:person:"
        )

    return token, author, version


def _headers(token, version):
    return {
        "Authorization": f"Bearer {token}",
        "Linkedin-Version": version,
        "X-Restli-Protocol-Version": "2.0.0",
        "Content-Type": "application/json",
    }


def _call(method, url, **kwargs):
    """Make a LinkedIn API request before the final publishing request."""
    timeout = kwargs.pop("timeout", 60)

    try:
        response = requests.request(
            method,
            url,
            timeout=timeout,
            **kwargs,
        )
    except requests.RequestException as exc:
        raise LinkedInDefiniteError(
            f"Network error during preparation: {exc}"
        ) from exc

    if response.status_code == 401:
        raise LinkedInDefiniteError(
            "LinkedIn returned 401 Unauthorized. Renew the access token."
        )

    if not 200 <= response.status_code < 300:
        raise LinkedInDefiniteError(
            f"LinkedIn API error {response.status_code}: "
            f"{response.text[:500]}"
        )

    return response


def upload_image(path, token, author, version):
    """Upload one image and return its LinkedIn image URN."""
    path = Path(path)

    if not path.is_file():
        raise LinkedInDefiniteError(f"Image file not found: {path}")

    response = _call(
        "POST",
        f"{API}/images?action=initializeUpload",
        headers=_headers(token, version),
        json={
            "initializeUploadRequest": {
                "owner": author,
            }
        },
    )

    try:
        value = response.json()["value"]
        upload_url = value["uploadUrl"]
        image_urn = value["image"]
    except (ValueError, KeyError, TypeError) as exc:
        raise LinkedInDefiniteError(
            "Unexpected image upload initialization response."
        ) from exc

    try:
        with path.open("rb") as file:
            upload_response = requests.put(
                upload_url,
                data=file,
                headers={"Authorization": f"Bearer {token}"},
                timeout=180,
            )
    except requests.RequestException as exc:
        raise LinkedInDefiniteError(
            f"Image upload failed: {exc}"
        ) from exc

    if not 200 <= upload_response.status_code < 300:
        raise LinkedInDefiniteError(
            f"Image upload failed ({upload_response.status_code}): "
            f"{upload_response.text[:300]}"
        )

    return image_urn


def upload_video(path, token, author, version):
    """Upload a video using LinkedIn's multipart upload instructions."""
    path = Path(path)

    if not path.is_file():
        raise LinkedInDefiniteError(f"Video file not found: {path}")

    headers = _headers(token, version)
    size = path.stat().st_size

    response = _call(
        "POST",
        f"{API}/videos?action=initializeUpload",
        headers=headers,
        json={
            "initializeUploadRequest": {
                "owner": author,
                "fileSizeBytes": size,
                "uploadCaptions": False,
                "uploadThumbnail": False,
            }
        },
    )

    try:
        value = response.json()["value"]
        video_urn = value["video"]
        instructions = value["uploadInstructions"]
    except (ValueError, KeyError, TypeError) as exc:
        raise LinkedInDefiniteError(
            "Unexpected video upload initialization response."
        ) from exc

    uploaded_parts = []

    try:
        with path.open("rb") as file:
            for part in instructions:
                first = part["firstByte"]
                last = part["lastByte"]
                upload_url = part["uploadUrl"]

                file.seek(first)
                chunk = file.read(last - first + 1)

                if len(chunk) != last - first + 1:
                    raise LinkedInDefiniteError(
                        "Could not read the complete video upload part."
                    )

                try:
                    result = requests.put(
                        upload_url,
                        data=chunk,
                        headers={
                            "Content-Type": "application/octet-stream"
                        },
                        timeout=300,
                    )
                except requests.RequestException as exc:
                    raise LinkedInDefiniteError(
                        f"Video part upload failed: {exc}"
                    ) from exc

                if not 200 <= result.status_code < 300:
                    raise LinkedInDefiniteError(
                        f"Video part upload failed ({result.status_code}): "
                        f"{result.text[:300]}"
                    )

                etag = result.headers.get("ETag", "").strip('"')

                if not etag:
                    raise LinkedInDefiniteError(
                        "Video upload returned no ETag for a part."
                    )

                uploaded_parts.append(etag)

    except (KeyError, TypeError) as exc:
        raise LinkedInDefiniteError(
            "Invalid video upload instructions from LinkedIn."
        ) from exc

    _call(
        "POST",
        f"{API}/videos?action=finalizeUpload",
        headers=headers,
        json={
            "finalizeUploadRequest": {
                "video": video_urn,
                "uploadToken": value.get("uploadToken", ""),
                "uploadedPartIds": uploaded_parts,
            }
        },
    )

    # Wait briefly for video processing.
    status_url = f"{API}/videos/{quote(video_urn, safe='')}"

    for _ in range(30):
        status_response = _call(
            "GET",
            status_url,
            headers=headers,
        )

        try:
            status = status_response.json().get("status")
        except ValueError as exc:
            raise LinkedInDefiniteError(
                "Invalid video status response."
            ) from exc

        if status == "AVAILABLE":
            return video_urn

        if status == "PROCESSING_FAILED":
            raise LinkedInDefiniteError(
                "LinkedIn failed to process the uploaded video."
            )

        time.sleep(2)

    raise LinkedInDefiniteError(
        "Video is still processing. Check its status before publishing."
    )


def _build_media(media_paths, token, author, version):
    """Build the media section of a LinkedIn post payload."""
    if not media_paths:
        return None

    paths = [Path(p) for p in media_paths]
    extensions = [p.suffix.lower() for p in paths]

    unsupported = [
        str(path)
        for path, ext in zip(paths, extensions)
        if ext not in IMAGE_EXT | VIDEO_EXT
    ]

    if unsupported:
        raise LinkedInDefiniteError(
            "Unsupported media file type: " + ", ".join(unsupported)
        )

    videos = [
        path for path, ext in zip(paths, extensions)
        if ext in VIDEO_EXT
    ]
    images = [
        path for path, ext in zip(paths, extensions)
        if ext in IMAGE_EXT
    ]

    if videos and (images or len(videos) > 1):
        raise LinkedInDefiniteError(
            "A post can contain one video or images, not both."
        )

    if videos:
        video_urn = upload_video(
            videos[0], token, author, version
        )
        return {"media": {"id": video_urn}}

    if len(images) > 20:
        raise LinkedInDefiniteError(
            "A maximum of 20 images is allowed by this implementation."
        )

    image_urns = [
        upload_image(path, token, author, version)
        for path in images
    ]

    if len(image_urns) == 1:
        return {"media": {"id": image_urns[0]}}

    if len(image_urns) > 1:
        return {
            "multiImage": {
                "images": [
                    {"id": image_urn}
                    for image_urn in image_urns
                ]
            }
        }

    return None


def publish_post(text: str, media_paths=None) -> str:
    """
    Publish a public LinkedIn post.

    Args:
        text: Text of the post.
        media_paths: Optional list of image/video file paths.

    Returns:
        LinkedIn post ID from the x-restli-id response header.

    Warning:
        If a network error or server error occurs during the final publish
        request, the post might already exist. Check LinkedIn before retrying.
    """
    text = text.strip()

    if not text:
        raise LinkedInDefiniteError("Post text cannot be empty.")

    token, author, version = _config()

    # Uploading media happens before the final post request.
    content = _build_media(
        media_paths or [],
        token,
        author,
        version,
    )

    payload = {
        "author": author,
        "commentary": escape_commentary(text),
        "visibility": "PUBLIC",
        "distribution": {
            "feedDistribution": "MAIN_FEED",
            "targetEntities": [],
            "thirdPartyDistributionChannels": [],
        },
        "lifecycleState": "PUBLISHED",
        "isReshareDisabledByAuthor": False,
    }

    if content:
        payload["content"] = content

    url = f"{API}/posts"

    # Diagnostic output; never print the token.
    print("LinkedIn API URL:", url)
    print("LinkedIn API version:", repr(version))

    try:
        response = requests.post(
            url,
            headers=_headers(token, version),
            json=payload,
            timeout=30,
        )
    except requests.RequestException as exc:
        raise LinkedInUnknownError(
            "The publish request had a network error. "
            "The post may have been created; check LinkedIn before retrying."
        ) from exc

    if response.status_code == 201:
        post_id = response.headers.get("x-restli-id")

        if not post_id:
            raise LinkedInUnknownError(
                "LinkedIn reported success but returned no post ID. "
                "Check your LinkedIn profile before retrying."
            )

        print("LinkedIn post published successfully.")
        return post_id

    if response.status_code == 401:
        raise LinkedInDefiniteError(
            "LinkedIn returned 401 Unauthorized. Renew the access token."
        )

    if response.status_code >= 500:
        raise LinkedInUnknownError(
            f"LinkedIn returned server error {response.status_code}. "
            "Check your LinkedIn profile before retrying."
        )

    raise LinkedInDefiniteError(
        f"LinkedIn API error {response.status_code}: "
        f"{response.text[:500]}"
    )
