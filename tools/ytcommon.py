"""Ortak YouTube yardimcilari: kimlik, kanal dogrulama."""
import os
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

EXPECTED_CHANNEL = "Kodla Görelim"


def build_service():
    creds = Credentials(
        None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def verified_channel(yt):
    """Token'in bagli oldugu kanali dondurur. Beklenen kanal degilse durur."""
    resp = yt.channels().list(part="snippet,statistics", mine=True).execute()
    items = resp.get("items", [])
    if not items:
        sys.exit("HATA: Token'a bagli kanal bulunamadi.")
    ch = items[0]
    title = ch["snippet"]["title"]
    print(f"Token'in bagli oldugu kanal: {title} ({ch['id']})")
    if title != EXPECTED_CHANNEL:
        sys.exit(
            f"DURDU: Beklenen kanal '{EXPECTED_CHANNEL}', ama token '{title}' kanalina bagli. "
            "Hicbir sey yuklenmedi. Token'i yeniden uretirken kanal secim ekraninda "
            f"'{EXPECTED_CHANNEL}' secilmeli."
        )
    return ch
