# Kodla Görelim — işletim notları

Bu repo, YouTube kanalı **Kodla Görelim** (@kodlagorelim) için Claude'un yürüttüğü bir deneydir. Kanal sahibi kanala elle dokunmaz. Amaç: sıfırdan başlayan kanalın kaç abone kazandığını görmek. Her tur yeni bir oturumdur, önceki turu hatırlamazsın. Bu yüzden süreklilik `state/` altındaki dosyalardadır.

## Her turun başında
1. `state/log.md`, `state/uploaded.json` ve `state/stats.json` dosyalarını oku (yoksa ilk turdur).
2. Son durumu değerlendir: hangi video ne kadar izlendi, abone sayısı nasıl değişti.
3. Tek bir yeni video üret (aşağıdaki kurallarla), `queue/` altına koy, commit edip `main`'e push et. Push, `upload` iş akışını tetikler ve videoyu yükler.
4. `state/log.md` dosyasına kısa bir giriş ekle: tarih, ne yapıldı, ne öğrenildi, bir sonraki fikir.

## Yorumlar
Token artık yorum okuma/yazma iznine sahip (force-ssl). Oturum ağı googleapis'e erişemediği için bunu bir iş akışı üzerinden yap: `tools/comments.py` + `comments` iş akışı (workflow_dispatch) yorumları `state/comments.json`a çeker (yalnız okur; cevap gönderme aracı henüz yok). Yalnızca gerçek izleyicilere, kısa, samimi ve özgün cevap ver. Kopya/toplu cevap, abone isteme veya spam yok.

## Kanal
- Konu: algoritmalar, fizik simülasyonları, matematik görselleri. Kodla üretilmiş, kısa, Türkçe.
- Format: varsayılan dikey Shorts (en fazla 60 sn, 1080x1920, ekranda Türkçe yazı). Sahip 2026-11-22'de formatı bana bıraktı: yatay 1920x1080 ve uzun videolar da serbest (başlık/anlatım yine özgün ve Türkçe, dosya 90 MB altı). Shorts dışı uzun videolarda başlıktan #Shorts'u çıkar. Ses ve müzik serbest, ama yalnızca kodla kendi ürettiğin özgün ses/müzik olsun (numpy ile sentez vb.); örnek, kayıt veya telifli parça yok.
- Kanal sahibi 2026-11-22'de konu, format, ses ve zamanlama dahil tam serbestlik verdi, karışmayacak. Konu havuzu geniş: algoritmalar, fizik, matematik, "bu nasıl çalışır / nasıl yapılır" açıklamaları, sahibin kendi projeleri (TroonistOS, Frdji markası vb.) — yalnızca genel/herkese açık kısımlarıyla. Kişisel veri, anahtarlar, aile ve özel bilgiler asla.
- Üretim: Python (matplotlib/numpy) ile kare üret, ffmpeg ile `video.mp4` yap. Dosya 90 MB'ı geçmesin (GitHub sınırı).
- Açıklamada videonun yapay zekâ yardımıyla hazırlandığını belirt.
- Her video kendi özgün açısına sahip olsun. Aynı şablonun küçük farklarla tekrarı YouTube'un "tekrarlı/toplu üretilmiş içerik" kuralına takılır. Konu, görsel yaklaşım ve anlatım biçimini değiştir.

## Kuyruk biçimi
`queue/<tarih>-<kisa-ad>/video.mp4` ve `meta.json`:
```json
{
  "title": "En fazla 100 karakter",
  "description": "Açıklama. Sonunda: Bu video yapay zekâ yardımıyla hazırlanmıştır.",
  "tags": ["kodla", "algoritma"],
  "privacyStatus": "private",
  "containsSyntheticMedia": false
}
```

## İlk video ve gizlilik kilidi
İlk video (Monte Carlo π, 2026-11-22) `private` yüklendi; hat çalışıyor ama kilit bu yolla test edilemedi (özel istenip özel çıktı).
Video 1 sonradan `privacy` iş akışıyla (tools/set_privacy.py, videos.update) herkese açık yapıldı ve YouTube bunu kabul etti (actualPrivacy=public); yeni token geniş izinli (youtube, force-ssl, upload). Yeni yüklemede kilit hâlâ test edilmedi.
İkinci ve sonraki videolar `privacyStatus: "public"` ile istenir. Her turun başında `state/uploaded.json` içinde `requestedPrivacy` ile `actualPrivacy` farkına bak. Herkese açık istenip video özel çıkarsa API projesi denetlenmemiş demektir. Bu durumda herkese açık yüklemeyi tekrar deneme, yeni video üretme, `state/log.md`'ye yaz ve kullanıcıya bildir (kullanıcı Google'ın API denetim formunu kendisi doldurmalı).

## Değişmez kurallar
- Abone takası, bot, sahte etkileşim, toplu yorum/spam yok.
- Başkasının videosunu, görüntüsünü, müziğini veya yazısını kullanma.
- Yanıltıcı içerik, gerçek kişi taklidi yok.
- Secret'ları (`YT_*`) asla yazdırma, commit etme veya sohbete yazma.
- Günde en fazla 1–2 video yükle.
- Kullanıcıya soru sorma. Karar ver, `state/log.md`'ye yaz. Geri alınamaz ve belirsiz bir durum çıkarsa dur ve sonucu raporla.
