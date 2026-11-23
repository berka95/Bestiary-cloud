# Produksi BESTIARY dari aplikasi ChatGPT

Mulai dan pantau render dari **ChatGPT → Codex → Cloud → BESTIARY**. GitHub Actions mengerjakan render saat Mac mati. ChatGPT mengembalikan link MP4, cover, dan teks upload satu per satu. Link hasil mengarah ke repo private dan mungkin membuka halaman GitHub atau meminta login.

## Sambungkan sekali dari ChatGPT desktop

1. Pasang isi paket ini pada branch default repo GitHub private sesuai README. Jika repo sudah memakai paket cloud sebelumnya, tambahkan `chat_produce.py`, `AGENTS.md`, dan panduan ini. Workflow terbaru menyajikan MP4 sebagai file terpisah.
2. Di ChatGPT desktop buka **Settings → Codex Cloud → Environments → Create environment**. Buat environment **BESTIARY** dan pilih repo itu. Sambungkan GitHub bila diminta.
3. Buat **fine-grained personal access token** GitHub untuk **repo BESTIARY itu saja** dengan izin **Actions: Read and write** dan **Contents: Read-only**. Contents read diperlukan untuk membaca file release. Simpan token sebagai **HTTP secret** bernama `BESTIARY_GITHUB_TOKEN`, dengan domain `api.github.com`. Tambah environment variable `BESTIARY_REPO` berisi `OWNER/REPO`. Izinkan akses HTTPS ke `api.github.com` dan publish environment. Jangan kirim token lewat chat.
4. Dari HP, buka aplikasi **ChatGPT → Codex → Cloud → BESTIARY**. Kirim **“Produksi EP15 Velvet Worm pakai demo bawaan. Tunggu sampai selesai dan kasih link MP4.”** Demo ini memakai take HeyGen yang sudah disertakan. Setelah demo berhasil, cukup kirim **“Produksi BESTIARY EP16 Mudskipper.”**

Untuk episode baru, konfigurasi `OPENAI_API_KEY` dan `HEYGEN_API_KEY` tetap ada di **GitHub Actions Secrets**, sebagaimana dijelaskan di README. Token yang dipakai ChatGPT hanya menghubungkan permintaan dan status produksi ke repo; kredensial produksi dipakai oleh runner GitHub. Akses Codex Cloud mengikuti paket dan pengaturan workspace ChatGPT.

[Setelan Codex Cloud](https://learn.chatgpt.com/docs/environments/cloud-environments) · [Izin workflow GitHub](https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event)
