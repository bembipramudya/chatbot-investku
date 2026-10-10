# InvestKu — Asisten Edukasi Investasi

Chatbot edukasi investasi berbasis AI. Tanya jawab seputar saham, reksadana,
deposito, obligasi/SBN, emas, profil risiko, diversifikasi, dana darurat,
sampai ciri-ciri investasi bodong.

**Live:** https://chatbot-investku.vercel.app

## Use Case

Education bot untuk literasi investasi dan keuangan personal. Bukan aplikasi
trading, bukan penasihat keuangan — murni edukasi. Setiap jawaban ditutup
penegasan bahwa ini materi edukasi, bukan saran finansial.

## Cara Kerja AI

- **Model:** Groq `openai/gpt-oss-20b` via API. Kalau `GROQ_API_KEY` tidak diisi,
  otomatis pakai knowledge-base lokal (13 topik) sebagai mode demo.
- **Gaya bahasa otomatis:** formal, santai, atau sederhana — dideteksi dari cara
  pengguna mengetik, tanpa perlu diatur manual.
- **Mode otomatis:** tanya jawab, simulasi skenario keuangan, atau kuis —
  dipilih berdasarkan isi pertanyaan.
- **Batasan domain:** hanya melayani topik investasi, keuangan personal, dan
  pasar modal. Pertanyaan di luar itu ditolak sopan dan diarahkan kembali.
- **Memory:** 10 pesan terakhir dikirim sebagai konteks, riwayat tersimpan di
  localStorage browser.

## Grafik Saham

Di atas chat ada grafik candlestick interaktif (data real-time Yahoo Finance):

- 40 emiten likuid Indonesia + IHSG
- Periode 1D, 5D, 1M, 3M, 6M, 1Y
- MA5, MA20, volume, info Buka/Tertinggi/Terendah/Volume
- Bisa di-tap untuk lihat detail tiap candle, digeser untuk pan, dicubit untuk zoom

Ticker berjalan di bagian atas menampilkan 12 saham Indonesia.

## Struktur

```
chatbot-investku/
├── investku_app.py      # backend Flask
├── templates/
│   └── index.html       # seluruh UI (chat + grafik + ticker)
├── requirements.txt
├── .env.example
└── README.md
```

Endpoint backend:

| Endpoint | Fungsi |
|---|---|
| `GET /` | halaman utama |
| `POST /api/chat` | kirim pesan, terima jawaban AI |
| `GET /api/ticker` | 12 saham untuk ticker (cache 5 menit) |
| `GET /api/stocks` | daftar 40 emiten + IHSG |
| `GET /api/chart/<simbol>?p=<periode>` | data OHLC + MA buat grafik |
| `GET /api/health` | status server & model |

## Menjalankan Lokal

```bash
pip install -r requirements.txt
cp .env.example .env   # isi GROQ_API_KEY kalau ada (opsional)
python investku_app.py
# buka http://localhost:5000
```

## Deploy

Deploy production di Vercel dari repo ini. `GROQ_API_KEY` dipasang sebagai
environment variable di dashboard Vercel.

## Catatan

InvestKu memberi edukasi investasi umum, bukan saran finansial profesional.
Selalu lakukan riset mandiri dan konsultasikan ke perencana keuangan berlisensi
untuk keputusan nyata.
