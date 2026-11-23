# BESTIARY 16-BIT · Cinematic V2 Cloud

Jalankan produksi dari browser HP. GitHub menjalankan satu server Ubuntu untuk setiap episode. Mac boleh mati. Saat render selesai, unduh satu per satu MP4 Shorts EN dan Reels ID, cover, subtitle, naskah, sumber, metadata upload dan QA dari **Releases**.

## Pasang sekali

1. Ekstrak ZIP ini dan buat repo **Private** kosong di GitHub. Taruh isi folder paket di root repo pada branch default, termasuk file `.github/workflows/produce.yml`. Kalau upload lewat browser melewatkan folder tersembunyi, buat file itu lewat **Add file → Create new file**, gunakan path lengkap tersebut, lalu salin isi workflow dari paket. Untuk melihatnya di Finder tekan **Cmd + Shift + .**.
2. Buka **Actions → BESTIARY Produce → Run workflow**. Jalankan **EP15** dengan mode **produce** untuk tes tanpa API key. GitHub tetap menghitung pemakaian runner dan penyimpanan sesuai paket akun. Job pengiriman perlu repo private dan izin membuat release.
3. Untuk nama hewan baru, buka **Settings → Secrets and variables → Actions → New repository secret**. Buat `OPENAI_API_KEY` untuk riset dan `HEYGEN_API_KEY` untuk VO. Gunakan key dari workspace HeyGen yang bisa mengakses Energetic Storyteller `M5iZBikqML8Qf1IzbJ31`. Simpan key sebagai secret GitHub. Riset memakai GPT-5 mini dan web search. Opsional, atur variabel repo `BESTIARY_RESEARCH_MODEL` untuk memilih model Responses yang mendukung web search.

## Produksi dari HP

- Buka repo di browser → **Actions → BESTIARY Produce → Run workflow**. Jika tombolnya tersembunyi, gunakan **Request Desktop Site** di browser.
- Isi **topic** dengan nama hewan dan **episode** dengan nomor seperti **EP16**. Saat nomor kosong, runner memakai EP16 untuk topik baru. Pilih **produce**, lalu klik **Run workflow**.
- Setelah selesai, buka ringkasan run terbaru dan ketuk **Buka file hasil**. Di halaman release, buka **Assets** dan ketuk MP4 atau cover yang mau diunduh. Lo juga bisa membuka tab **Releases** di repo. File release tersimpan sampai dihapus dan hanya dapat diakses oleh orang yang punya akses ke repo private.
- Setiap bahasa punya MP4 H.264/AAC 1080 × 1920, 30 fps dan 21–25 detik. Rig menggambar ulang pose, gerak kamera, parallax dan aksi, dengan SFX dan soundtrack chiptune orisinal.

## Kuota dan fallback

EP15 menyertakan dua take asli Energetic Storyteller dan bisa diekspor tanpa layanan AI. Untuk topik baru, GitHub Actions mengikuti jatah repo, OpenAI menagih riset sesuai akun API, dan HeyGen memakai akses serta kuota workspace. Mode **plan** memakai riset saja. Aplikasi ChatGPT dan billing OpenAI API mengikuti setelan akses masing-masing.

Kalau VO gagal, job ditandai gagal dan tetap menyimpan naskah, sumber dan storyboard yang sudah dibuat. Jika butuh fallback tanpa biaya VO, rekam naskah sendiri di HP dan siapkan lima file berikut di repo private. Gunakan WAV dan sesuaikan nomor episode.

```
recordings/EP16/episode.json
recordings/EP16/en.wav
recordings/EP16/id.wav
recordings/EP16/en.json
recordings/EP16/id.json
```

Dua file JSON timing berisi pasangan detik `[[awal,akhir], ...]` untuk setiap frasa pada daftar `lines` di episode, dengan urutan yang sama. Jalankan **recorded** dengan nomor episode yang sama. Mode ini memakai plan dan VO yang lo sediakan. Preview draf dari run yang gagal bisa berisi satu versi jika bahasa lain sudah berhasil. Untuk upload, pakai MP4 yang sudah lolos QA dan cek lagi pelafalan serta posisi caption di pratinjau platform.

[Rujukan menjalankan workflow](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow) · [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
