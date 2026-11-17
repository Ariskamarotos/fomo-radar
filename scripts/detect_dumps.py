"""Contract-specific drawdown warnings; heuristic, not a rug-pull verdict."""
import json
from pathlib import Path

PATH = Path("data/dex_enrichment.json")
STATE = Path("data/dex_risk_state.json")

def key(row):
    chain = str(row.get("chain") or "").lower()
    address = str(row.get("address") or "").lower()
    return (chain, address) if chain and address else None

def assess(row, prior):
    result = dict(row)
    result.update(observedPeakPriceUsd=None, drawdownFromObservedPeakPct=None,
                  liquidityChangePct=None, rapidDumpWarning=False,
                  liquidityDropWarning=False, riskWarningReasons=[])
    if row.get("status") != "ok":
        return result
    price = row.get("priceUsd")
    liq = row.get("liquidityUsd")
    prev = prior or {}
    peaks = [x for x in (price, prev.get("peak"), prev.get("price")) if isinstance(x, (int, float)) and x > 0]
    peak = max(peaks) if peaks else None
    result["observedPeakPriceUsd"] = peak
    if peak and isinstance(price, (int, float)):
        result["drawdownFromObservedPeakPct"] = round(100 * (price / peak - 1), 2)
    old_liq = prev.get("liquidity")
    if isinstance(old_liq, (int, float)) and old_liq > 0 and isinstance(liq, (int, float)):
        result["liquidityChangePct"] = round(100 * (liq / old_liq - 1), 2)
    reasons = []
    if isinstance(row.get("priceChange5mPct"), (int, float)) and row["priceChange5mPct"] <= -20:
        reasons.append("five_minute_drop")
    if isinstance(row.get("priceChange1hPct"), (int, float)) and row["priceChange1hPct"] <= -35:
        reasons.append("hourly_drop")
    if result["drawdownFromObservedPeakPct"] is not None and result["drawdownFromObservedPeakPct"] <= -50:
        reasons.append("observed_peak_drawdown")
    if result["liquidityChangePct"] is not None and result["liquidityChangePct"] <= -40:
        reasons.append("liquidity_drop")
    result["rapidDumpWarning"] = any(x != "liquidity_drop" for x in reasons)
    result["liquidityDropWarning"] = "liquidity_drop" in reasons
    result["riskWarningReasons"] = reasons
    return result

def main():
    data = json.loads(PATH.read_text(encoding="utf-8"))
    old = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    prior = old.get("contracts", {})
    current = dict(prior)
    rows = []
    for row in data.get("tokens", []):
        k = key(row)
        stored = prior.get("|".join(k)) if k else None
        assessed = assess(row, stored)
        rows.append(assessed)
        if k and row.get("status") == "ok":
            price = row.get("priceUsd")
            peak = assessed["observedPeakPriceUsd"]
            current["|".join(k)] = {
                "peak": peak, "price": price, "liquidity": row.get("liquidityUsd"),
                "checkedAt": row.get("checkedAt")
            }
    data["tokens"] = rows
    data["riskWarningNote"] = "Heuristic price/liquidity flags only; not independently verified rug pulls. Peak means highest observed sampled price, not exchange ATH."
    PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    STATE.write_text(json.dumps({"contracts": current}, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    main()
