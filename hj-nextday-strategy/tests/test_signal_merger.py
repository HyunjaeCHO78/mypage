import unittest

from src.services.execution_score_engine import ExecutionIntradayState
from src.services.signal_merger import SignalMerger


class SignalMergerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.merger = SignalMerger()

    def test_intraday_merge_keeps_final_classification_and_adds_intraday_payload(self) -> None:
        board_item = {
            "ticker": "A00001",
            "final_classification": "관찰",
            "next_action": "관망",
        }
        intraday_state = ExecutionIntradayState(
            ticker="A00001",
            execution_score=52,
            execution_intraday_score=72,
            intraday_classification="실행검토",
            last_intraday_update_at="2026-04-21T09:12:00+00:00",
            score_change_reasons=["breakout_detected:+12"],
            intraday_event_history=[
                {"after": 60},
                {"after": 72},
            ],
        )

        merged = self.merger.merge_for_phase(board_item, "intraday", intraday_state)

        self.assertEqual(merged["final_classification"], "관찰")
        self.assertEqual(merged["intraday_classification"], "실행검토")
        self.assertIn("intraday_payload", merged)
        self.assertEqual(merged["intraday_payload"]["intraday_classification"]["status"], "changed")

    def test_post_close_merge_removes_intraday_fields(self) -> None:
        board_item = {
            "ticker": "A00002",
            "final_classification": "후보",
            "intraday_classification": "매수대기",
            "execution_intraday_score": 61,
            "intraday_payload": {"market_phase": "intraday"},
        }

        merged = self.merger.merge_for_phase(board_item, "post_close")

        self.assertEqual(merged["final_classification"], "후보")
        self.assertNotIn("intraday_classification", merged)
        self.assertNotIn("execution_intraday_score", merged)
        self.assertNotIn("intraday_payload", merged)

    def test_build_intraday_board_sorts_and_separates_intraday_rows(self) -> None:
        merged_items = [
            {
                "ticker": "A00003",
                "name": "샘플3",
                "industry": "수송",
                "role": "후발주",
                "intraday_classification": "관찰",
                "execution_intraday_score": 37,
                "intraday_updated_at": "2026-04-21T09:15:00+00:00",
                "intraday_payload": {
                    "intraday_classification": {
                        "status": "suppressed",
                        "change_reason": "trade_strength_change<=85:-8",
                        "previous_label": "관찰",
                        "label": "관찰",
                    },
                    "history": {
                        "recent_changes": [
                            {
                                "at": "2026-04-21T09:15:00+00:00",
                                "before": 45,
                                "after": 37,
                                "delta": -8,
                                "reasons": ["trade_strength_change<=85:-8"],
                                "features": {
                                    "trade_strength_change": 80.0,
                                    "leader_follower_alignment_hint": "lagging",
                                },
                            }
                        ],
                        "last_event": {
                            "features": {
                                "trade_strength_change": 80.0,
                                "leader_follower_alignment_hint": "lagging",
                            }
                        },
                    },
                },
            },
            {
                "ticker": "A00001",
                "name": "샘플1",
                "industry": "에너지",
                "role": "대표주",
                "intraday_classification": "실행검토",
                "execution_intraday_score": 74,
                "intraday_updated_at": "2026-04-21T09:16:00+00:00",
                "intraday_payload": {
                    "intraday_classification": {
                        "status": "changed",
                        "change_reason": "breakout_detected:+12",
                        "previous_label": "매수대기",
                        "label": "실행검토",
                    },
                    "history": {
                        "recent_changes": [
                            {
                                "at": "2026-04-21T09:16:00+00:00",
                                "before": 62,
                                "after": 74,
                                "delta": 12,
                                "reasons": ["breakout_detected:+12"],
                                "features": {
                                    "breakout_detected": True,
                                    "trade_strength_change": 132.0,
                                    "leader_follower_alignment_hint": "aligned",
                                },
                            }
                        ],
                        "last_event": {
                            "features": {
                                "breakout_detected": True,
                                "trade_strength_change": 132.0,
                                "leader_follower_alignment_hint": "aligned",
                            }
                        },
                    },
                },
            },
            {
                "ticker": "A00002",
                "name": "샘플2",
                "industry": "금융",
                "role": "대표주",
                "intraday_classification": "실행검토",
                "execution_intraday_score": 71,
                "intraday_updated_at": "2026-04-21T09:17:00+00:00",
                "intraday_payload": {
                    "intraday_classification": {
                        "status": "unchanged",
                        "change_reason": "trading_value_spike:+10",
                        "label": "실행검토",
                    },
                    "history": {
                        "recent_changes": [
                            {
                                "at": "2026-04-21T09:17:00+00:00",
                                "before": 61,
                                "after": 71,
                                "delta": 10,
                                "reasons": ["trading_value_spike:+10"],
                                "features": {
                                    "trading_value_spike": True,
                                    "trade_strength_change": 122.0,
                                    "leader_follower_alignment_hint": "aligned",
                                },
                            }
                        ]
                        ,
                        "last_event": {
                            "features": {
                                "trading_value_spike": True,
                                "trade_strength_change": 122.0,
                                "leader_follower_alignment_hint": "aligned",
                            }
                        },
                    },
                },
            },
            {
                "ticker": "A00004",
                "name": "샘플4",
                "industry": "반도체",
                "role": "후발주",
                "intraday_classification": "실행검토",
                "execution_intraday_score": 75,
                "intraday_updated_at": "2026-04-21T09:18:00+00:00",
                "intraday_payload": {
                    "intraday_classification": {
                        "status": "unchanged",
                        "change_reason": "leader_follower_alignment_hint=lagging:-4",
                        "label": "실행검토",
                    },
                    "history": {
                        "recent_changes": [
                            {
                                "at": "2026-04-21T09:18:00+00:00",
                                "before": 79,
                                "after": 75,
                                "delta": -4,
                                "reasons": ["leader_follower_alignment_hint=lagging:-4"],
                                "features": {
                                    "trade_strength_change": 84.0,
                                    "leader_follower_alignment_hint": "lagging",
                                },
                            }
                        ],
                        "last_event": {
                            "features": {
                                "trade_strength_change": 84.0,
                                "leader_follower_alignment_hint": "lagging",
                            }
                        },
                    },
                },
            },
        ]

        board = self.merger.build_intraday_board(merged_items, "intraday")

        self.assertEqual(board["market_phase"], "intraday")
        self.assertEqual(len(board["intraday_board"]), 4)
        self.assertEqual(board["intraday_board"][0]["ticker"], "A00001")
        self.assertEqual(board["intraday_board"][1]["ticker"], "A00002")
        self.assertEqual(board["intraday_board"][-1]["status"], "suppressed")
        self.assertEqual(board["intraday_board"][0]["execution_priority"], 1)
        self.assertEqual(board["intraday_board"][2]["execution_priority"], 3)
        self.assertIn("분류 변경", board["intraday_board"][0]["change_reason"])
        self.assertTrue(board["intraday_board"][0]["recent_status"])
        self.assertIn("최종 실행 우선순위", " / ".join(board["intraday_board"][0]["priority_reasons"]))
        self.assertIn("priority_reason", board["intraday_board"][0])
        self.assertEqual(board["intraday_board"][0]["priority_rank"], 1)
        self.assertTrue(board["intraday_board"][0]["priority_history"])
        self.assertEqual(board["intraday_board"][0]["name"], "샘플1")


if __name__ == "__main__":
    unittest.main()
