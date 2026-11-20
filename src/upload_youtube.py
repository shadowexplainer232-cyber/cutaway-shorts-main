"""Upload a finished MP4 to YOUTUBE AS PRIVATE. Publishing public is always done by you in YouTube Studio.

Needs three secrets (see README): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
"""
import os

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CATEGORY_EDUCATION = "27"


def upload_private(mp4_path, episode):
    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
        scopes=SCOPES,
    )
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)

    title = episode["titles"][episode.get("upload_title_index", 0)]
    hashtags = " ".join(episode.get("hashtags", []))
    description = f"{episode['description'].strip()}\n\n{hashtags}".strip()

    body = {
        "snippet": {
            "title": title[:100],
            "description": description,
            "tags": episode.get("tags", []),
            "categoryId": CATEGORY_EDUCATION,
        },
        "status": {
            "privacyStatus": "private",                      # never public from automation
            "containsSyntheticMedia": bool(episode.get("synthetic_media", False)),
        },
    }
    media = MediaFileUpload(str(mp4_path), mimetype="video/mp4", chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        _, resp = req.next_chunk()
    return resp["id"]
