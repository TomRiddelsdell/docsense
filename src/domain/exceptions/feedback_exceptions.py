from uuid import UUID


class FeedbackException(Exception):
    pass


class FeedbackNotFound(FeedbackException):
    def __init__(self, feedback_id: UUID):
        self.feedback_id = feedback_id
        super().__init__(f"Feedback not found: {feedback_id}")


class ChangeAlreadyProcessed(FeedbackException):
    def __init__(self, feedback_id: UUID, current_status: str):
        self.feedback_id = feedback_id
        self.current_status = current_status
        super().__init__(
            f"Change already processed for feedback {feedback_id}. "
            f"Current status: {current_status}"
        )
