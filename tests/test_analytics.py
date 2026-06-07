import unittest
from datetime import datetime, timedelta
from core.analytics import calculate_confidence, calculate_mastery, calculate_weighted_trend
from core.models import TopicProgress


class AnalyticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.topic = TopicProgress(
            topic='Physics',
            score=84.0,
            last_review=datetime.now() - timedelta(days=3),
            difficulty=0.4,
            attempt_history=[70.0, 75.0, 80.0, 84.0],
        )

    def test_calculate_confidence_range(self) -> None:
        confidence = calculate_confidence(self.topic)
        self.assertGreaterEqual(confidence, 0.0)
        self.assertLessEqual(confidence, 1.0)

    def test_calculate_weighted_trend_positive(self) -> None:
        trend = calculate_weighted_trend(self.topic)
        self.assertGreaterEqual(trend, 0.0)
        self.assertLessEqual(trend, 0.05)

    def test_calculate_mastery_range(self) -> None:
        mastery = calculate_mastery(self.topic)
        self.assertGreaterEqual(mastery, 0.0)
        self.assertLessEqual(mastery, 1.0)


if __name__ == '__main__':
    unittest.main()
