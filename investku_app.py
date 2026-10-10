# InvestKu - chatbot edukasi investasi
# Backend Flask: ngobrol via Groq, grafik & ticker via Yahoo Finance.
# Kalau GROQ_API_KEY kosong, otomatis pakai knowledge-base lokal.

import os
import re
import json
import time
import urllib.request
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b").strip()
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

UA = {"User-Agent": "InvestKu/1.0 (chatbot-investku.vercel.app)"}

STYLE_PROMPTS = {
    "formal": (
        "Kamu adalah InvestKu, asisten edukasi investasi. Jawablah dengan gaya bahasa "
        "FORMAL dan baku seperti penjelasan akademis: definisi singkat, konsep kunci "
        "(risiko, return, diversifikasi), lalu penjelasan. Tetap ringkas."
    ),
    "santai": (
        "Kamu adalah InvestKu, asisten edukasi investasi. Jawablah dengan gaya SANTAI "
        "seperti ngobrol dengan teman, tapi tetap akurat. Boleh pakai analogi "
        "sehari-hari, istilah finansial dijelaskan dulu artinya."
    ),
    "sederhana": (
        "Kamu adalah InvestKu, asisten edukasi investasi. Jelaskan dengan bahasa "
        "SEDERHANA: kalimat pendek, contoh konkret sehari-hari, hindari istilah "
        "finansial tanpa penjelasan."
    ),
}

MODE_PROMPTS = {
    "tanya": "Mode TANYA JAWAB: jawab pertanyaan seputar investasi secara langsung dan jelas.",
    "simulasi": (
        "Mode SIMULASI: analisis skenario investasi pengguna: 1) profil risikonya, "
        "2) instrumen yang cocok, 3) langkah praktis. Akhiri dengan ringkasan edukatif."
    ),
    "kuis": (
        "Mode KUIS: uji pemahaman dengan 1 pertanyaan pilihan ganda tentang investasi "
        "dan pasar modal Indonesia per giliran. Tunggu jawaban, lalu koreksi dan jelaskan."
    ),
}

DISCLAIMER = (
    "\n\nCatatan: ini materi edukasi, bukan saran finansial. "
    "Selalu lakukan riset mandiri dan konsultasikan dengan perencana keuangan "
    "berlisensi sebelum berinvestasi."
)

# knowledge-base lokal, dipakai kalau Groq tidak tersedia
KB = [
    (["apa itu investasi", "definisi investasi", "investasi itu apa"],
     "**Investasi** adalah menempatkan uang pada suatu aset dengan harapan nilainya **bertumbuh**. "
     "Beda dengan menabung (uang diam, tergerus inflasi) — investasi bertujuan mengalahkan inflasi. "
     "Kuncinya: pahami risikonya sebelum mulai."),
    (["saham", "beli saham", "main saham"],
     "**Saham** adalah bukti kepemilikan sebagian kecil perusahaan. Beli saham = jadi pemilik kecil "
     "perusahaan itu. Untung dari: kenaikan harga (capital gain) + dividen. Risiko: harga bisa turun, "
     "bahkan rugi besar. Cocok untuk jangka **panjang (5+ tahun)** dan profil risiko agresif. "
     "Mulai dari Rp100 ribu via aplikasi sekuritas yang terdaftar OJK."),
    (["reksadana", "reksa dana"],
     "**Reksadana** adalah wadah menghimpun dana banyak orang yang dikelola **manajer investasi** "
     "profesional. Modal kecil (Rp10-100 ribu), diversifikasi otomatis, tidak perlu pantau pasar tiap hari. "
     "Jenisnya: pasar uang (paling aman), pendapatan tetap, campuran, saham (paling agresif)."),
    (["deposito"],
     "**Deposito** adalah simpanan berjangka di bank dengan bunga lebih tinggi dari tabungan biasa. "
     "Dana dikunci 1-24 bulan. Dijamin LPS sampai Rp2 miliar per bank. Risiko hampir nol, "
     "tapi return kecil — sering kalah dari inflasi. Cocok untuk dana jangka pendek."),
    (["obligasi", "sbn", "surat berharga"],
     "**Obligasi** adalah surat utang — kamu meminjamkan uang ke perusahaan/negara dan dapat bunga (kupon). "
     "**SBN (Surat Berharga Negara)** seperti ORI & Sukuk Ritel bisa dibeli mulai Rp1 juta, dijamin negara. "
     "Risiko rendah-menengah, cocok untuk profil konservatif-moderat."),
    (["emas", "logam mulia", "nabung emas"],
     "**Emas** adalah aset lindung nilai (safe haven) — nilainya cenderung naik saat ekonomi tidak pasti. "
     "Bisa beli fisik (Antam/UBS) atau digital (Rp10 ribu pun bisa). Kekurangan: tidak menghasilkan "
     "dividen/bunga, ada spread jual-beli. Cocok sebagai 5-10% portofolio."),
    (["profil risiko", "risiko investasi", "konservatif", "moderat", "agresif"],
     "**Profil risiko** menentukan instrumen yang cocok: **Konservatif** (tidak tahan rugi -> deposito, "
     "reksadana pasar uang, SBN), **Moderat** (tahan fluktuasi sedang -> reksadana campuran), "
     "**Agresif** (siap rugi besar demi cuan besar -> saham, crypto). Kenali dulu profilmu!"),
    (["diversifikasi", "jangan taruh telur"],
     "**Diversifikasi** = jangan taruh semua uang di satu aset. Bagi ke beberapa instrumen agar kalau "
     "satu rugi, yang lain menutupi. Contoh: 40% reksadana pasar uang + 30% SBN + 20% saham + 10% emas."),
    (["dana darurat", "emergency fund"],
     "**Dana darurat WAJIB sebelum investasi!** Idealnya 3-6x pengeluaran bulanan (lajang), "
     "6-12x (berkeluarga), disimpan di tempat likuid. Investasi pakai uang dingin — jangan pakai "
     "uang kebutuhan pokok atau utang."),
    (["investasi bodong", "ciri investasi bodong", "penipuan investasi", "skema ponzi"],
     "Ciri **investasi bodong**: janji return **pasti & tidak masuk akal** (mis. 10% per bulan), "
     "harus rekrut member baru (skema ponzi), tidak terdaftar OJK. Cek legalitas di **ojk.go.id** "
     "atau hubungi **OJK 157**. Ingat: tidak ada investasi yang pasti untung."),
    (["crypto", "bitcoin", "aset kripto"],
     "**Aset kripto** sangat **volatil** — bisa naik/turun puluhan persen dalam sehari. Di Indonesia "
     "diawasi Bappebti. Aturan main: maksimal 5% portofolio, pakai uang dingin, pahami teknologinya dulu."),
    (["mulai investasi", "modal kecil", "mulai dari mana", "100 ribu"],
     "Mulai investasi modal kecil: 1) Siapkan **dana darurat** dulu, 2) Tentukan **tujuan & jangka waktu**, "
     "3) Kenali **profil risikomu**, 4) Mulai dari yang aman: **reksadana pasar uang** (Rp10-100 ribu), "
     "5) Naik level bertahap sambil belajar. Konsisten > besar di awal."),
    (["inflasi"],
     "**Inflasi** adalah kenaikan harga barang dari waktu ke waktu — yang bikin nilai uangmu **menyusut**. "
     "Inilah alasan investasi: return harus **lebih besar dari inflasi** agar kekayaan bertumbuh nyata."),
]


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


def kb_answer(question):
    q = normalize(question)
    for keywords, answer in KB:
        if any(k in q for k in keywords):
            return answer
    return ("Aku belum punya materi spesifik tentang itu di mode demo. Coba tanya soal saham, "
            "reksadana, deposito, obligasi, emas, diversifikasi, atau dana darurat.")


def detect_style(question, history=None):
    texts = [question] + [m.get("content", "") for m in (history or [])[-4:]
             if m.get("role") == "user"]
    blob = " ".join(texts).lower()
    formal_mark = ["apakah", "bagaimana", "mohon", "terima kasih", "anda", "dapatkah"]
    santai_mark = ["gimana", "dong", "sih", "bro", "cuy", "wkwk", "banget", "gue", "gua"]
    if sum(1 for w in formal_mark if w in blob) >= 2:
        return "formal"
    if any(w in blob for w in santai_mark):
        return "santai"
    return "sederhana"


def detect_mode(question):
    q = question.lower()
    if any(w in q for w in ["kuis", "soal", "tes ", "ujian", "latihan soal"]):
        return "kuis"
    if any(w in q for w in ["kalau saya", "jika saya", "misal", "andaikan", "simulasi",
                            "punya uang", "gaji", "rp", "juta"]):
        return "simulasi"
    return "tanya"


def clean_markdown(text):
    # ubah tabel markdown jadi poin teks, buang heading
    lines, out = text.split("\n"), []
    for ln in lines:
        s = ln.strip()
        if re.match(r"^\|?[\s:\-|]+\|?$", s) and "|" in s:
            continue
        if s.startswith("|") and s.endswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            out.append("- " + " | ".join(c for c in cells if c))
            continue
        out.append(re.sub(r"^#{1,6}\s+", "", ln))
    return "\n".join(out).strip()


def groq_answer(history, style, mode, question, temperature=0.7, max_tokens=500):
    system = STYLE_PROMPTS.get(style, STYLE_PROMPTS["sederhana"])
    system += " " + MODE_PROMPTS.get(mode, MODE_PROMPTS["tanya"])
    system += (
        " Selalu jawab dalam Bahasa Indonesia. Jangan tambahkan disclaimer sendiri. "
        "BATASAN DOMAIN: kamu HANYA melayani topik investasi, keuangan personal, dan pasar modal. "
        "Pertanyaan di luar itu (politik, sejarah, hiburan, olahraga, dll) tolak sopan dalam "
        "1-2 kalimat dan arahkan kembali ke investasi. "
        "Jangan pakai tabel markdown (| --- |) atau heading (#/##). "
        "Sajikan sebagai teks biasa dengan baris baru dan poin-poin. Boleh pakai **tebal**."
    )
    messages = [{"role": "system", "content": system}]
    for m in history[-10:]:
        messages.append({"role": m["role"], "content": m["content"]})
    # frontend sudah push pesan user ke history, jadi cek dulu biar tidak dobel
    if not messages[1:] or messages[-1].get("content", "").strip() != question.strip():
        messages.append({"role": "user", "content": question})

    payload = {"model": GROQ_MODEL, "messages": messages,
               "temperature": temperature, "max_tokens": max_tokens}
    req = urllib.request.Request(
        GROQ_URL, data=json.dumps(payload).encode(),
        headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                 "Content-Type": "application/json", **UA},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode())
    text = clean_markdown(data["choices"][0]["message"]["content"].strip())
    if "bukan saran finansial" not in text:
        text += DISCLAIMER
    return text


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    question = (body.get("message") or "").strip()
    if not question:
        return jsonify({"error": "Pesan kosong."}), 400

    history = body.get("history") or []
    history = [{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:2000]}
               for m in history if isinstance(m, dict)][-10:]

    style = body.get("style") or detect_style(question, history)
    mode = body.get("mode") or detect_mode(question)
    try:
        temperature = max(0.0, min(1.0, float(body.get("temperature", 0.7))))
    except (TypeError, ValueError):
        temperature = 0.7
    try:
        max_tokens = max(50, min(2000, int(body.get("max_tokens", 500))))
    except (TypeError, ValueError):
        max_tokens = 500

    if GROQ_API_KEY:
        try:
            answer = groq_answer(history, style, mode, question, temperature, max_tokens)
            return jsonify({"answer": answer, "engine": "groq", "model": GROQ_MODEL})
        except Exception as e:
            detail = str(e)[:200]
            answer = kb_answer(question)
            return jsonify({"answer": answer + "\n\n_(AI tidak merespons, dialihkan ke mode demo.)_",
                            "engine": "demo-fallback", "warning": detail})
    return jsonify({"answer": kb_answer(question), "engine": "demo"})


@app.route("/api/health")
def health():
    return jsonify({"ok": True, "ai_mode": bool(GROQ_API_KEY), "model": GROQ_MODEL})


# --- data pasar dari Yahoo Finance ---

TICKER_SYMBOLS = ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "UNVR.JK", "INDF.JK",
                  "ANTM.JK", "ADRO.JK", "ICBP.JK", "KLBF.JK", "SMGR.JK", "ARTO.JK"]

# emiten likuid BEI + IHSG buat dropdown grafik
IDX_STOCKS = [
    ("BBCA", "Bank Central Asia"), ("BBRI", "Bank Rakyat Indonesia"),
    ("BMRI", "Bank Mandiri"), ("BBNI", "Bank Negara Indonesia"),
    ("BBTN", "Bank Tabungan Negara"), ("BRIS", "Bank Syariah Indonesia"),
    ("TLKM", "Telkom Indonesia"), ("EXCL", "XL Axiata"),
    ("ISAT", "Indosat"), ("ASII", "Astra International"),
    ("UNVR", "Unilever Indonesia"), ("INDF", "Indofood Sukses Makmur"),
    ("ICBP", "Indofood CBP"), ("KLBF", "Kalbe Farma"),
    ("SIDO", "Industri Jamu Sido Muncul"), ("SMGR", "Semen Indonesia"),
    ("INTP", "Indocement"), ("UNTR", "United Tractors"),
    ("ITMG", "Indo Tambangraya Megah"), ("ADRO", "Adaro Energy"),
    ("PTBA", "Bukit Asam"), ("INCO", "Vale Indonesia"),
    ("ANTM", "Aneka Tambang"), ("TINS", "Timah"),
    ("MDKA", "Merdeka Copper Gold"), ("BRPT", "Barito Pacific"),
    ("CPIN", "Charoen Pokphand"), ("JPFA", "Japfa Comfeed"),
    ("SMRA", "Summarecon Agung"), ("BSDE", "Bumi Serpong Damai"),
    ("PWON", "Pakuwon Jati"), ("CTRA", "Ciputra Development"),
    ("AKRA", "AKR Corporindo"), ("MAPI", "Mitra Adiperkasa"),
    ("ACES", "Ace Hardware"), ("SCMA", "Surya Citra Media"),
    ("EMTK", "Elang Mahkota Teknologi"), ("GOTO", "GoTo Gojek Tokopedia"),
    ("BUKA", "Bukalapak"), ("ARTO", "Bank Jago"),
    ("^JKSE", "IHSG (Indeks Harga Saham Gabungan)"),
]

_ticker_cache = {"at": 0, "data": []}


def yahoo_chart(symbol, rng, itv, timeout=15):
    req = urllib.request.Request(
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval={itv}&range={rng}",
        headers=UA, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())["chart"]["result"][0]


@app.route("/api/ticker")
def ticker():
    now = time.time()
    if now - _ticker_cache["at"] < 300 and _ticker_cache["data"]:
        return jsonify({"stocks": _ticker_cache["data"], "cached": True})
    out = []
    try:
        for sym in TICKER_SYMBOLS:
            meta = yahoo_chart(sym, "2d", "1d", timeout=10)["meta"]
            price = meta.get("regularMarketPrice") or 0
            prev = meta.get("chartPreviousClose") or price or 1
            chg = (price - prev) / prev * 100 if prev else 0
            out.append({"s": sym.replace(".JK", ""), "p": round(price), "c": round(chg, 2)})
    except Exception:
        pass
    if out:
        _ticker_cache.update({"at": now, "data": out})
        return jsonify({"stocks": out, "cached": False})
    if _ticker_cache["data"]:
        return jsonify({"stocks": _ticker_cache["data"], "cached": True})
    return jsonify({"stocks": [], "error": "gagal mengambil data"}), 502


@app.route("/api/stocks")
def stock_list():
    return jsonify({"stocks": [{"s": s, "n": n} for s, n in IDX_STOCKS]})


PERIODS = {
    "1d": ("1d", "15m", "%H:%M"), "5d": ("5d", "1h", "%H:%M"),
    "1mo": ("1mo", "1d", "%d %b"), "3mo": ("3mo", "1d", "%d %b"),
    "6mo": ("6mo", "1d", "%d %b"), "1y": ("1y", "1wk", "%b %y"),
}


def moving_avg(closes, n):
    return [None if i + 1 < n else round(sum(closes[i - n + 1:i + 1]) / n)
            for i in range(len(closes))]


@app.route("/api/chart/<symbol>")
def chart(symbol):
    sym = re.sub(r"[^A-Z0-9]", "", symbol.upper())
    if sym == "IHSG":
        sym = "^JKSE"  # karakter ^ bermasalah di URL, pakai alias
    ysym = sym if sym.startswith("^") else sym + ".JK"
    valid = [s if s.startswith("^") else s + ".JK" for s, _ in IDX_STOCKS]
    if ysym not in valid:
        return jsonify({"error": "simbol tidak dikenal"}), 404

    period = request.args.get("p", "1mo")
    rng, itv, fmt = PERIODS.get(period, PERIODS["1mo"])
    try:
        r = yahoo_chart(ysym, rng, itv)
        ts = r["timestamp"] or []
        q = r["indicators"]["quote"][0]
        points = []
        for i, t in enumerate(ts):
            o = q["open"][i]
            h = q["high"][i]
            l = q["low"][i]
            c = q["close"][i]
            v = q["volume"][i]
            if c is None:
                continue
            points.append({"d": time.strftime(fmt, time.gmtime(t)),
                           "o": round(o or c), "h": round(h or c),
                           "l": round(l or c), "c": round(c), "v": int(v or 0)})
        if len(points) < 2:
            return jsonify({"error": "data kurang"}), 502
        closes = [p["c"] for p in points]
        chg = (closes[-1] - closes[0]) / closes[0] * 100 if closes[0] else 0
        return jsonify({
            "symbol": sym, "points": points,
            "ma5": moving_avg(closes, 5), "ma20": moving_avg(closes, 20),
            "last": closes[-1], "change": round(chg, 2),
            "open": points[-1]["o"],
            "high": max(p["h"] for p in points[-5:]),
            "low": min(p["l"] for p in points[-5:]),
            "vol": points[-1]["v"], "period": period,
        })
    except Exception:
        return jsonify({"error": "gagal mengambil data"}), 502



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
