# Fon Takip — Otomatik Güncelleme

Orijinal dashboard içerik ve görünüm olarak korunur. HTML, GitHub yükleme sınırları yüzünden `site-archive/000.txt` … `025.txt` parçalarında saklanır. Netlify derlemesinde `scripts/bootstrap.py` bunları birleştirir ve **SHA-256 ile orijinal dosyayla birebir eşitliğini denetler**.

- Orijinal dosya: 5.156.725 bayt; SHA-256: `dcf107747f7b28a9cbe14094349a1d484f11ff413c0242c037f549b4d2f468c8`.
- Netlify yayın klasörü: `public`.
- Veri çekme günleri: günlük 10.00 ve 19.00 Türkiye saati hedefi.
- Veri kaynakları: Fonoloji/TEFAS günlük fon fiyatı, AUM ve yatırımcı; KAP portföy ve ödeme bilgilerinin doğrulanmış entegrasyonu sonraki faz.
- `FONOLOJI_KEY` yalnız GitHub Actions Secrets içine konulmalı; kaynak koduna konulmamalı.
- İlk yayında HTML özgün haliyle açılır. Gerçek veri sağlayıcı entegrasyonunun ilk başarılı çalışmasından sonra güncellenmiş veriler yayımlanır.
- Başarısız, eksik veya tutarsız kaynak verileri yayına alınmaz.

**Kurulum:** Netlify > Add new project > Import an existing project > GitHub > `Validation2026/Fon-Takip`. `netlify.toml` varsayılan kurulum ayarlarını içerir. `build command`: `python3 scripts/bootstrap.py`; `publish directory`: `public`.

Dosyalardaki veriler bilgi amaçlıdır; tekil ihraççı ödeme bildirimleri doğrulanmadan ödendi/ödenmedi durumları değiştirilmez.
