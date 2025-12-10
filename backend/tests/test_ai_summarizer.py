import unittest
from unittest.mock import MagicMock, patch

from services.ai_summarizer import AiSummaryService


class AiSummaryServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.metrics = {
            "sku": "SKU-123",
            "mode": "inventory",
            "horizon": 30,
            "stockout_date": "2024-09-01",
            "reorder_point": 120,
            "reorder_date": "2024-08-15",
            "recommended_order_qty": 400,
            "safety_stock": 200,
            "service_level": 0.95,
            "insights": ["Demand is rising"],
        }

    @patch("services.ai_summarizer.requests.Session.post")
    def test_summarize_parses_success_response(self, mock_post: MagicMock) -> None:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json_blob(
                            summary="Inventory levels look stable.",
                            actions=["Confirm supplier lead time."],
                            risks=["Monitor demand spikes."],
                        )
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        service = AiSummaryService(api_token="dummy", enable_cache=False)
        result = service.summarize("job-1", self.metrics)

        self.assertEqual(result.summary, "Inventory levels look stable.")
        self.assertEqual(result.actions, ["Confirm supplier lead time."])
        self.assertEqual(result.risks, ["Monitor demand spikes."])
        self.assertEqual(result.source, "HuggingFaceH4/zephyr-7b-beta")
        self.assertIsNotNone(result.generated_at)

    @patch("services.ai_summarizer.time.sleep", autospec=True)
    @patch("services.ai_summarizer.requests.Session.post")
    def test_summarize_retries_on_rate_limit(
        self, mock_post: MagicMock, mock_sleep: MagicMock
    ) -> None:
        rate_limited = MagicMock()
        rate_limited.status_code = 429

        success = MagicMock()
        success.status_code = 200
        success.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json_blob(
                            summary="Reorder is needed soon.",
                            actions=["Place an order for 400 units."],
                            risks=[],
                        )
                    }
                }
            ]
        }

        mock_post.side_effect = [rate_limited, success]

        service = AiSummaryService(api_token="dummy", enable_cache=False, max_retries=2)
        result = service.summarize("job-2", self.metrics)

        self.assertEqual(mock_post.call_count, 2)
        mock_sleep.assert_called()
        self.assertEqual(result.summary, "Reorder is needed soon.")

    @patch("services.ai_summarizer.requests.Session.post")
    def test_summarize_returns_fallback_when_request_fails(
        self, mock_post: MagicMock
    ) -> None:
        failure = MagicMock()
        failure.status_code = 503
        failure.text = "Service unavailable"
        mock_post.return_value = failure

        service = AiSummaryService(api_token="dummy", enable_cache=False, max_retries=0)
        result = service.summarize("job-3", self.metrics)

        self.assertIn("unavailable", result.summary.lower())
        self.assertTrue(result.source.endswith("-fallback"))
        self.assertGreaterEqual(len(result.actions), 1)


def json_blob(summary: str, actions: list[str], risks: list[str]) -> str:
    import json

    return json.dumps(
        {
            "summary": summary,
            "actions": actions,
            "risks": risks,
        }
    )
