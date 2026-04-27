# Tarozi AI Soft

Temir yo'l vagonlarini avtomatik aniqlash, raqamini o'qish va tarozida tortish tizimi.

RTSP kameralardan real-time video olib, YOLO modellari yordamida vagonlarni aniqlaydi, vagon raqamini OCR bilan o'qiydi, raqamli tarozidan og'irlikni oladi va ma'lumotlarni serverga yuboradi.

---

## Texnologiyalar

| Soha | Texnologiya |
|------|-------------|
| GUI | PyQt6 (Fusion style, frameless window) |
| AI/ML | PyTorch + Ultralytics YOLO v8 |
| Video | PyAV (RTSP/H.264), OpenCV |
| Ma'lumotlar bazasi | SQLite3 |
| Shifrlash | AES-256 CBC (PyCryptodome) |
| Tarozi | PySerial (RS-232, 9600 baud) |
| Server | REST API (Bearer token auth) |

---

## O'rnatish

### 1. Python virtual environment

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. YOLO modellar

Quyidagi fayllarni `models/` papkaga joylashtiring:

| Fayl | Hajm | Vazifa |
|------|------|--------|
| `wagon_id.pt` | ~45 MB | Vagonni aniqlash (detection + tracking) |
| `wagon_id_number.pt` | ~52 MB | Vagon raqamini o'qish (OCR) |

### 3. Environment variables (ixtiyoriy)

Parollar default qiymatlar bilan ishlaydi, lekin **production** uchun env var o'rnatish tavsiya etiladi:

```bash
# Server autentifikatsiya
set TAROZI_BASE_DOMAIN=ai-project.das-uty.uz
set TAROZI_USERNAME=wagon
set TAROZI_PASSWORD=***
set TAROZI_APP_USERNAME=tarozi
set TAROZI_APP_PASSWORD=***
set TAROZI_STATIC_PASSWORD=***

# Shifrlash kaliti (mavjud key.bin bilan mos bo'lishi kerak)
set TAROZI_CIPHER_PASSWORD=***
set TAROZI_CIPHER_SALT=***          # base64 encoded
```

> Env var o'rnatilmasa — `core/config.py` dagi default qiymatlar ishlatiladi.

---

## Ishga tushirish

```bash
# Administrator huquqi bilan:
venv\Scripts\python.exe main.py
```

Dastur administrator huquqisiz ishlamaydi (tarozi COM porti uchun kerak).

---

## Loyiha tuzilishi

```
Tarozi AI Soft/
├── main.py                    # Kirish nuqtasi
├── warmup.py                  # YOLO modellarni oldindan yuklash
├── requirements.txt
├── .gitignore
│
├── core/                      # Yadro modullari
│   ├── config.py              # Markaziy konfiguratsiya, konstantlar
│   ├── database.py            # SQLite BufferDB (backup + history)
│   └── cipher.py              # AES-256 shifrlash/deshifrlash
│
├── ui/                        # Foydalanuvchi interfeysi (PyQt6)
│   ├── app.py                 # App klass (mixin-based)
│   ├── main_window.py         # Eski monolitik App (hali ishlatiladi)
│   ├── models.py              # SendingData, SavingData dataclasslari
│   ├── settings_manager.py    # Shifrlangan sozlamalar boshqaruvi
│   ├── theme.py               # DARK/LIGHT rang palitralari
│   ├── styles.py              # CSS stylesheet generatsiya
│   ├── widgets.py             # Custom widgetlar (Switch, BlurEffect, ...)
│   ├── video_label.py         # Video ko'rsatish widgeti
│   ├── table.py               # Ma'lumotlar jadvali
│   ├── history.py             # Tarix ko'rish
│   ├── settings_panel.py      # Sozlamalar paneli
│   ├── dialogs.py             # Dialog oynalari
│   ├── password_dialog.py     # Parol kiritish dialogi
│   ├── app_builder.py         # UI qurish (mixin)
│   ├── app_mixins.py          # Blur, Theme, Timer mixinlari
│   ├── app_settings.py        # Parol/maxfiy sozlamalar (mixin)
│   ├── app_cam_settings.py    # Kamera sozlamalari (mixin)
│   ├── app_video.py           # Video boshqaruvi (mixin)
│   ├── app_data.py            # Ma'lumot ko'rsatish (mixin)
│   ├── app_upload.py          # Yuklash logikasi (mixin)
│   ├── app_responses.py       # Server javoblarini qayta ishlash (mixin)
│   └── app_window.py          # Oyna boshqaruvi (mixin)
│
├── threads/                   # Background threadlar
│   ├── base_video.py          # Video threadlar uchun base klass
│   ├── video.py               # Manual rejim (VideoThread)
│   ├── auto_video.py          # Avto rejim (AutoVideoThread)
│   ├── upload.py              # Server ga yuborish threadlari
│   ├── workers.py             # Server, login, tarozi, kamera threadlari
│   └── model_cache.py         # YOLO model singleton
│
├── network/                   # API aloqa
│   └── api.py                 # login, upload, token boshqaruvi
│
├── utils/                     # Yordamchi funksiyalar
│   ├── helpers.py             # UI, network, serial, Luhn, GPU helpers
│   └── image.py               # Rasm konvertatsiya (QPixmap <-> ndarray)
│
├── models/                    # YOLO modellar (.pt)
├── images/                    # UI rasm/iconkalar
├── settings/                  # Runtime config (shifrlangan .bin fayllar)
├── log/                       # Shifrlangan loglar
├── backup/                    # Offline saqlangan rasmlar
└── history/                   # Tarix eksportlari
```

---

## Arxitektura

### Asosiy oqim

```
RTSP kamera ──→ Capture Thread ──→ Frame Queue
                                       │
                                       ├──→ Display Loop (10 FPS) ──→ UI
                                       │       ↑ draw commands
                                       └──→ Inference Thread (2-3 FPS)
                                               │
                                               ├── YOLO Detection (wagon_id.pt)
                                               ├── YOLO OCR (wagon_id_number.pt)
                                               └──→ Draw Commands ──→ Display Loop
                                               └──→ Data Signal ──→ Upload Thread ──→ Server
```

### Threadlar (8 ta)

| Thread | Vazifa | Signal |
|--------|--------|--------|
| `VideoThread` | Manual rejim: detection + OCR | `data_signal`, `image_signal` |
| `AutoVideoThread` | Avto rejim: tracking + auto-send | `data_signal`, `image_signal` |
| `ServerConnectionThread` | Server/internet holatini tekshirish (53s interval) | `connection_signal` |
| `LoginThread` | Token olish/yangilash | `login_signal` |
| `ScaleThread` | COM portdan og'irlik o'qish (1s interval) | `scale_signal` |
| `SaveThread` | RTSP kamera ulanishini tekshirish | `save_signal` |
| `UploadThread` | Ma'lumotni serverga yuborish | `message_signal` |
| `BackupUploadThread` | Offline buffer dagi ma'lumotlarni sync | `upload_signal` |

### Display arxitekturasi (titrashsiz)

```
Capture Thread:    [raw1] [raw2] [raw3] [raw4] [raw5] [raw6]  (15 FPS)
Inference Thread:  [cmds]........................[cmds]         (2-3 FPS)
Display Loop:      raw1   raw2   raw3   raw4   raw5   raw6    (10 FPS)
                   +cmds  +cmds  +cmds  +cmds  +cmds  +cmds
```

Inference thread rasm chizmaydi — faqat **draw commands** (rect, text, fill) saqlaydi.
Display loop har bir yangi raw kadrga shu buyruqlarni chizadi.
Natija: silliq video + annotatsiyalar doimo ko'rinadi.

### Ma'lumotlar bazasi

Ikki turdagi jadval:

**`backup`** — serverga yuborilmagan ma'lumotlar (offline buffer):
```
id | wagonImage1Base64 | wagonImage2Base64 | wagonNumberImageBase64 | wagonNumber | scaleNumber | stationCode | scaleCode | createdDate
```

**`history_YYYY_MM`** — oylik tarix (dinamik yaratiladi):
```
id | source_id | ... (backup bilan bir xil) ... | sentAt
```

### Shifrlash

Barcha sozlamalar AES-256 CBC bilan shifrlangan:
- `settings/*.bin` — kamera URL, parollar, parametrlar
- `log/logs.bin` — dastur loglari
- Kalit: PBKDF2 dan hosil qilingan, `settings/key.bin` da saqlanadi

### Auto rejim oqimi

1. YOLO vagonni aniqlaydi va `track_id` beradi (BotSort tracker)
2. Har kadrda vagonning `x_min` pozitsiyasi yig'iladi
3. `max_count` kadr to'planganda, `dx` (siljish) tekshiriladi
4. Agar `abs(dx) <= threshold` — vagon to'xtagan deb hisoblanadi
5. OCR vagon raqamini o'qiydi
6. Luhn algoritmi bilan raqam tekshiriladi/tuzatiladi
7. Tarozi og'irligi >= 20,000 kg bo'lsa — serverga yuboriladi
8. Timeout boshlanadi (qayta yuborish oldini olish)

---

## Konfiguratsiya

### Dastur ichidagi sozlamalar

| Parametr | Default | Tavsif |
|----------|---------|--------|
| `STATION_CODE` | 111111 | Stansiya kodi |
| `SCALE_CODE` | 111111 | Tarozi kodi |
| `SEND_TIME` | 75 | Yuborish intervali (soniya) |
| `D_CONF` | 0.7 | Detection confidence (0.6-0.8) |
| `R_CONF` | 0.75 | Recognition confidence (0.7-0.85) |
| `AUTO` | false | Avtomatik rejim |
| `THEME` | LIGHT | Mavzu (DARK/LIGHT) |

### Maxfiy sozlamalar

Parol bilan himoyalangan (default: `@1234@4321@`).
`Ctrl+Shift+Middle Click` — kamera sozlamalarini ochadi.

### Kamera parametrlari (har bir kamera uchun alohida)

| Parametr | Default | Tavsif |
|----------|---------|--------|
| `top/bottom/left/right` | 40/1/2/2 | Detection zonasi (%) |
| `frame_count` | 128 | To'xtash uchun kerak kadrlar soni |
| `distance` | 6 | Siljish threshold (piksel) |
| `fps` | true | FPS ko'rsatish |
| `half` | false | FP16 inference (CUDA 7.0+ kerak) |

---

## Server API

```
POST /api/auth/device-login     — Token olish
POST /api/wagon-scale-values    — Vagon ma'lumotini yuborish
```

Yuborish formati:
```json
{
  "wagonNumber": "62481037",
  "scaleNumber": 85000,
  "stationCode": "111111",
  "scaleCode": "111111",
  "createdDate": "2026-04-10T08:30:00Z",
  "wagonImage1Base64": "data:image/jpeg;base64,...",
  "wagonImage2Base64": "data:image/jpeg;base64,...",
  "wagonNumberImageBase64": "data:image/jpeg;base64,..."
}
```

Internet yo'q bo'lganda ma'lumot `backup` jadvaliga saqlanadi, rasmlar `backup/` papkaga yoziladi. Internet qaytganda avtomatik sync bo'ladi.

---

## Vagon raqami tekshiruvi (Luhn)

8 raqamli vagon kodi Luhn algoritmi bilan tekshiriladi:
- 7 ta asosiy raqam + 1 ta tekshiruv raqami
- Agar OCR 1-2 ta raqamni aniqlamasa (`x` belgisi), Luhn bilan tuzatishga harakat qilinadi
- Raqam `0` yoki `1` bilan boshlanmaydi

---

## Tez-tez uchraydigan muammolar

| Muammo | Yechim |
|--------|--------|
| "Dasturni administrator huquqlari bilan oching" | Dasturni Run as Administrator bilan ishga tushiring |
| Kamera ulanmayapti | RTSP URL ni tekshiring, kamera IP ga ping qiling |
| Tarozi ko'rinmayapti | COM port mavjudligini Device Manager da tekshiring |
| GPU ishlatilmayapti | CUDA Toolkit va NVIDIA driver o'rnatilganini tekshiring |
| Token olinmayapti | Server URL va login/parolni maxfiy sozlamalarda tekshiring |
| Backup to'planib ketyapti | Server aloqasini tekshiring, `backup/` papkani kuzating |
