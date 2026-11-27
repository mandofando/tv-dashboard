import json, urllib.request, urllib.parse, datetime

SYMBOLS = ["^GSPC", "XU100.IS", "VGWD.DE", "SPCX", "ANT"]
out = {"updated": datetime.datetime.now(datetime.timezone.utc).isoformat()}

for sym in SYMBOLS:
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?interval=1d&range=5d"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            meta = json.loads(r.read().decode())["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice")
            prev = meta.get("chartPreviousClose") or meta.get("previousClose")
            pct = ((price - prev) / prev) * 100 if (price and prev) else None
            out[sym] = {"price": price, "pct": pct, "currency": meta.get("currency")}
    except Exception as e:
        print("WARN", sym, e)

with open("app/markets.json", "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2)
print("WROTE app/markets.json:", out)

# Also fetch official FotMob season leaders (Top Scorer, Assists, FotMob Rating) + studio cutout portraits
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
print("WROTE app/leaders.json:", leaders)
