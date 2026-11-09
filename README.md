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


## 2026-11: KAP referans izleme pilotu

- `scripts/kap_watch.py` Fonoloji'nin fon bazlı KAP portföy ve bildirim alanlarını **TLY ve TP2** için okur.
- Sonuçlar `audit/kap_latest.json` dosyasında denetim amacıyla tutulur; mevcut HTML'deki KAP portföy pozisyonları ve ödendi/ödenmedi durumları **asla otomatik değiştirilmez**.
- `payment_status = NOT_VERIFIED` bir temerrüt/ödeme kararı değildir. Ödeme teyidi için açıklamanın resmi KAP metni ve hak kullanım/ödeme belgeleri ayrıca doğrulanmalıdır.
- Resmi KAP Veri Yayın Servisi abonelik/yetkilendirme gerektirir. Bu pilot Fonoloji'deki KAP kaynaklı referans bilgileriyle sınırlıdır.
- Fonoloji günlük ve aylık kota kontrolü `scripts/update_rolling.py` tarafından yapılır; fon fiyatı ve büyüklüğü tarihleri fon bazındadır, tek bir gün herkes için güncel sayılmaz.
- `audit/latest.json` fon kapsamını, `state/scan.json` tarama ilerlemesini içerir. `public/data/fund_prices.json` kısmi veri durumunu açıkça belirtir.
- Veri dosyaları GitHub'a işlendiğinde Netlify yayın yapar ancak aynı veri commit'i yeni bir fon taramasını başlatmaz. Manuel çalıştırma `workflow_dispatch` ile mümkündür.

### KAP çapraz kaynak karşılaştırması ve ödeme işaretleri

- `scripts/kap_compare.py`, orijinal HTML içindeki `R` pozisyonları ile Fonoloji'nin en son KAP portföyü arasında **yalnızca tekil ve birebir menkul kıymet kodu eşleşmelerini** yüzde puan cinsinden karşılaştırır. Kod birden fazla satırda geçiyorsa yanıltıcı toplama yapmayıp karşılaştırma dışı bırakır.
- Orijinal rapor döneminin kesin eşleşmesi doğrulanmadığından, farklar **yeni alım/satım veya işlem kanıtı değildir**; `audit/kap_latest.json` içine sadece denetim referansı olarak kaydedilir.
- Ödeme/iade/temerrüt kelimeleri geçen KAP bildirimleri *inceleme adayı* olarak işaretlenir. **Hiçbir durumda otomatik `Ödendi` veya `Ödenmedi` kararı verilmez.**
- İlk KAP taraması baz alınır; sonraki çalışmalarda yeni bildirim numaraları ve rapor dönemi değişiklikleri sayılır. Sağlayıcı düzeltmeleri işlem/pozisyon değişikliği sayılmaz.

### KAP denetiminin Netlify'da salt-okunur yayını

- Pilot başarılı olduğunda `public/data/kap_watch.json` oluşturulur; Netlify yayını üzerinden `/data/kap_watch.json` adresinde okunabilir.
- Bu JSON, **yalnızca TLY ve TP2** için referans karşılaştırma verisidir; orijinal sekiz bölümlü HTML değiştirilmez.
- `payment_data_verified: false` ve `payment_status: NOT_VERIFIED` alanları bilinçli olarak korunur. Bir bildirimde ödeme kelimesinin geçmesi işlem yapıldığına kanıt değildir.
- Kaynağın herhangi birinde eksik/bozuk veri varsa yeni pilot dosyası yayımlanmaz; son başarılı verinin tarihine bakılmalıdır.

### 8 fonluk KAP izleme kapsamı

- İzlenen fonlar: TLY, TP2, THF, KHA, PRY, HEH, KSA, AC4. Bunlar yalnızca pilot kapsamdır; 2.540 fonun tamamı izleniyor denmez.
- Her biri için son portföy dönemi, pozisyon sayısı ve son 20 KAP bildirimi izlenir. Kaynak dönemleri farklı olabilir.
- Fon adları orijinal dashboard'daki veri kümesinden alınır. Orijinal sekiz bölüm, portföy ve ödeme alanları değişmez.
- Pilot kaynaklardan birinin veri kalitesi/erişim hatası halinde kısmi pilot 'PILOT_INCOMPLETE' sayılır; eski başarılı KAP verisi korunur.

### Kısmi KAP pilotu

- KAP'da sekiz pilottan biri erişilemezse, TLY ve TP2 dahil en az beş doğrulanmış fon bulunduğunda **PILOT_PARTIAL** yayımlanabilir. Eksik kodlar ve hata türleri `errors` içinde listelenir; sekiz fonun tamamı doğrulanmış sayılmaz.
- Portföy isteği yalnız `holdings` bloğunu talep eder. Gövde en fazla 8 MB ile sınırlandırılır; beklenmedik HTML veya hatalı JSON işlenmez.
- KAP kısmi hata ana fiyat/AUM otomasyonunu durdurmaz; kaynak veri dönemleri ayrı tutulur.
