"""Yorum yazar. Ortam: VIDEO_ID, TEXT, istege bagli PARENT_ID (cevap icin).
PARENT_ID yoksa videoya ust duzey yorum, varsa o yoruma cevap yazar.
Yalnizca kanal sahibi hesabindan, kisa ve ozgun metinlerle kullan."""
import os
import sys

from ytcommon import build_service, verified_channel

text = os.environ["TEXT"].strip()
if not text or len(text) > 9000:
    sys.exit("Gecersiz metin uzunlugu")
yt = build_service()
verified_channel(yt)
parent = os.environ.get("PARENT_ID", "").strip()
if parent:
    r = yt.comments().insert(part="snippet", body={"snippet": {"parentId": parent, "textOriginal": text}}).execute()
    print("Cevap yazildi:", r["id"])
else:
    vid = os.environ["VIDEO_ID"].strip()
    r = yt.commentThreads().insert(part="snippet", body={"snippet": {
        "videoId": vid, "topLevelComment": {"snippet": {"textOriginal": text}}}}).execute()
    print("Yorum yazildi:", r["id"])
