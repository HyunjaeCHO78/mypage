import unittest

from src.services.execution_score_engine import ExecutionIntradayState, ExecutionScoreEngine


class ExecutionScoreEngineTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = ExecutionScoreEngine()

    def test_intraday_payload_applies_positive_signals(self) -> None:
        payload = {
            "market_phase": "intraday",
            "ticker": "A00001",
            "execution_score": 52,
            "features": {
                "breakout_detected": True,
                "trading_value_spike": True,
                "trade_strength_change": 129.0,
                "leader_follower_alignment_hint": "aligned",
            },
        }

        state = self.engine.apply_intraday_payload(payload)

        self.assertEqual(state.execution_score, 52)
        self.assertEqual(state.execution_intraday_score, 87)
        self.assertEqual(state.intraday_classification, "실행검토")
        self.assertTrue(any("breakout_detected" in r for r in state.score_change_reasons))

    def test_intraday_payload_applies_negative_signals(self) -> None:
        previous = ExecutionIntradayState(
            ticker="A00002",
            execution_score=50,
            execution_intraday_score=50,
        )
        payload = {
            "market_phase": "intraday",
            "ticker": "A00002",
            "features": {
                "breakout_detected": False,
                "trading_value_spike": False,
                "trade_strength_change": 80.0,
                "leader_follower_alignment_hint": "lagging",
            },
        }

        state = self.engine.apply_intraday_payload(payload, previous=previous)

        self.assertEqual(state.execution_intraday_score, 38)
        self.assertEqual(state.intraday_classification, "관찰")
        self.assertTrue(any("lagging" in r for r in state.score_change_reasons))

    def test_duplicate_intraday_payload_is_ignored(self) -> None:
        payload = {
            "market_phase": "intraday",
            "ticker": "A00003",
            "execution_score": 40,
            "features": {
                "breakout_detected": True,
                "trading_value_spike": False,
                "trade_strength_change": 121.0,
                "leader_follower_alignment_hint": "aligned",
            },
        }

        state = self.engine.apply_intraday_payload(payload)
        updated = self.engine.apply_intraday_payload(payload, previous=state)

        self.assertEqual(updated.execution_intraday_score, state.execution_intraday_score)
        self.assertEqual(len(updated.intraday_event_history), 1)


if __name__ == "__main__":
    unittest.main()
