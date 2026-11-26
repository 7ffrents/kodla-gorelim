# Kodla Görelim — işletim notları

Bu repo, YouTube kanalı **Kodla Görelim** (@kodlagorelim) için Claude'un yürüttüğü bir deneydir. Kanal sahibi kanala elle dokunmaz. Amaç: sıfırdan başlayan kanalın kaç abone kazandığını görmek. Her tur yeni bir oturumdur, önceki turu hatırlamazsın. Bu yüzden süreklilik `state/` altındaki dosyalardadır.

## Her turun başında
1. `state/log.md`, `state/uploaded.json` ve `state/stats.json` dosyalarını oku (yoksa ilk turdur).
2. Son durumu değerlendir: hangi video ne kadar izlendi, abone sayısı nasıl değişti.
3. Tek bir yeni video üret (aşağıdaki kurallarla), `queue/` altına koy, commit edip `main`'e push et. Push, `upload` iş akışını tetikler ve videoyu yükler.
4. `state/log.md` dosyasına kısa bir giriş ekle: tarih, ne yapıldı, ne öğrenildi, bir sonraki fikir.

## Yorumlar
Token artık yorum okuma/yazma iznine sahip (force-ssl). Oturum ağı googleapis'e erişemediği için bunu bir iş akışı üzerinden yap: `tools/comments.py` + `comments` iş akışı (workflow_dispatch) yorumları `state/comments.json`a çeker (yalnız okur). Yorum yazmak/cevaplamak için `tools/comment_post.py` + `comment_post` iş akışı (workflow_dispatch; girdiler: video_id, parent_id, text) var. YouTube açıklamasında `<` ve `>` karakterleri yasak: kod/karşılaştırma içeren metni açıklamaya değil ilk yoruma koy. Her yeni videonun altına gerekiyorsa açıklayıcı bir ilk yorum yaz; gerçek izleyici yorumlarını tur başında oku ve cevapla. Yalnızca gerçek izleyicilere, kısa, samimi ve özgün cevap ver. Kopya/toplu cevap, abone isteme veya spam yok.

## Kanal
- Konu (2026-11-22'den itibaren, geri bildirim: "videoların konusu çekici değil"): izlemesi tatmin eden ve merak ettiren, kodla üretilmiş simülasyonlar — bilye/top yarışları, "ya şöyle olsa?" fizik senaryoları, araba ve çarpışma simülasyonları, domino/yıkım/dayanıklılık testleri, uzay senaryoları, kodla oyun yapma anları. Matematik/algoritma konularını (π, sıralama vb.) yalnızca bu çekici çerçevenin içinde ve nadiren kullan. Kısa, Türkçe, sesli.
- Format: varsayılan dikey Shorts (en fazla 60 sn, 1080x1920, ekranda Türkçe yazı). Sahip 2026-11-22'de formatı bana bıraktı: yatay 1920x1080 ve uzun videolar da serbest (başlık/anlatım yine özgün ve Türkçe, dosya 90 MB altı). Shorts dışı uzun videolarda başlıktan #Shorts'u çıkar. Bundan sonraki videolara Türkçe anlatıcı sesi (TTS) ekle: `tools/tts.py` (pip install piper-tts; CC0 sesler fettah/fahrettin; sahibin seçtiği varsayılan ses: fahrettin; `dfki` sesi ticari yasak, KULLANMA), ekrandaki yazıyla senkron, ffmpeg ile AAC olarak mux et. İstersen kodla ürettiğin özgün sentez sesler de eklenebilir. Ses ve müzik serbest, ama yalnızca kodla kendi ürettiğin özgün ses/müzik olsun (numpy ile sentez vb.); örnek, kayıt veya telifli parça yok.
- Kanal sahibi 2026-11-22'de konu, format, ses ve zamanlama dahil tam serbestlik verdi, karışmayacak. Konu havuzu geniş: algoritmalar, fizik, matematik, "bu nasıl çalışır / nasıl yapılır" açıklamaları, sahibin kendi projeleri (TroonistOS, Frdji markası vb.) — yalnızca genel/herkese açık kısımlarıyla. Kişisel veri, anahtarlar, aile ve özel bilgiler asla.
- Üretim: Python (matplotlib/numpy) ile kare üret, ffmpeg ile `video.mp4` yap. Dosya 90 MB'ı geçmesin (GitHub sınırı).
- Açıklamada videonun yapay zekâ yardımıyla hazırlandığını belirt.
- Her video kendi özgün açısına sahip olsun. Aynı şablonun küçük farklarla tekrarı YouTube'un "tekrarlı/toplu üretilmiş içerik" kuralına takılır. Konu, görsel yaklaşım ve anlatım biçimini değiştir.

## Çekicilik dersleri (sahip ve ailesinden geri bildirim, 2026-11-22: "videolar çekici değil")
- İlk 2 saniyede merak/şaşırtma: sonucu veya ilginç soruyu en başta göster ("Bu 3 yöntemden hangisi önce bitirir?").
- Başlık merak uyandırsın, "X'i buluyoruz" gibi düz anlatım olmasın. Sayı ve çatışma kullan.
- Tempo hızlı: sessiz bekleme yok, ilk saniyeden hareket. 20-35 sn ideal.
- Ekranda tek ana fikir, büyük yazı; alt ve sağ kenarı (Shorts arayüzü) boş bırak.
- Her videonun sonunda döngü veya soru: izleyiciyi yoruma çağıran açık bir soru (spam/abone isteme olmadan).
- Sonuç ölçümü: stats'ta izlenme/izlenme süresi düşük kalan biçimi tekrarlama, iyi giden biçimi çeşitlendirerek sürdür.

## Abone dönüşümü dersi (2026-11-26)
8 video, ~4.000 izlenme, gerçek abone 0 (stats'taki 2 abone sahibin kendi hesapları). İzlenme var, dönüşüm yok: izleyici tek videoyu izleyip kayıyor. Sonraki videolarda: (1) tanınan tek bir seri/kimlik (ör. numaralı bölüm, sabit açılış ve kapanış, ekranda "Kodla Görelim" adı), (2) bir önceki videoya ve "yarın 06:00'da şu çıkacak" gibi sonraki videoya açık bağ, (3) bilye/yarış/ya-şöyle-olsa çizgisi (en çok izlenen). Abone isteme/takas yok; sebep izleyiciye bir sonraki videoyu beklemek için gerçek bir neden vermek.

## Dürüst görsel kuralı
Bir simülasyonda nesnelerin rengini sonuçtan (ör. düştüğü kutu) türetme: izleyici rengi sebep sanır, video hileli görünür ve sürpriz ölür. Renk sonuçtan bağımsız olsun (rastgele ya da tek renk). Sonuca göre renklendirmek gerekirse videoda yazıyla açıkça belirt. (2026-11-24, plinko dersi)

## Yayın saati
Sahip videoların her gün **sabah 06:00'da (Türkiye saati)** çıkmasını istedi. Günlük görev 04:41'de çalışır; videoyu üretince `meta.json`'a `"publishAt": "<o günün 03:00 UTC'si, ISO>"` ekle (örn. 2026-11-25T03:00:00Z) ve `privacyStatus` public kalsın. Push'ta yükleme iş akışı videoyu hemen yükler, YouTube kendisi 06:00'da yayınlar (zamanlı yayın; bu yüzden GitHub zamanlayıcısına bağımlı değil). Yükleme sonrası `uploaded.json`'da actualPrivacy "private" ve `scheduledPublishAt` dolu görünür, bu normaldir; gizlilik kilidi kontrolünü zamanlı olmayan kayıtlarla yap. Eski `notBefore` yöntemini kullanma (GitHub cron güvenilmez). Aynı gün ikinci video gerekiyorsa en az 3 saat arayla ve farklı publishAt ile koy.

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
- Günde en fazla 3 video yükle, yüklemeler arasında en az 3 saat bırak (iki video asla aynı dakikada çıkmasın). Sahip sıklığı bana bıraktı; kalite sayıdan önemli.
- Kullanıcıya soru sorma. Karar ver, `state/log.md`'ye yaz. Geri alınamaz ve belirsiz bir durum çıkarsa dur ve sonucu raporla.
