from dataclasses import dataclass

HIGH_CONFIDENCE_THRESHOLD = 0.7


@dataclass(frozen=True)
class ConfidenceScore:
    value: float

    def __post_init__(self):
        if self.value < 0.0 or self.value > 1.0:
            raise ValueError(f"Confidence score must be between 0.0 and 1.0, got {self.value}")

    def is_high_confidence(self, threshold: float = HIGH_CONFIDENCE_THRESHOLD) -> bool:
        return self.value >= threshold
