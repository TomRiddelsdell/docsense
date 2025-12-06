from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable
from uuid import UUID, uuid4


class AnalysisStage(Enum):
    INITIALIZED = "initialized"
    PREPROCESSING = "preprocessing"
    ANALYZING = "analyzing"
    EVALUATING_POLICIES = "evaluating_policies"
    GENERATING_FEEDBACK = "generating_feedback"
    AGGREGATING_RESULTS = "aggregating_results"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AnalysisProgress:
    analysis_id: UUID
    document_id: UUID
    stage: AnalysisStage
    progress_percent: float
    current_step: str
    total_steps: int
    completed_steps: int
    started_at: datetime
    updated_at: datetime
    estimated_completion: datetime | None = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "analysis_id": str(self.analysis_id),
            "document_id": str(self.document_id),
            "stage": self.stage.value,
            "progress_percent": self.progress_percent,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "estimated_completion": self.estimated_completion.isoformat() if self.estimated_completion else None,
            "errors": self.errors,
            "warnings": self.warnings,
        }


ProgressCallback = Callable[[AnalysisProgress], None]


class ProgressTracker:
    
    def __init__(self, document_id: UUID, total_steps: int = 5):
        self._analysis_id = uuid4()
        self._document_id = document_id
        self._total_steps = total_steps
        self._completed_steps = 0
        self._stage = AnalysisStage.INITIALIZED
        self._current_step = "Initializing"
        self._started_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()
        self._errors: list[str] = []
        self._warnings: list[str] = []
        self._callbacks: list[ProgressCallback] = []
        self._cancelled = False

    @property
    def analysis_id(self) -> UUID:
        return self._analysis_id

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def add_callback(self, callback: ProgressCallback) -> None:
        self._callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def get_progress(self) -> AnalysisProgress:
        progress_percent = (self._completed_steps / self._total_steps) * 100 if self._total_steps > 0 else 0
        
        estimated_completion = None
        if self._completed_steps > 0 and self._stage not in (AnalysisStage.COMPLETED, AnalysisStage.FAILED, AnalysisStage.CANCELLED):
            elapsed = (datetime.utcnow() - self._started_at).total_seconds()
            time_per_step = elapsed / self._completed_steps
            remaining_steps = self._total_steps - self._completed_steps
            estimated_seconds = remaining_steps * time_per_step
            from datetime import timedelta
            estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)
        
        return AnalysisProgress(
            analysis_id=self._analysis_id,
            document_id=self._document_id,
            stage=self._stage,
            progress_percent=progress_percent,
            current_step=self._current_step,
            total_steps=self._total_steps,
            completed_steps=self._completed_steps,
            started_at=self._started_at,
            updated_at=self._updated_at,
            estimated_completion=estimated_completion,
            errors=self._errors.copy(),
            warnings=self._warnings.copy(),
        )

    def start_stage(self, stage: AnalysisStage, step_description: str) -> None:
        if self._cancelled:
            raise AnalysisCancelledException("Analysis was cancelled")
        
        self._stage = stage
        self._current_step = step_description
        self._updated_at = datetime.utcnow()
        self._notify_callbacks()

    def complete_step(self, next_description: str | None = None) -> None:
        if self._cancelled:
            raise AnalysisCancelledException("Analysis was cancelled")
        
        self._completed_steps += 1
        if next_description:
            self._current_step = next_description
        self._updated_at = datetime.utcnow()
        self._notify_callbacks()

    def add_error(self, error: str) -> None:
        self._errors.append(error)
        self._updated_at = datetime.utcnow()
        self._notify_callbacks()

    def add_warning(self, warning: str) -> None:
        self._warnings.append(warning)
        self._updated_at = datetime.utcnow()
        self._notify_callbacks()

    def complete(self) -> None:
        self._stage = AnalysisStage.COMPLETED
        self._completed_steps = self._total_steps
        self._current_step = "Analysis complete"
        self._updated_at = datetime.utcnow()
        self._notify_callbacks()

    def fail(self, error: str) -> None:
        self._stage = AnalysisStage.FAILED
        self._current_step = "Analysis failed"
        self._errors.append(error)
        self._updated_at = datetime.utcnow()
        self._notify_callbacks()

    def cancel(self) -> None:
        self._cancelled = True
        self._stage = AnalysisStage.CANCELLED
        self._current_step = "Analysis cancelled"
        self._updated_at = datetime.utcnow()
        self._notify_callbacks()

    def _notify_callbacks(self) -> None:
        progress = self.get_progress()
        for callback in self._callbacks:
            try:
                callback(progress)
            except Exception:
                pass


class AnalysisCancelledException(Exception):
    pass
