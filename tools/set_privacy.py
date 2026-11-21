"""Bir videonun gorunurlugunu degistirir (VIDEO_ID, PRIVACY ortam degiskenleri)."""
import json
import os
import sys
from pathlib import Path

from ytcommon import build_service, verified_channel

VIDEO_ID = os.environ["VIDEO_ID"].strip()
PRIVACY = os.environ["PRIVACY"].strip()
if PRIVACY not in ("public", "unlisted", "private"):
    sys.exit(f"Gecersiz gorunurluk: {PRIVACY}")

yt = build_service()
verified_channel(yt)

resp = yt.videos().list(part="status,snippet", id=VIDEO_ID).execute()
items = resp.get("items", [])
if not items:
    sys.exit("HATA: Video bu kanalda bulunamadi.")
status = items[0]["status"]
print(f"Onceki gorunurluk: {status['privacyStatus']}")
status["privacyStatus"] = PRIVACY
yt.videos().update(part="status", body={"id": VIDEO_ID, "status": status}).execute()

after = yt.videos().list(part="status", id=VIDEO_ID).execute()["items"][0]["status"]["privacyStatus"]
print(f"Yeni gorunurluk: {after}")

up = Path(__file__).resolve().parent.parent / "state" / "uploaded.json"
if up.exists():
    data = json.loads(up.read_text(encoding="utf-8"))
    for rec in data.values():
        if rec.get("videoId") == VIDEO_ID:
            rec["actualPrivacy"] = after
    up.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
if after != PRIVACY:
    sys.exit(f"UYARI: {PRIVACY} istendi ama {after} kaldi (API denetimi kilidi olabilir).")
