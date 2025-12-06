from uuid import UUID


class AnalysisException(Exception):
    pass


class AnalysisInProgress(AnalysisException):
    def __init__(self, document_id: UUID):
        self.document_id = document_id
        super().__init__(f"Analysis already in progress for document: {document_id}")


class AnalysisFailed(AnalysisException):
    def __init__(self, document_id: UUID, error_message: str, error_code: str = ""):
        self.document_id = document_id
        self.error_message = error_message
        self.error_code = error_code
        super().__init__(f"Analysis failed for document {document_id}: {error_message}")


class AnalysisNotStarted(AnalysisException):
    def __init__(self, document_id: UUID):
        self.document_id = document_id
        super().__init__(f"Analysis not started for document: {document_id}")
