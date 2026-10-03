"""Health Scoring Stage — calculates deterministic manifest integrity scores."""
from typing import Any, List


class HealthScoringStage:
    """Calculates health scores (0-100) based on violation severity."""

    @staticmethod
    def calculate_score(violations: List[Any]) -> float:
        """Calculates a deterministic health score from 0.0 to 100.0.

        Args:
            violations: Combined list of schema and integrity violations.

        Returns:
            Float score clamped between 0.0 and 100.0.
        """
        score = 100.0
        for v in violations:
            sev = getattr(v, 'severity', 'LOW')
            if isinstance(sev, str):
                sev = sev.upper()
            else:
                sev = str(sev).upper()

            if sev == "CRITICAL":
                score -= 15.0
            elif sev == "HIGH":
                score -= 5.0
            elif sev == "MEDIUM":
                score -= 2.0
            else:
                score -= 0.5

        return max(0.0, score)
