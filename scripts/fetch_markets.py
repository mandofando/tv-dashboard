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
