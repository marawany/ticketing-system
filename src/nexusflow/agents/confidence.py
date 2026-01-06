"""
Confidence Calculation Module

Implements state-of-the-art confidence calibration techniques
for ensemble classification combining graph, vector, and LLM predictions.
"""

import math
from dataclasses import dataclass, field

import structlog

from nexusflow.config import settings

logger = structlog.get_logger(__name__)


@dataclass
class ComponentPrediction:
    """A prediction from a single component."""

    level1: str
    level2: str
    level3: str
    confidence: float
    source: str  # "graph", "vector", or "llm"
    metadata: dict = field(default_factory=dict)


@dataclass
class EnsembleResult:
    """Result of ensemble confidence calculation."""

    # Final prediction
    level1: str
    level2: str
    level3: str

    # Component scores
    graph_confidence: float
    vector_confidence: float
    llm_confidence: float

    # Ensemble weights (can be learned)
    graph_weight: float = 0.35
    vector_weight: float = 0.35
    llm_weight: float = 0.30

    # Combined scores
    raw_combined_score: float = 0.0
    calibrated_score: float = 0.0

    # Agreement metrics
    component_agreement: float = 0.0
    entropy: float = 0.0

    # Calibration info
    calibration_method: str = "platt_scaling"
    calibration_temperature: float = 1.0

    @property
    def is_high_confidence(self) -> bool:
        """Check if prediction is high confidence."""
        return (
            self.calibrated_score >= settings.classification_confidence_threshold
            and self.component_agreement >= 0.6
        )

    @property
    def needs_review(self) -> bool:
        """Check if prediction needs human review."""
        return self.calibrated_score < settings.hitl_threshold or self.component_agreement < 0.4


class ConfidenceCalculator:
    """
    Advanced confidence calculator using ensemble methods and calibration.

    Techniques implemented:
    1. Weighted ensemble averaging
    2. Component agreement scoring
    3. Prediction entropy
    4. Platt scaling for calibration
    5. Temperature scaling
    """

    def __init__(
        self,
        graph_weight: float = 0.35,
        vector_weight: float = 0.35,
        llm_weight: float = 0.30,
        calibration_temperature: float = 1.0,
    ):
        self.graph_weight = graph_weight
        self.vector_weight = vector_weight
        self.llm_weight = llm_weight
        self.calibration_temperature = calibration_temperature

        # Platt scaling parameters (can be learned from validation data)
        self.platt_a = 1.0
        self.platt_b = 0.0

    def calculate_ensemble_confidence(
        self,
        graph_prediction: ComponentPrediction,
        vector_prediction: ComponentPrediction,
        llm_prediction: ComponentPrediction,
    ) -> EnsembleResult:
        """
        Calculate ensemble confidence from all three components.

        The ensemble method:
        1. Weighted average of component confidences
        2. Agreement bonus/penalty
        3. Calibration using Platt scaling
        """
        # Calculate component agreement
        agreement = self._calculate_agreement(graph_prediction, vector_prediction, llm_prediction)

        # Calculate weighted raw score
        raw_score = (
            self.graph_weight * graph_prediction.confidence
            + self.vector_weight * vector_prediction.confidence
            + self.llm_weight * llm_prediction.confidence
        )

        # Apply agreement adjustment
        # High agreement increases confidence, low agreement decreases it
        agreement_adjusted = raw_score * (0.7 + 0.3 * agreement)

        # Calculate prediction entropy
        entropy = self._calculate_entropy(
            [
                graph_prediction.confidence,
                vector_prediction.confidence,
                llm_prediction.confidence,
            ]
        )

        # Apply calibration
        calibrated = self._apply_platt_scaling(agreement_adjusted)

        # Apply temperature scaling
        calibrated = self._apply_temperature_scaling(calibrated)

        # Determine final prediction (majority vote with confidence weighting)
        final_l1, final_l2, final_l3 = self._get_majority_prediction(
            graph_prediction, vector_prediction, llm_prediction
        )

        return EnsembleResult(
            level1=final_l1,
            level2=final_l2,
            level3=final_l3,
            graph_confidence=graph_prediction.confidence,
            vector_confidence=vector_prediction.confidence,
            llm_confidence=llm_prediction.confidence,
            graph_weight=self.graph_weight,
            vector_weight=self.vector_weight,
            llm_weight=self.llm_weight,
            raw_combined_score=raw_score,
            calibrated_score=calibrated,
            component_agreement=agreement,
            entropy=entropy,
            calibration_method="platt_scaling",
            calibration_temperature=self.calibration_temperature,
        )

    def _calculate_agreement(
        self,
        graph_pred: ComponentPrediction,
        vector_pred: ComponentPrediction,
        llm_pred: ComponentPrediction,
    ) -> float:
        """
        Calculate agreement between components.

        Returns a score from 0-1 where:
        - 1.0 = all components agree on all levels
        - 0.0 = complete disagreement
        """
        predictions = [graph_pred, vector_pred, llm_pred]

        # Level 1 agreement
        l1_values = [p.level1 for p in predictions]
        l1_agreement = self._calculate_level_agreement(l1_values)

        # Level 2 agreement (weighted less if L1 disagrees)
        l2_values = [p.level2 for p in predictions]
        l2_agreement = self._calculate_level_agreement(l2_values)

        # Level 3 agreement (weighted less if L2 disagrees)
        l3_values = [p.level3 for p in predictions]
        l3_agreement = self._calculate_level_agreement(l3_values)

        # Hierarchical weighting - higher levels matter more
        # If L1 disagrees, L2 and L3 agreement matters less
        weighted_agreement = (
            0.4 * l1_agreement
            + 0.35 * l2_agreement * l1_agreement
            + 0.25 * l3_agreement * l2_agreement
        )

        return weighted_agreement

    def _calculate_level_agreement(self, values: list[str]) -> float:
        """Calculate agreement for a single level."""
        if not values:
            return 0.0

        # Count most common value
        from collections import Counter

        counts = Counter(values)
        most_common_count = counts.most_common(1)[0][1]

        # Agreement is proportion of predictions that agree
        return most_common_count / len(values)

    def _calculate_entropy(self, confidences: list[float]) -> float:
        """
        Calculate entropy of confidence distribution.

        Lower entropy = more confident prediction
        Higher entropy = more uncertain
        """
        # Normalize confidences to form a probability distribution
        total = sum(confidences)
        if total == 0:
            return 1.0  # Maximum uncertainty

        probs = [c / total for c in confidences]

        # Calculate Shannon entropy
        entropy = 0.0
        for p in probs:
            if p > 0:
                entropy -= p * math.log2(p)

        # Normalize to 0-1 range (max entropy for 3 items is log2(3) ≈ 1.58)
        max_entropy = math.log2(len(confidences))
        normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

        return normalized_entropy

    def _apply_platt_scaling(self, score: float) -> float:
        """
        Apply Platt scaling calibration.

        Transforms the raw score using a sigmoid function:
        calibrated = 1 / (1 + exp(A * score + B))

        Parameters A and B can be learned from validation data.
        """
        # Apply sigmoid transformation
        exponent = self.platt_a * score + self.platt_b

        # Avoid overflow
        if exponent > 100:
            return 0.0
        if exponent < -100:
            return 1.0

        calibrated = 1.0 / (1.0 + math.exp(-exponent))
        return calibrated

    def _apply_temperature_scaling(self, score: float) -> float:
        """
        Apply temperature scaling.

        Temperature > 1 makes predictions more conservative (lower confidence)
        Temperature < 1 makes predictions more confident
        """
        if self.calibration_temperature == 1.0:
            return score

        # Convert to logit, scale, convert back
        # Clip to avoid log(0) or log(1)
        score_clipped = max(0.001, min(0.999, score))
        logit = math.log(score_clipped / (1 - score_clipped))

        scaled_logit = logit / self.calibration_temperature

        scaled_score = 1.0 / (1.0 + math.exp(-scaled_logit))
        return scaled_score

    def _get_majority_prediction(
        self,
        graph_pred: ComponentPrediction,
        vector_pred: ComponentPrediction,
        llm_pred: ComponentPrediction,
    ) -> tuple[str, str, str]:
        """
        Get majority prediction with confidence-weighted voting.
        """
        predictions = [
            (graph_pred, self.graph_weight),
            (vector_pred, self.vector_weight),
            (llm_pred, self.llm_weight),
        ]

        # Weighted voting for each level
        def weighted_vote(level_getter) -> str:
            votes: dict[str, float] = {}
            for pred, weight in predictions:
                value = level_getter(pred)
                votes[value] = votes.get(value, 0) + weight * pred.confidence
            return max(votes.items(), key=lambda x: x[1])[0]

        final_l1 = weighted_vote(lambda p: p.level1)
        final_l2 = weighted_vote(lambda p: p.level2)
        final_l3 = weighted_vote(lambda p: p.level3)

        return final_l1, final_l2, final_l3

    def fit_calibration(
        self,
        validation_scores: list[float],
        validation_labels: list[bool],
    ) -> None:
        """
        Fit Platt scaling parameters on validation data.

        Args:
            validation_scores: Raw ensemble scores
            validation_labels: True if prediction was correct
        """
        try:
            from scipy.optimize import minimize

            def negative_log_likelihood(params):
                a, b = params
                total_nll = 0.0
                for score, label in zip(validation_scores, validation_labels):
                    p = 1.0 / (1.0 + math.exp(-(a * score + b)))
                    p = max(1e-10, min(1 - 1e-10, p))
                    if label:
                        total_nll -= math.log(p)
                    else:
                        total_nll -= math.log(1 - p)
                return total_nll

            result = minimize(
                negative_log_likelihood,
                x0=[1.0, 0.0],
                method="BFGS",
            )

            self.platt_a, self.platt_b = result.x
            logger.info(
                "Fitted Platt scaling parameters",
                a=self.platt_a,
                b=self.platt_b,
            )
        except ImportError:
            logger.warning("scipy not available, using default calibration parameters")


def calculate_ensemble_confidence(
    graph_confidence: float,
    graph_prediction: tuple[str, str, str],
    vector_confidence: float,
    vector_prediction: tuple[str, str, str],
    llm_confidence: float,
    llm_prediction: tuple[str, str, str],
    graph_weight: float = 0.35,
    vector_weight: float = 0.35,
    llm_weight: float = 0.30,
) -> EnsembleResult:
    """
    Convenience function to calculate ensemble confidence.
    """
    calculator = ConfidenceCalculator(
        graph_weight=graph_weight,
        vector_weight=vector_weight,
        llm_weight=llm_weight,
    )

    graph_pred = ComponentPrediction(
        level1=graph_prediction[0],
        level2=graph_prediction[1],
        level3=graph_prediction[2],
        confidence=graph_confidence,
        source="graph",
    )

    vector_pred = ComponentPrediction(
        level1=vector_prediction[0],
        level2=vector_prediction[1],
        level3=vector_prediction[2],
        confidence=vector_confidence,
        source="vector",
    )

    llm_pred = ComponentPrediction(
        level1=llm_prediction[0],
        level2=llm_prediction[1],
        level3=llm_prediction[2],
        confidence=llm_confidence,
        source="llm",
    )

    return calculator.calculate_ensemble_confidence(graph_pred, vector_pred, llm_pred)
