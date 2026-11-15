"""Independent DEX Screener enrichment for FOMO trending contracts.

Public data only. Missing values remain null; never imply security verification.
"""
import datetime
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

INPUT = Path("data/trending.json")
OUTPUT = Path("data/dex_enrichment.json")
API = "https://api.dexscreener.com/token-pairs/v1"
NETWORKS = {1399811149: "solana", 56: "bsc", 1: "ethereum", 8453: "base"}

def get_pairs(chain, address):
    url = f"{API}/{chain}/{urllib.parse.quote(address, safe='')}"
    req = urllib.request.Request(url, headers={"User-Agent": "fomo-radar/1.1", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=18) as response:
        data = json.load(response)
    return data if isinstance(data, list) else []

def number(value):
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None

def matching_pair(pair, chain, address):
    return (str(pair.get("chainId", "")).lower() == chain
            and str((pair.get("baseToken") or {}).get("address", "")).lower() == address.lower())

def enrich(token, checked_at):
    address = token.get("address")
    chain = NETWORKS.get(token.get("network"))
    row = {"rank": token.get("rank"), "symbol": token.get("symbol"),
           "network": token.get("network"), "chain": chain, "address": address,
           "checkedAt": checked_at, "status": "unavailable",
           "liquidityUsd": None, "volume5mUsd": None, "volume1hUsd": None,
           "priceChange5mPct": None, "priceChange1hPct": None,
           "buys5m": None, "sells5m": None, "buys1h": None, "sells1h": None,
           "pairAddress": None, "dexUrl": None, "pairCreatedAt": None,
           "holderConcentration": None, "creatorActivity": None,
           "washTradingRisk": "not_assessed", "rugPullRisk": "not_assessed"}
    if not chain or not address:
        row["status"] = "unsupported_network_or_missing_address"
        return row
    try:
        pairs = [p for p in get_pairs(chain, address) if matching_pair(p, chain, address)]
        if not pairs:
            row["status"] = "no_matching_base_token_pair"
            return row
        # Choose the deepest matching pool; other pools may also matter.
        pair = max(pairs, key=lambda p: number((p.get("liquidity") or {}).get("usd")) or 0)
        volume, change, tx = pair.get("volume") or {}, pair.get("priceChange") or {}, pair.get("txns") or {}
        row.update({"status": "ok", "liquidityUsd": number((pair.get("liquidity") or {}).get("usd")),
                    "volume5mUsd": number(volume.get("m5")), "volume1hUsd": number(volume.get("h1")),
                    "priceChange5mPct": number(change.get("m5")), "priceChange1hPct": number(change.get("h1")),
                    "buys5m": (tx.get("m5") or {}).get("buys"), "sells5m": (tx.get("m5") or {}).get("sells"),
                    "buys1h": (tx.get("h1") or {}).get("buys"), "sells1h": (tx.get("h1") or {}).get("sells"),
                    "pairAddress": pair.get("pairAddress"), "dexUrl": pair.get("url"),
                    "pairCreatedAt": pair.get("pairCreatedAt"), "matchingPairs": len(pairs)})
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        row["status"] = "fetch_error"
        row["errorType"] = type(exc).__name__
    return row

def main():
    snapshot = json.loads(INPUT.read_text(encoding="utf-8"))
    checked_at = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    rows = []
    for token in snapshot.get("tokens", [])[:25]:
        rows.append(enrich(token, checked_at))
        time.sleep(0.25)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps({
        "checkedAt": checked_at, "fomoPolledAt": snapshot.get("polledAt"),
        "fomoCapturedAt": snapshot.get("capturedAt"),
        "source": "DEX Screener public token-pairs API",
        "warning": "Pool data is third-party and time-sensitive. Largest matching base-token pool only. No wallet analysis, wash trading detection, rug audit, or endorsement.",
        "tokens": rows
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"DEX enrichment: {sum(x['status']=='ok' for x in rows)}/{len(rows)} matched")

if __name__ == "__main__":
    main()
