"""queue/ altindaki videolari yukler, sonucu state/uploaded.json'a yazar.

Her kuyruk ogesi: queue/<slug>/video.mp4 + queue/<slug>/meta.json
meta.json alanlari:
  title (zorunlu, en fazla 100 karakter)
  description (zorunlu)
  tags (liste, istege bagli)
  privacyStatus ("private" | "unlisted" | "public", varsayilan "private")
  containsSyntheticMedia (bool, varsayilan false)
"""
import json
import pathlib
import sys
from datetime import datetime, timezone

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from ytcommon import build_service, verified_channel

ROOT = pathlib.Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
STATE = ROOT / "state" / "uploaded.json"


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_state(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def upload_one(yt, slug, folder):
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    title = meta["title"][:100]
    requested = meta.get("privacyStatus", "private")
    publish_at = meta.get("publishAt")
    scheduled = False
    if publish_at:
        t = datetime.fromisoformat(publish_at.replace("Z", "+00:00"))
        if t > datetime.now(timezone.utc) and requested == "public":
            scheduled = True
    body = {
        "snippet": {
            "title": title,
            "description": meta["description"],
            "tags": meta.get("tags", []),
            "categoryId": "27",  # Egitim
            "defaultLanguage": "tr",
        },
        "status": {
            "privacyStatus": "private" if scheduled else requested,
            "selfDeclaredMadeForKids": False,
            "containsSyntheticMedia": bool(meta.get("containsSyntheticMedia", False)),
        },
    }
    if scheduled:
        body["status"]["publishAt"] = publish_at.replace("+00:00", "Z")
    media = MediaFileUpload(str(folder / "video.mp4"), chunksize=-1, resumable=True, mimetype="video/mp4")
    request = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]
    actual = response.get("status", {}).get("privacyStatus", "?")
    print(f"Yuklendi: {slug} -> https://youtu.be/{video_id} (istenen={requested}, gercek={actual})")
    if scheduled:
        print(f"Zamanli: YouTube {publish_at} aninda herkese acacak (simdilik ozel).")
    elif actual != requested:
        print(
            f"UYARI: Istenen gizlilik '{requested}' ama video '{actual}' olarak olustu. "
            "API projesi dogrulanmamis olabilir (2020 sonrasi projelerde videolar ozel kilitlenir)."
        )
    return {
        "videoId": video_id,
        "title": title,
        "requestedPrivacy": requested,
        "actualPrivacy": actual,
        **({"scheduledPublishAt": publish_at} if scheduled else {}),
        "uploadedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main():
    state = load_state()
    pending = sorted(
        p for p in QUEUE.glob("*") if p.is_dir() and (p / "video.mp4").exists() and p.name not in state
    )
    now = datetime.now(timezone.utc)
    ready = []
    for p in pending:
        nb = json.loads((p / "meta.json").read_text(encoding="utf-8")).get("notBefore")
        if nb and now < datetime.fromisoformat(nb.replace("Z", "+00:00")):
            print(f"Bekliyor ({p.name}): {nb} oncesi yuklenmez.")
            continue
        ready.append(p)
    pending = ready
    if not pending:
        print("Yuklenecek yeni video yok.")
        return
    yt = build_service()
    verified_channel(yt)
    failed = False
    for folder in pending:
        try:
            state[folder.name] = upload_one(yt, folder.name, folder)
            save_state(state)  # her basarili yuklemeden sonra kaydet
        except HttpError as e:
            failed = True
            print(f"HATA ({folder.name}): {e}")
            if e.resp.status in (403, 429) and b"quota" in e.content.lower():
                print("Gunluk API kotasi doldu, kalanlar yarin yuklenecek.")
                break
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
