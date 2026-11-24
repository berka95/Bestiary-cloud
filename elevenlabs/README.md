# BESTIARY 16-BIT · workflow ElevenLabs

Workflow cloud dari naskah final ke MP4. Narasi diambil langsung dari ElevenLabs bersama timestamp per karakter. FFmpeg menyesuaikan tempo dengan durasi video. Renderer memakai timestamp itu untuk takarir dan adegan. Musik, efek suara, dan visual tetap dirender di cloud.

## Setup satu kali

1. Buat API key di akun ElevenLabs. Izinkan **Text to Speech** serta akses baca untuk **Voices**, **Models**, dan informasi **User/Subscription**. Simpan sebagai secret `ELEVENLABS_API_KEY` di Codex Cloud atau GitHub Actions. Masukkan key langsung di pengaturan secret.
2. Pastikan usage-based billing di workspace ElevenLabs nonaktif. Workflow memeriksa sisa kredit sebelum setiap narasi baru.
3. Preset awal mengikuti rekaman EP17 dengan Roger, Eleven v4, stability 50%, dan similarity 75%. Jika Roger di akunmu memakai ID lain, set variabel `ELEVENLABS_VOICE_ID`. Pemeriksaan awal menampilkan nama suara sebagaimana tercatat di akun.

[Autentikasi ElevenLabs](https://elevenlabs.io/docs/api-reference/authentication) · [Model ElevenLabs](https://elevenlabs.io/docs/overview/models) · [API narasi dan timestamp](https://elevenlabs.io/docs/api-reference/text-to-speech/convert-with-timestamps)

## Jalankan di Codex Cloud

Pasang dependensi Python dari `requirements.txt` di cloud. Renderer memakai FFmpeg, FFprobe, DejaVu, dan Liberation Sans.

```bash
python bestiary.py EP17 --check
python bestiary.py EP17
```

`--check` hanya membaca konfigurasi ElevenLabs. Perintah kedua menggunakan kredit narasi dari langganan dan menaruh MP4, paket publikasi, serta hasil pemeriksaan teknis di `output/EP17/`. Cloud yang sama menyimpan respons narasi di `.work/` dan memakainya kembali bila naskah serta preset masih sama. Jika koneksi putus saat request, cek History ElevenLabs sebelum mencoba lagi.

## Jalankan di GitHub Actions

Di repo ini, kode produksi ada di folder `elevenlabs/`. Di tab **Actions**, pilih **BESTIARY ElevenLabs** lalu **Run workflow**. Jalankan pemeriksaan akun dengan opsi Generate kosong, atau pilih Generate untuk merender. Ambil hasilnya dari **Artifacts** pada halaman run.

Gunakan repo privat jika naskah atau hasilnya belum boleh dibagikan. GitHub-hosted runner memakai kuota Actions repo. Pastikan repo masih memiliki menit yang termasuk dalam paket. Setiap dispatch produksi baru memakai runner baru dan bisa memakai kredit lagi. Jika render gagal setelah audio dibuat, cek History ElevenLabs sebelum dispatch ulang.

## Episode baru

Paket membawa renderer EP17 yang telah dipakai untuk Barreleye. Untuk perintah `Gas EP[nomor]`, minta Codex menyiapkan folder episode baru sebelum memanggil workflow. Gunakan kontrak berikut.

- `episode.json` memuat `animal` sebagai slug kapital, `duration` dalam detik, dan `captions` sebagai daftar potongan naskah final dalam urutan baca. Pakai baris baru untuk pemenggalan takarir pada layar.
- `render.py` menerima `--timing` dan `--output`. Buat visual khusus satwanya, dengan HUD EP17 sebagai acuan.
- `sound.py` menerima `--timing`, `--video`, `--voice`, dan `--output`. Pakai kode EP17 sebagai dasar musik dan SFX, lalu sesuaikan ke adegan baru.
- `publishing.txt` memuat judul, deskripsi, tag, caption, hashtag, dan sumber ilmiah.

Sesudah render, periksa gerakan satwa, pelafalan, takarir, dan keseimbangan audio sebelum publikasi. Workflow mengecek format, durasi, dekode, frame hitam atau beku, loudness, dan peak. Kredensial dan rekaman mentah tinggal di lingkungan produksi.
