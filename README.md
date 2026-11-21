# Kodla Görelim

YouTube kanalı **Kodla Görelim** (@kodlagorelim) için otomasyon deposu.

- `queue/`: yüklenecek videolar. Her klasörde `video.mp4` ve `meta.json` bulunur. `queue/` altına yapılan her push, `upload` iş akışını çalıştırır.
- `state/`: yükleme kayıtları (`uploaded.json`), kanal istatistikleri (`stats.json`, `stats_history.csv`) ve günlük (`log.md`).
- `tools/`: yükleme ve istatistik betikleri.
- `.github/workflows/`: `upload` (queue değişince) ve `stats` (her gün) iş akışları.
- `index.html`, `privacy.html`: GitHub Pages ile yayınlanan ana sayfa ve gizlilik politikası.
- `CLAUDE.md`: Claude'un her turda izlediği işletim notları.

## Gerekli secret'lar
Settings > Secrets and variables > Actions altında: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`.

İş akışı her çalıştığında token'ın bağlı olduğu kanalı doğrular. Kanal "Kodla Görelim" değilse hiçbir şey yüklemeden durur.
