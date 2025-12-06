from enum import Enum


class FeedbackStatus(Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    MODIFIED = "MODIFIED"

    def is_resolved(self) -> bool:
        return self != FeedbackStatus.PENDING
