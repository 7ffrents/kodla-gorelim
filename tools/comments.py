"""Kanaldaki videolarin yorumlarini state/comments.json'a ceker (yalniz okur)."""
import json
from pathlib import Path

from ytcommon import build_service, verified_channel

ROOT = Path(__file__).resolve().parent.parent
yt = build_service()
ch = verified_channel(yt)

up = json.loads((ROOT / "state" / "uploaded.json").read_text(encoding="utf-8"))
out = {}
for slug, rec in up.items():
    vid = rec["videoId"]
    items = []
    token = None
    while True:
        resp = yt.commentThreads().list(
            part="snippet", videoId=vid, maxResults=50, order="time",
            textFormat="plainText", pageToken=token,
        ).execute()
        for it in resp.get("items", []):
            top = it["snippet"]["topLevelComment"]
            sn = top["snippet"]
            items.append({
                "id": top["id"],
                "author": sn.get("authorDisplayName", ""),
                "fromOwner": sn.get("authorChannelId", {}).get("value") == ch["id"],
                "text": sn.get("textDisplay", "")[:400],
                "publishedAt": sn.get("publishedAt", ""),
                "likes": sn.get("likeCount", 0),
                "replies": it["snippet"].get("totalReplyCount", 0),
            })
        token = resp.get("nextPageToken")
        if not token:
            break
    out[vid] = items
    print(f"{vid}: {len(items)} yorum")

(ROOT / "state" / "comments.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
