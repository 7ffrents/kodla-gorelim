"""Kanaldaki videolarin yorumlarini state/comments.json'a ceker (yalniz okur)."""
import json
from pathlib import Path

from googleapiclient.errors import HttpError

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
        try:
            resp = yt.commentThreads().list(
                part="snippet,replies", videoId=vid, maxResults=50, order="time",
                textFormat="plainText", pageToken=token,
            ).execute()
        except HttpError as e:
            # zamanli (henuz yayinlanmamis) videoda yorumlar kapali gorunur; atla, calismayi bozma
            print(f"{vid}: atlandi ({e.resp.status})")
            break
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
                "replyItems": [
                    {
                        "id": r["id"],
                        "author": r["snippet"].get("authorDisplayName", ""),
                        "fromOwner": r["snippet"].get("authorChannelId", {}).get("value") == ch["id"],
                        "text": r["snippet"].get("textDisplay", "")[:400],
                        "publishedAt": r["snippet"].get("publishedAt", ""),
                    }
                    for r in it.get("replies", {}).get("comments", [])
                ],
            })
        token = resp.get("nextPageToken")
        if not token:
            break
    out[vid] = items
    print(f"{vid}: {len(items)} yorum")

(ROOT / "state" / "comments.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
