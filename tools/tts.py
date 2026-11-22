"""Turkce TTS: CC0 piper sesleri (fettah, fahrettin). Kullanim:
   python tts.py "metin" cikti.wav [fettah|fahrettin]
On kosul: pip install piper-tts. Model yoksa GitHub releases'ten indirilir (~67 MB, /tmp/tts).
NOT: dfki sesi CC BY-NC-SA (ticari yasak) -> KULLANMA."""
import subprocess
import sys
from pathlib import Path

CACHE = Path("/tmp/tts")
BASE = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/"


def synth(text, out_wav, voice="fettah"):
    if voice not in ("fettah", "fahrettin"):
        raise SystemExit("Yalniz CC0 sesler: fettah, fahrettin")
    name = f"vits-piper-tr_TR-{voice}-medium"
    model = CACHE / name / f"tr_TR-{voice}-medium.onnx"
    if not model.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        tar = CACHE / f"{name}.tar.bz2"
        subprocess.run(["curl", "-sL", "-o", str(tar), f"{BASE}{name}.tar.bz2"], check=True)
        subprocess.run(["tar", "xjf", str(tar), "-C", str(CACHE)], check=True)
    subprocess.run(
        [sys.executable, "-m", "piper", "-m", str(model), "-f", str(out_wav)],
        input=text.encode("utf-8"), check=True,
    )


if __name__ == "__main__":
    synth(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "fettah")
