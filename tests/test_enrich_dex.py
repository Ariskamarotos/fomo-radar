import unittest
from unittest.mock import patch
from scripts.enrich_dex import enrich, matching_pair

TOKEN = {"rank": 1, "symbol": "TEST", "network": 1399811149, "address": "SoLTest"}
PAIR = {"chainId": "solana", "baseToken": {"address": "SoLTest"},
        "pairAddress": "pool1", "url": "https://dexscreener.com/solana/pool1",
        "liquidity": {"usd": 35000}, "volume": {"m5": 5000, "h1": 18000},
        "priceChange": {"m5": 2.5, "h1": 11.2},
        "txns": {"m5": {"buys": 23, "sells": 10}, "h1": {"buys": 85, "sells": 42}}}

class TestEnrichment(unittest.TestCase):
    def test_contract_match_not_symbol(self):
        self.assertTrue(matching_pair(PAIR, "solana", "SoLTest"))
        self.assertFalse(matching_pair(PAIR, "solana", "OtherContract"))
    @patch("scripts.enrich_dex.get_pairs", return_value=[PAIR])
    def test_metrics(self, _):
        result = enrich(TOKEN, "2026-11-15T20:00:00Z")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["liquidityUsd"], 35000)
        self.assertEqual(result["volume5mUsd"], 5000)
        self.assertEqual(result["priceChange1hPct"], 11.2)
        self.assertEqual(result["washTradingRisk"], "not_assessed")
    @patch("scripts.enrich_dex.get_pairs", return_value=[])
    def test_missing_pair_is_not_zero_liquidity(self, _):
        result = enrich(TOKEN, "2026-11-15T20:00:00Z")
        self.assertIsNone(result["liquidityUsd"])
        self.assertEqual(result["status"], "no_matching_base_token_pair")

if __name__ == "__main__":
    unittest.main()
