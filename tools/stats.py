"""Kanal ve video istatistiklerini state/ altina yazar."""
import csv
import json
import pathlib
from datetime import datetime, timezone

from ytcommon import build_service, verified_channel

ROOT = pathlib.Path(__file__).resolve().parent.parent
STATE_DIR = ROOT / "state"


def main():
    STATE_DIR.mkdir(exist_ok=True)
    yt = build_service()
    ch = verified_channel(yt)
    st = ch["statistics"]
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    uploaded_path = STATE_DIR / "uploaded.json"
    uploaded = json.loads(uploaded_path.read_text(encoding="utf-8")) if uploaded_path.exists() else {}
    ids = [v["videoId"] for v in uploaded.values()]
    videos = []
    for i in range(0, len(ids), 50):
        resp = yt.videos().list(part="statistics,status", id=",".join(ids[i : i + 50])).execute()
        for it in resp.get("items", []):
            s = it.get("statistics", {})
            videos.append(
                {
                    "videoId": it["id"],
                    "privacy": it["status"]["privacyStatus"],
                    "views": int(s.get("viewCount", 0)),
                    "likes": int(s.get("likeCount", 0)),
                    "comments": int(s.get("commentCount", 0)),
                }
            )

    snapshot = {
        "at": now,
        "channel": ch["snippet"]["title"],
        "subscribers": int(st.get("subscriberCount", 0)),
        "subscribersHidden": bool(st.get("hiddenSubscriberCount", False)),
        "views": int(st.get("viewCount", 0)),
        "videos": int(st.get("videoCount", 0)),
        "perVideo": videos,
    }
    (STATE_DIR / "stats.json").write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    hist = STATE_DIR / "stats_history.csv"
    new = not hist.exists()
    with hist.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["at", "subscribers", "views", "videos"])
        w.writerow([now, snapshot["subscribers"], snapshot["views"], snapshot["videos"]])
    print(f"Abone: {snapshot['subscribers']} | Izlenme: {snapshot['views']} | Video: {snapshot['videos']}")


if __name__ == "__main__":
    main()
