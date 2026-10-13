import importlib
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# Prevent loading a real API key or creating clients connected to services.
with patch.dict(os.environ, {"MOCK_GEMINI_SERVICE": "true"}):
    import api_client

with patch("kafka_producer.KafkaFeedbackProducer") as producer_class, patch(
    "mongodb.MongoDBConnection"
) as mongo_class:
    api = importlib.import_module("fast_api")


class FeedbackTests(unittest.TestCase):
    def setUp(self):
        self.producer = MagicMock()
        self.db = MagicMock()
        self.producer_patch = patch.object(api, "producer", self.producer)
        self.db_patch = patch.object(api, "db", self.db)
        self.producer_patch.start()
        self.db_patch.start()
        self.addCleanup(self.producer_patch.stop)
        self.addCleanup(self.db_patch.stop)
        self.client = TestClient(api.app)
        self.addCleanup(self.client.close)

    def test_valid_feedback_is_sent_to_queue(self):
        response = self.client.post("/feedback/", json={"comment": " Bom! ", "rating": 5})
        self.assertEqual(response.status_code, 200)
        self.producer.produce_feedback.assert_called_once_with({"comment": "Bom!", "rating": 5})

    def test_invalid_feedback_is_not_sent(self):
        for comment, rating in [("", 3), ("   ", 3), ("ok", 0), ("ok", 6), ("x" * 5001, 3)]:
            with self.subTest(comment_length=len(comment), rating=rating):
                response = self.client.post("/feedback/", json={"comment": comment, "rating": rating})
                self.assertEqual(response.status_code, 422)
        self.producer.produce_feedback.assert_not_called()

    def test_queue_failure_returns_503(self):
        self.producer.produce_feedback.side_effect = RuntimeError("Broker unavailable")
        response = self.client.post("/feedback/", json={"comment": "ok", "rating": 3})
        self.assertEqual(response.status_code, 503)

    def test_find_feedback(self):
        self.db["feedback"].find_one.return_value = {"_id": "internal", "comment": "Bom", "status": "aprovado"}
        response = self.client.get("/feedback/Bom")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"comment": "Bom", "status": "aprovado"})
        self.db["feedback"].find_one.assert_called_once_with({"comment": "Bom"})

    def test_missing_feedback_returns_404(self):
        self.db["feedback"].find_one.return_value = None
        self.assertEqual(self.client.get("/feedback/ausente").status_code, 404)

    def test_mock_does_not_request_gemini(self):
        with patch.object(api_client, "MOCK_GEMINI_SERVICE", True), patch.object(api_client, "_request_feedback") as request:
            result = api_client.analyze_sentiment("Bom", 5)
        self.assertEqual(result["status"], "aprovado")
        self.assertIsInstance(result["descricao"], str)
        request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
