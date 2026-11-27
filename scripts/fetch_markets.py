import json, urllib.request, urllib.parse, datetime

SYMBOLS = [
    ("EURTRY=X", "fx"),
    ("EURUSD=X", "eurusd"),
    ("GC=F",     "gold"),
    ("SI=F",     "silver"),
    ("BTC-USD",  "btc"),
    ("ETH-USD",  "eth"),
    ("SOL-USD",  "sol"),
    ("^GSPC",    "gspc"),
    ("XU100.IS", "bist"),
    ("VGWD.DE",  "vgwd"),
    ("SPCX",     "spcx"),
    ("ANT",      "ant"),
    ("^TNX",     "us10y"),
    ("IEF",      "ief"),
    ("EUNH.DE",  "eunh"),
    ("CBON",     "cbon"),
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
            if len(closes) >= 2 and price:
                prev_day = closes[-2]
                pct = ((price - prev_day) / prev_day) * 100
            else:
                prev = meta.get("chartPreviousClose") or meta.get("previousClose")
                pct = ((price - prev) / prev) * 100 if (price and prev) else None
            rsi = calc_rsi(closes, 14)
            sig = {
                "s": signal_from_sma(price, closes, 20, 0.012, rsi),
                "m": signal_from_sma(price, closes, 60, 0.020),
                "l": signal_from_sma(price, closes, 200, 0.030),
            }
            out[sym] = {"price": price, "pct": pct, "currency": meta.get("currency"), "sig": sig}
    except Exception as e:
        print("WARN", sym, e)

# Also fetch official ECB 10Y AAA Eurozone yield
try:
    req = urllib.request.Request(
        "https://data-api.ecb.europa.eu/service/data/YC/B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y?lastNObservations=2&format=jsondata",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        d = json.loads(r.read().decode())
        obs = d["dataSets"][0]["series"]["0:0:0:0:0:0:0"]["observations"]
        vals = [v[0] for v in obs.values()]
        if vals:
            out["EU10Y"] = {"price": vals[-1]}
except Exception as e:
    print("WARN_ECB", e)

with open("app/markets.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("WROTE app/markets.json:", len(out), "entries")

# Fetch official FotMob season leaders + studio cutout portraits
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
