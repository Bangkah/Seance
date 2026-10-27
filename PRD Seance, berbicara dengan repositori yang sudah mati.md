# PRD: Seance — berbicara dengan repositori yang sudah mati

Versi 0.2 · 27 Oktober 2026 · Status: dibekukan. Revisi 0.2 menyesuaikan PRD dengan aturan resmi challenge (lihat §19); rencana kerja kini 4 hari, bukan 5.

## 1. Ringkasan

**Seance** adalah CLI Python lokal yang membaca riwayat git sebuah repositori yang sudah ditinggalkan, lalu memakai **model open-weight lokal** (Ollama) untuk menghasilkan dua hal:

1. **Laporan autopsi**: proyek ini dulu untuk apa, kapan dan bagaimana ia "mati", dan langkah apa yang masuk akal untuk menghidupkannya kembali.
2. **Sesi séance**: kamu bertanya kepada repositori itu, dan ia menjawab dengan suara "arwah proyek" yang berbicara tentang commit-commitnya sendiri.

Prinsip utamanya: **model berbicara, kode memverifikasi.** Setiap klaim harus menunjuk bukti nyata (commit, file, tanggal) yang diperiksa oleh kode. Klaim tanpa bukti dibuang dan dihitung, tidak ditampilkan sebagai fakta.

Target: submission **Hacktoberfest Open-Source AI Challenge Week 4, tema "Ghost in the Machine"** (menghidupkan kembali alat open-source yang ditinggalkan).

**Batas kepatuhan yang mengikat seluruh dokumen ini:** challenge mensyaratkan proyek **baru** — repo dan seluruh isinya harus dimulai dan diselesaikan di dalam window challenge (26–30 Oktober 2026). Tidak ada satu baris pun kode dari proyek sebelumnya (termasuk TidyMind) yang disalin ke Seance. Artikel submission ditulis dalam **bahasa Inggris**; PRD ini tetap berbahasa Indonesia sebagai dokumen kerja.

## 2. Konteks challenge (terverifikasi 27 Oktober 2026)

| Hal | Isi resmi |
| --- | --- |
| Batas pengiriman | Halaman challenge & Official Rules: **31 Oktober 2026, 23:59 PDT** (≈ 1 November 13:59 WIB). Feed event DEV menyimpan `ends_at = 2026-10-31T06:59Z` (≈ 31 Oktober 13:59 WIB), **satu hari lebih awal**. Target internal: **terbit 30 Oktober 2026, 21:00 WIB**, yang aman untuk kedua tafsir. |
| Tag wajib | `#devchallenge`, `#hf26challenge` (maksimal 4 tag per post di DEV). |
| Syarat inti | Model open-weight, agent harness/framework open-source, atau inferensi lokal harus menjadi inti proyek. |
| Wajib ada di artikel | Mengapa open innovation penting untuk proyek ini, dan di mana pendekatan terbuka lebih baik daripada yang tertutup. |
| Bahasa artikel | **Inggris.** "Non-english submissions are eligible for a completion badge but not eligible for prizes." |
| Proyek baru | "All submissions and their respective repositories must be started and completed within the challenge window." Commit setelah deadline **wajib dicatat di README**. |
| Kode pihak ketiga | "Riffing on open source code and borrowing and improving on previous work/ideas is encouraged but it's important your changes are significant enough… Any non-generic, non-trivial usage of prior work, including open source code must be credited." |
| Tim | Boleh 1–4 orang; kalau berkelompok, semua DEV handle dicantumkan dan hanya satu post per tim. **Keputusan: solo.** |
| Kelayakan | 18+, punya akun DEV aktif. Indonesia **tidak** termasuk yurisdiksi yang dikecualikan (daftar: Afghanistan, Belarus, Republik Afrika Tengah, Kuba, Guinea Ekuatorial, Iran, Irak, Kosovo, Libya, Myanmar, Korea Utara, Rusia, Sudan Selatan, Sudan, Suriah, Tanzania, Venezuela, Yaman). |
| AI dalam proses | Diizinkan. |
| Penilaian | Kualitas tulisan (bobot terbesar), relevansi tema, kreativitas, eksekusi teknis, penggunaan teknologi partner (opsional). |
| Tie-break | Post dengan reaksi positif terbanyak. |
| Hadiah | Overall $250 + DEV++ + badge; 6 kategori featured $200; 14 kategori partner $100; semua submission valid dapat badge completion. Penerima hadiah tunai dapat diminta menandatangani affidavit dan menyerahkan W-9 / SSN / Federal Tax ID dalam 7 hari kerja. |

**Konsekuensi untuk rencana:** hari 5 untuk menulis artikel sudah tidak ada. Artikel **mulai ditulis hari 2**, diisi angka nyata hari 3–4, dan terbit 30 Oktober malam WIB.

## 3. Masalah dan pengguna

**Masalah.** Repositori yang ditinggalkan kehilangan konteksnya: pemiliknya lupa untuk apa ia dibuat, mengapa berhenti, dan apakah layak dihidupkan lagi. README sering usang dan riwayat commit panjang sulit dibaca. Mengirim riwayat itu ke API cloud tidak selalu pantas, karena repo pribadi bisa memuat path, nama klien, atau rahasia yang pernah ter-commit.

**Pengguna utama.** Developer yang ingin memutuskan nasib repo lamanya sendiri, atau yang sedang mengevaluasi proyek open-source terbengkalai sebelum mem-fork-nya.

**Mengapa model lokal.** Riwayat git adalah data sensitif yang tidak perlu meninggalkan mesin. Inferensi lokal berarti tanpa kunci API, tanpa biaya per permintaan, dan bisa berjalan tanpa internet setelah model terunduh (diklaim hanya jika benar-benar diuji dengan jaringan terputus).

## 4. Prinsip produk

1. **Read-only.** Seance tidak pernah mengubah repositori target dan tidak pernah menjalankan kode di dalamnya.
2. **Lokal.** Satu-satunya koneksi jaringan adalah ke Ollama di alamat loopback.
3. **Bukti dulu.** Fakta (tanggal, hash, jumlah, nama file) diambil dan diisi oleh kode. Model hanya menulis prosa di atas bukti yang disediakan.
4. **Fail-closed.** Output model yang tidak valid atau tidak berdasar ditolak. Setelah retry terbatas, perintah gagal dengan jelas dan tidak menampilkan setengah jawaban.
5. **Gaya bukan fakta.** Suara "arwah" hanyalah lapisan gaya. Ia tidak boleh mengubah isi klaim atau menambah fakta.

## 5. Ruang lingkup

| Prioritas | Fitur |
| --- | --- |
| P0 | Pembacaan repo yang aman, ekstraksi bukti deterministik (`facts`), laporan autopsi dengan validasi grounding |
| P1 | Mode `ask` (séance interaktif) dengan retrieval leksikal dan jawaban yang menyebut bukti |
| P2 | Nada bicara `spooky`, keluaran file Markdown |
| P3 (opsional, hanya jika P0–P1 selesai 29 Oktober) | (a) nada `warnet`; (b) perbandingan `gemma3:4b` vs `qwen3:4b` untuk kategori **Best Use of Gemma** |

**Di luar lingkup (MVP):** menjalankan atau membangun repo target, memeriksa kerentanan keamanan atau CVE (butuh basis data eksternal), analisis isi diff mendalam, repo di atas batas ukuran, GUI atau web, klaim dukungan macOS, analisis bahasa selain Python/JS/Go/Rust pada level manifest, dan penerjemahan otomatis yang dijamin berkualitas.

**Urutan pemotongan:** P3 (warnet lebih dulu daripada Gemma), lalu P2, lalu P1. P0 harus selesai dan teruji. Artikel tidak pernah dipotong — ia bobot penilaian terbesar.

## 6. Pengalaman pengguna (CLI)

```text
seance facts  <repo>                      # bukti deterministik, tanpa model
seance report <repo> [--output laporan.md] [--model qwen3:4b] [--lang en]
seance ask    <repo> [--tone plain|spooky|warnet]
```

Opsi umum: `--endpoint` (hanya loopback), `--max-commits` (default 2000), `--timeout`, `--debug`.

Contoh bentuk keluaran (**rancangan ilustratif, bukan keluaran nyata**):

```text
AUTOPSY: example-project
  Lahir : 2019-03-02 (C:a1b2c3d)
  Mati  : 2021-08-14 (C:9f8e7d6)  [terakhir ada commit]
  Jeda  : 62 bulan sejak commit terakhir

Penyebab kematian (hipotesis, bukan fakta):
  1. Pengembang utama berhenti commit setelah rilis v0.4. [C:9f8e7d6, M:authors]  keyakinan: sedang

Langkah kebangkitan (saran, bukan jaminan):
  1. Perbarui dependensi yang terakhir diubah 2020-11. [F:requirements.txt@4c5d6e7]

2 klaim dibuang karena tidak berdasar pada bukti.
```

`--lang` hanya memengaruhi bahasa prosa keluaran. Nilai default `en`; `id` disediakan untuk pemakaian pribadi dan **tidak** dipakai di artikel submission.

## 7. Requirement fungsional

### FR-01 Pembacaan repo yang aman

- Input: path repo lokal.
- Seance membuat **bare clone sementara** dengan `git clone --bare --no-local` ke direktori temp, lalu hanya membaca dari klon itu. Konfigurasi dan hook repo sumber tidak ikut tersalin.
- Setiap perintah git dijalankan tanpa shell, dengan `GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL` diarahkan ke perangkat kosong (`NUL` di Windows, `/dev/null` di Linux), `GIT_TERMINAL_PROMPT=0`, serta `--no-ext-diff` dan `--no-textconv`.
- Tidak ada checkout, tidak ada submodule, tidak ada eksekusi file repo.
- Direktori temp dihapus di akhir, termasuk saat terjadi error.
- **Penerimaan:** repo uji dengan `core.fsmonitor`, `diff.external` dan `core.pager` berbahaya (menunjuk ke skrip kenari) tidak pernah membuat file kenari tercipta.

### FR-02 Ekstraksi bukti deterministik

Kode mengekstrak, tanpa model:

- commit pertama dan terakhir, jumlah commit, rentang tanggal, jeda sejak commit terakhir, jumlah penulis (nama sesuai riwayat);
- tag/versi;
- manifest dependensi (misalnya `pyproject.toml`, `requirements.txt`, `package.json`, `go.mod`, `Cargo.toml`) dan **tanggal commit terakhir yang menyentuh masing-masing manifest** (tanda dependensi membusuk, dihitung tanpa jaringan);
- bahasa dominan berdasarkan ekstensi;
- teks README (dibatasi), 30 subjek commit terakhir, dan subjek commit yang mengandung kata kunci seperti `deprecated`, `broken`, `abandon`, `TODO`.

Setiap bukti mendapat **ID yang dibuat oleh kode**: `C:<hash7>` untuk commit, `F:<path>@<hash7>` untuk file pada commit tertentu, dan `M:<nama>` untuk metrik turunan. Model hanya boleh mengutip ID yang ada.

Definisi yang harus dipaku agar hasil reproducible: urutan commit memakai `--date-order` dengan tie-break hash; tanggal ditampilkan dalam format ISO dengan offset asli commit (bukan zona waktu mesin); nama penulis dinormalisasi dari `%an`; hash selalu 7 karakter pertama.

- **Penerimaan:** `seance facts` pada repo fixture menghasilkan JSON yang identik di setiap run (deterministik), termasuk saat dijalankan dengan `TZ` berbeda.

### FR-03 Anggaran konteks

- Paket bukti dibatasi (target awal 10.000 karakter untuk `report`, 6.000 untuk `ask`) dan `num_ctx` diatur **eksplisit** di setiap permintaan ke Ollama, karena konteks yang terlalu kecil bisa memotong prompt tanpa pesan error.
- Jika bukti melebihi anggaran, kode membuang bukti berprioritas rendah dengan aturan tetap dan mencatat "N bukti dihilangkan" di laporan.
- **Penerimaan:** repo besar tidak pernah menghasilkan prompt di atas anggaran, dan jumlah bukti yang dibuang tampil di keluaran.

### FR-04 Laporan autopsi (`report`)

- Model diminta menghasilkan JSON sesuai skema ketat: `summary`, `purpose`, `timeline[]`, `death_hypotheses[]`, `revival_steps[]`, masing-masing item berisi `text`, `evidence_ids[]`, dan untuk hipotesis `confidence` (`low|medium|high`).
- **Kode yang mengisi fakta**: tanggal pada timeline diambil dari bukti yang dikutip, bukan ditulis model.
- Validator grounding (lihat bagian 9) menolak item yang tidak lolos. Item yang ditolak dibuang dan dihitung.
- Retry terbatas (3), dengan variasi sampling pada percobaan ulang, lalu gagal tertutup.
- **Penerimaan:** tidak ada klaim di laporan akhir tanpa minimal satu ID bukti yang valid.

### FR-05 Sesi séance (`ask`)

- REPL: pengguna mengetik pertanyaan, kode mengambil bukti relevan (retrieval leksikal deterministik atas subjek/isi commit, path file, dan potongan README), model menjawab dengan JSON `{answer, evidence_ids[]}`.
- Jawaban tanpa bukti valid diganti kalimat penolakan tetap (misalnya "arwah ini tidak mengingat hal itu") dan tidak dikarang.
- Persona hanya memengaruhi gaya kalimat pada `answer`.
- **Penerimaan:** pertanyaan yang tidak ada dasar buktinya tidak menghasilkan jawaban faktual.

### FR-06 Nada bicara

- `plain` (default), `spooky`, dan `warnet`. `warnet` berstatus **eksperimental (P3)** dan hanya dimasukkan jika lolos uji kualitas kecil (lihat bagian 11). Jika kualitasnya buruk, fitur dihapus dari MVP dan hal itu dicatat sebagai batasan.

### FR-07 Keluaran

- Render terminal plus `--output` Markdown yang **tidak pernah menimpa** file yang sudah ada.
- Semua teks dari repo atau model di-escape dari karakter kontrol dan bidi sebelum dicetak.

### FR-08 Lokal saja

- `--endpoint` hanya menerima `localhost`, `127.0.0.1`, `::1`. Proxy environment diabaikan untuk koneksi ke Ollama.

### FR-09 Batas sumber daya

- `--max-commits` (default 2000), batas ukuran per file yang dibaca, file biner dilewati, penanganan encoding non-UTF-8 tanpa crash.

### FR-10 Kode keluar stabil

- Daftar kode keluar didokumentasikan: sukses, error input, model tidak tersedia atau output tidak valid, tidak ada bukti cukup, error internal.

## 8. Requirement non-fungsional

- **Privasi:** tidak ada telemetri, tidak ada koneksi non-loopback, tidak ada log yang menyimpan isi repo.
- **Portabilitas:** Windows 11 dan Linux, **Python 3.12** (dan 3.11), bergantung pada `git` terpasang. Dependensi runtime Python sebisa mungkin hanya library standar. **Catatan lingkungan 27 Oktober 2026:** mesin pengembangan masih memakai Python 3.10.20, sehingga `tomllib` tidak tersedia; pasang 3.12 sebelum hari 1 dimulai. Git 2.55.0, Ollama 0.40.11 dan ruff 0.16.8 sudah ada.
- **Kinerja:** target awal laporan selesai dalam 120 detik untuk repo sampai 2000 commit pada laptop pengembangan. **Angka ini adalah hipotesis yang harus diukur**, dan hasil ukurannya yang dilaporkan, bukan target ini.
- **Keterujian:** semua tes berjalan tanpa Ollama dan tanpa jaringan, memakai Ollama palsu dan repo fixture yang dibuat skrip.
- **Kualitas kode:** `ruff`, `mypy --strict`, `bandit`, pemindaian secret, dan CI dasar (lint, typecheck, test) di Ubuntu dan Windows. CI bukan kriteria penilaian, jadi jangan mengorbankan artikel untuk CI.
- **Dapat dicoba juri tanpa instalasi:** lihat artefak demo di bagian 11.

## 9. Arsitektur

```text
repo path
   |
   v
[gitreader]  bare clone sementara, perintah git aman, read-only
   |
   v
[evidence]   fakta deterministik + ID bukti (C:, F:, M:), anggaran konteks
   |
   v
[prompts]    bukti dibungkus sebagai DATA dalam JSON, instruksi tetap di sistem prompt
   |
   v
[model_client]  Ollama loopback, format JSON schema, num_ctx eksplisit, retry terbatas
   |
   v
[grounding validator]  setiap klaim dicek terhadap bukti; yang gagal dibuang dan dihitung
   |
   v
[renderer]   terminal atau Markdown, teks di-escape
```

Modul: `gitreader`, `evidence`, `retrieval`, `prompts`, `model_client`, `grounding`, `renderer`, `cli`.

### Aturan grounding (inti proyek)

1. Setiap item laporan atau jawaban punya `evidence_ids` berisi minimal satu ID.
2. Semua ID harus ada di paket bukti. ID yang tidak ada berarti item ditolak.
3. Jika item memuat `quote` (kutipan), kutipan itu harus persis sama dengan substring teks bukti yang dikutip.
4. Tanggal, hash, dan angka tidak ditulis bebas oleh model. Kode mengisinya dari bukti.
5. Langkah kebangkitan tanpa bukti hanya boleh tampil dengan label **"saran"**. Perintah shell di dalamnya ditampilkan sebagai teks dan **tidak pernah dijalankan**.
6. Hipotesis penyebab "kematian" diberi label hipotesis dan tingkat keyakinan, bukan dinyatakan sebagai fakta.

## 10. Keamanan dan ancaman

| Ancaman | Mitigasi |
| --- | --- |
| `.git/config` berbahaya (`fsmonitor`, `diff.external`, `core.pager`) mengeksekusi perintah | Bare clone sementara (konfigurasi tidak ikut), `--no-ext-diff --no-textconv`, tanpa shell, uji dengan skrip kenari |
| Prompt injection lewat README atau pesan commit | Teks repo dikirim sebagai data, bukan instruksi; keluaran dibatasi skema; validator grounding membuang klaim yang tidak berdasar |
| Escape terminal atau karakter bidi di nama file atau commit | Escape sebelum cetak |
| Repo raksasa atau file biner menghabiskan memori | Batas commit, batas ukuran file, lewati biner |
| Model mengarang fakta | Grounding wajib, kode mengisi tanggal dan angka, klaim tak berdasar dibuang dan dihitung |
| Kebocoran data keluar mesin | Hanya loopback, tanpa telemetri |

**Batas yang jujur.** Prompt injection tidak bisa dihilangkan sepenuhnya. Teks README yang menyesatkan masih bisa memengaruhi prosa yang *lolos* validasi karena ia benar-benar ada di repo. Karena itu semua laporan diberi catatan: *dihasilkan model dari teks repositori, verifikasi sebelum dipercaya*.

## 11. Strategi pengujian

- **Repo fixture sintetis** dibuat oleh skrip (`git init` dengan tanggal dan penulis tetap sehingga hash reproduksibel): repo mati normal, repo tanpa manifest, repo dengan commit sangat banyak, repo dengan file biner dan non-UTF-8, repo dengan simlink dan submodule.
- **Repo berbahaya:** konfigurasi dengan kenari (fsmonitor, diff.external, pager), README berisi prompt injection, pesan commit berisi escape ANSI.
- **Tes unit:** pembangkit ID bukti, anggaran konteks, validator grounding (ID palsu, kutipan palsu, kutipan benar, klaim tanpa ID), retrieval, parser JSON ketat.
- **Tes black-box:** CLI dijalankan sebagai subprocess terhadap Ollama palsu, memeriksa kode keluar, keluaran, dan bahwa repo target tidak berubah (snapshot hash sebelum dan sesudah).
- **Ollama palsu yang berbohong:** versi yang sengaja mengembalikan klaim tanpa ID, ID palsu, kutipan palsu, dan JSON rusak, untuk membuktikan fail-closed.
- **Pengujian model asli** (`qwen3:4b`): 2 hingga 3 repo nyata (satu repo milikmu sendiri yang sudah ditinggalkan, satu repo publik berlisensi jelas, satu fixture). Dari laporan nyata, ambil sampel **30 klaim**, periksa manual kebenarannya, lalu laporkan angka grounded dan akurat apa adanya.
- **Uji kualitas `warnet`:** 5 sampel jawaban; jika mayoritas tidak meyakinkan, fitur dikeluarkan dari MVP.
- **Uji offline:** hanya diklaim jika alurnya dijalankan dengan jaringan terputus.
- **Artefak demo (wajib, bukan opsional):** juri tidak akan memasang Ollama dan Python untuk mencoba CLI. Karena itu repo harus memuat (a) satu rekaman terminal dalam bentuk GIF, (b) satu rekaman asciinema, (c) satu laporan Markdown nyata beserta repo targetnya di `demo/`, dan (d) daftar perintah persis untuk mereproduksinya. Ini bagian dari "Technical Execution" dan harus selesai 30 Oktober pagi.
- **Sesi agent:** simpan sesi kerja lewat DevRelay dan sematkan di artikel. Ini diminta halaman challenge ("Show your work"), dan sekaligus jalan termurah untuk kategori Best Use of Entire.
- **CI:** lint, typecheck, matriks Ubuntu dan Windows, coverage dengan ambang pada `grounding` dan `gitreader`, bandit, pip-audit, secret scan. Pangkas jika waktu habis; jangan pernah memangkas tes grounding.

## 12. Metrik keberhasilan

Target berikut adalah **hipotesis yang akan diukur**, bukan hasil:

| Metrik | Target awal | Cara ukur |
| --- | --- | --- |
| Klaim lolos grounding pada laporan nyata | tidak ada klaim akhir tanpa ID valid (100% secara konstruksi) | otomatis |
| Klaim yang ternyata akurat (sampel 30) | ditentukan setelah pengukuran pertama | manual |
| Eksekusi kode repo target | nol | tes kenari |
| Waktu laporan (≤2000 commit) | ≤120 detik | stopwatch pada laptop pengembangan |
| Perubahan pada repo target | nol | hash sebelum dan sesudah |
| Kesiapan submission | 100% checklist §19 terpenuhi | manual, 30 Oktober |

## 13. Rencana kerja (4 hari, bukan 5)

| Hari | Tanggal | Fokus | Keluaran |
| --- | --- | --- | --- |
| 1 | Sel 27 Okt | Bekukan PRD 0.2, pasang Python 3.12, skeleton repo, `gitreader` aman, fixture, `facts` | `seance facts` jalan, tes kenari lulus |
| 2 | Rab 28 Okt | ID bukti, anggaran konteks, retrieval, model client, skema laporan, **validator grounding**, Ollama palsu yang berbohong. **Mulai kerangka artikel (Inggris).** | `report` jalan dengan model palsu, run pertama dengan model asli |
| 3 | Kam 29 Okt | Mode `ask`, nada `spooky`, renderer, `--output`, CI hijau, ukur 30 klaim, rekam GIF + asciinema | P0–P1 selesai, angka nyata masuk artikel |
| 4 | Jum 30 Okt | Selesaikan artikel, demo, README, dokumen bukti, cek checklist §19. **Terbit 21:00 WIB.** | Artikel terbit, submission selesai |
| Cadangan | Sab 31 Okt | Hanya perbaikan kecil tanpa commit fitur: typo, gambar, tautan. Tidak ada klaim baru. | — |

**Batas keras:** terbit 30 Oktober 21:00 WIB. Jika feed event benar (31 Okt 13:59 WIB), hari Cadangan hanya tersisa pagi. Jika Official Rules yang benar (1 Nov 13:59 WIB), buffer itu tetap tidak dipakai untuk fitur baru.

**Aturan pemotongan:** jika di akhir hari 3 `ask` belum teruji, `ask` dikeluarkan dan artikel memakai `report` saja. Artikel selalu didahulukan daripada fitur.

## 14. Risiko

| Risiko | Dampak | Mitigasi |
| --- | --- | --- |
| Aturan "proyek baru" ternyata ketat ("must be started and completed within the challenge window") | Diskualifikasi | Tulis 100% kode baru; **jangan** memakai ulang kode TidyMind sekalipun disebut terbuka; README menyatakan repo dibuat 27 Oktober 2026; catat commit setelah deadline jika ada |
| Artikel tidak berbahasa Inggris | Tidak layak hadiah | Tulis artikel langsung dalam bahasa Inggris sejak hari 2; PRD tetap Indonesia |
| Feed event dan halaman challenge berbeda satu hari | Submission terlambat | Terbit 30 Oktober 21:00 WIB, bukan 31 Oktober |
| Juri tidak dapat menjalankan CLI lokal + Ollama | Eksekusi teknis tidak terbukti | GIF, asciinema, laporan contoh yang di-commit, dan perintah reproduksi |
| Model 4B menghasilkan JSON dengan id ganda atau format salah | Laporan gagal | Skema ketat, retry dengan variasi sampling, fail-closed |
| Konteks terpotong diam-diam | Laporan salah tanpa tanda | `num_ctx` eksplisit dan anggaran bukti, diuji dengan repo besar |
| Nada `warnet` tidak meyakinkan | Fitur jelek | Uji 5 sampel, buang jika gagal (P3, aman untuk dipotong) |
| Waktu menulis artikel terlalu sempit | Kualitas tulisan turun (bobot terbesar) | Kerangka mulai hari 2, angka nyata mengalir hari 3, artikel bukan pekerjaan hari terakhir |
| Repo target tidak boleh dianalisis | Masalah etika atau lisensi | Pakai repo milik sendiri atau berlisensi jelas; jangan analisis repo pribadi orang lain |
| Hasil model asli lebih buruk dari harapan | Tidak ada cerita sukses | Laporkan jujur, jadikan bagian "What went wrong" |
| Hadiah tunai butuh W-9 / Federal Tax ID untuk non-AS | Hadiah sulit dicairkan | Tidak menghalangi submission; siapkan sejak menang diumumkan |

## 15. Pemetaan ke kriteria penilaian dan kategori partner

- **Kualitas tulisan:** cerita tunggal yang jelas, angka nyata, kegagalan dilaporkan jujur.
- **Relevansi tema:** menghidupkan kembali alat yang ditinggalkan, bertema arwah.
- **Kreativitas:** repo sebagai arwah yang bisa ditanyai, dengan pagar bukti.
- **Eksekusi teknis:** pembacaan git aman, grounding yang diverifikasi kode, pengujian, artefak demo.
- **Kategori partner:** opt-in dilakukan dengan **menggunakan teknologi partner dan menuliskannya di bagian Prize Categories pada post**. Hanya klaim yang benar-benar dipakai.

| Kategori | Status | Alasan |
| --- | --- | --- |
| Best Use of Entire ($100) | **Ya** | Sesi agent disematkan di artikel; deskripsi kategori memang "share the agent sessions behind your project in the write-up". Tidak menambah kode. |
| Best Use of Gemma ($200) | **Hanya jika P3 sempat** | Tukar model ke `gemma3:4b` di Ollama dan bandingkan tingkat klaim yang lolos grounding. Ini sekaligus bukti terkuat bahwa model bisa ditukar. |
| Kategori lain | Tidak | Tidak dipakai, dan klaim palsu merusak kredibilitas. |

## 16. Kerangka artikel DEV (bahasa Inggris)

Ikuti template halaman challenge, dengan heading persis seperti template:

1. **What I Built** — CLI lokal yang membedah repo mati dan membiarkan kamu bertanya kepadanya; satu contoh nyata dari repo sungguhan.
2. **How I interpreted the theme** — arwah = riwayat commit yang tidak lagi dibaca siapa pun; séance = pertanyaan ke masa lalu proyek. Pakai satu kalimat dari ide resmi challenge.
3. **Demo** — GIF terminal nyata, keluaran `report` dan `ask`, dan bagian yang klaimnya dibuang validator.
4. **Code** — tautan repo publik + lisensi MIT.
5. **How I Built It** — "model speaks, code verifies"; ID bukti; pembacaan git yang aman (bare clone, tanpa eksekusi); hasil sampel 30 klaim dengan angka apa adanya.
6. **Why Does Open Innovation Matter?** — riwayat git tidak keluar dari mesin; model bisa diganti (tunjukkan `qwen3:4b` → `gemma3:4b` jika ada); tanpa biaya per permintaan; bisa jalan tanpa internet.
7. **My Agent Session** — sematkan sesi DevRelay.
8. **Prize Categories** — sebut eksplisit: Best Use of Entire, dan Best Use of Gemma hanya jika benar-benar dijalankan.
9. **Limitations / What went wrong** — apa yang tidak terbukti.

Aturan penulisan: bahasa Inggris, tag `#devchallenge` dan `#hf26challenge`, sebutkan bahwa repo dibuat di dalam window challenge, dan jangan mengklaim apa pun yang tidak diukur.

## 17. Keputusan

**Sudah ditutup:**

1. Nama final dan perintah: `seance`.
2. Repo target demo: repo milik sendiri yang sudah ditinggalkan (aman secara etika dan lisensi), ditambah satu repo publik berlisensi jelas.
3. Nada `warnet`: P3. Hanya dikerjakan jika P0–P1 selesai 29 Oktober.
4. Gemma: P3, dan hanya diklaim sebagai kategori jika benar-benar dijalankan.
5. Kode dari TidyMind: **tidak dipakai sama sekali.** PRD ini tidak mengadaptasi kode proyek sebelumnya.
6. Tim: solo.
7. Lisensi repo: MIT.
8. Bahasa artikel: Inggris.

**Masih terbuka:**

1. Repo publik mana yang dipakai sebagai contoh kedua di artikel.
2. Apakah `spooky` cukup kuat untuk demo, atau `plain` lebih meyakinkan.

## 18. Definition of Done

- P0 selesai dan lolos semua tes, termasuk tes kenari dan tes Ollama yang berbohong.
- Repo publik, berlisensi MIT, dengan README yang menyatakan proyek dibuat 27–30 Oktober 2026 di dalam window challenge; commit setelah deadline (jika ada) dicatat.
- Artefak demo lengkap: GIF, asciinema, laporan contoh di `demo/`, perintah reproduksi.
- Pengujian model asli dicatat dengan angka nyata dan batasannya, termasuk sampel 30 klaim.
- README dan dokumen bukti tidak mengklaim apa pun yang belum dibuktikan.
- Artikel berbahasa Inggris terbit sebelum 30 Oktober 21:00 WIB dengan tag `#devchallenge` dan `#hf26challenge`, memuat bagian "Why Does Open Innovation Matter?", dan menyebut kategori partner yang diklaim.
- Sesi agent DevRelay tersimpan dan tersemat di artikel.

## 19. Checklist kepatuhan (jalankan 30 Oktober sebelum terbit)

| # | Syarat | Bukti |
| --- | --- | --- |
| 1 | Repo dimulai dan selesai di dalam window challenge | Tanggal commit pertama 27 Okt 2026, tidak ada kode lama |
| 2 | Tidak ada kode dari proyek sebelumnya | Riwayat git publik, tidak ada yang disalin dari TidyMind |
| 3 | Model open-weight / inferensi lokal sebagai inti | Ollama + `qwen3:4b` (Apache-2.0), bukan panggilan API cloud |
| 4 | Artikel berbahasa Inggris | Seluruh badan post |
| 5 | Tag `#devchallenge` dan `#hf26challenge` | Tag post |
| 6 | Menjelaskan mengapa open innovation penting | Bagian khusus di artikel |
| 7 | Demo terlihat tanpa instalasi | GIF + asciinema + laporan contoh |
| 8 | Kode publik dan berlisensi | Tautan repo + MIT |
| 9 | Kategori partner ditulis eksplisit | Bagian Prize Categories |
| 10 | Bebas plagiarisme / kredit pihak ketiga | Tidak ada kode pihak ketiga non-trivial; kredit jika ada |
| 11 | Commit setelah 30/31 Okt dicatat di README | Satu baris "Post-deadline changes" |
| 12 | Akun DEV aktif, peserta 18+, Indonesia tidak dikecualikan | Profil DEV |

**Sumber aturan:** halaman Hacktoberfest Open-Source AI Challenge: Week 4 (`dev.to/challenges/hacktoberfest-week4-2026-10-26`), including FAQ "Can I work on an old project?", "Do submissions have to be in English?", "Can my submission include open source code?"; DEV Community Official Challenges and Hackathon Rules (`dev.to/page/official-hackathon-rules`); feed `hacktoberfest-api.mlh.com/api/events` untuk `ends_at`.
