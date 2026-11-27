import json, urllib.request, urllib.parse, datetime

# All 8 market tiles: fetch 1y daily closes to compute transparent technical trend signals
# Short (1M): SMA20 + RSI14 | Medium (3M): SMA50 | Long (1J): SMA200 (or max available for recent IPOs)
SYMBOLS = [
    ("EURTRY=X", "fx"),
    ("GC=F",     "gold"),
    ("BTC-USD",  "btc"),
    ("^GSPC",    "gspc"),
    ("XU100.IS", "bist"),
    ("VGWD.DE",  "vgwd"),
    ("SPCX",     "spcx"),
    ("ANT",      "ant"),
]

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(-period, 0)]
    gains = sum(d for d in deltas if d > 0) / period
    losses = sum(-d for d in deltas if d < 0) / period
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))

def signal_from_sma(price, closes, window, band=0.015, rsi=None):
    w = min(window, len(closes))
    if w < 5:
        return "H"
    sma = sum(closes[-w:]) / w
    diff = (price - sma) / sma
    if rsi is not None:
        if diff > band and rsi < 72:
            return "K"
        if diff < -band and rsi > 28:
            return "V"
        return "H"
    if diff > band:
        return "K"
    if diff < -band:
        return "V"
    return "H"

out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat()}

for sym, key in SYMBOLS:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?interval=1d&range=1y"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as r:
            res = json.loads(r.read().decode())["chart"]["result"][0]
            meta = res["meta"]
            closes = [c for c in res["indicators"]["quote"][0].get("close", []) if c is not None]
            price = meta.get("regularMarketPrice") or (closes[-1] if closes else None)
            prev = meta.get("chartPreviousClose") or meta.get("previousClose") or (closes[-2] if len(closes) >= 2 else None)
            # Use last two daily closes for 1-day % change when available
            if len(closes) >= 2 and price:
                prev_day = closes[-2]
                pct = ((price - prev_day) / prev_day) * 100
            else:
                pct = ((price - prev) / prev) * 100 if (price and prev) else None
            rsi = calc_rsi(closes, 14)
            sig = {
                "s": signal_from_sma(price, closes, 20, 0.012, rsi),   # 1M (Short)
                "m": signal_from_sma(price, closes, 60, 0.020),        # 3M (Medium)
                "l": signal_from_sma(price, closes, 200, 0.030),       # 1J (Long)
            }
            out[sym] = {"price": price, "pct": pct, "currency": meta.get("currency"), "sig": sig}
    except Exception as e:
        print("WARN", sym, e)

with open("app/markets.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("WROTE app/markets.json:", {k: (v.get("sig") if isinstance(v, dict) else v) for k, v in out.items()})

# Fetch official FotMob season leaders (Top Scorer, Assists, FotMob Rating) + studio cutout portraits
leaders = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat()}
for key, tid in [("gala", 8637), ("rbl", 178475)]:
    try:
        req = urllib.request.Request(
            f"https://www.fotmob.com/api/data/teams?id={tid}",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            d = json.loads(r.read().decode())
        picked = {}
        for p in (d.get("stats", {}).get("players") or []):
            hdr = p.get("header")
            top = (p.get("topThree") or [None])[0]
            if not top:
                continue
            if hdr in ("Top scorer", "Assists", "FotMob rating"):
                picked[hdr] = {
                    "name": top.get("name"),
                    "value": top.get("value"),
                    "img": f"https://images.fotmob.com/image_resources/playerimages/{top.get('id')}.png"
                }
        leaders[key] = picked
    except Exception as e:
        print("WARN_FOTMOB", key, e)

with open("app/leaders.json", "w", encoding="utf-8") as f:
    json.dump(leaders, f, indent=2, ensure_ascii=False)
print("WROTE app/leaders.json")
