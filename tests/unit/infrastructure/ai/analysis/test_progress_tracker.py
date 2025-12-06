import pytest
from uuid import uuid4
from datetime import datetime

from src.infrastructure.ai.analysis.progress_tracker import (
    ProgressTracker,
    AnalysisProgress,
    AnalysisStage,
    AnalysisCancelledException,
)


class TestAnalysisStage:
    def test_stage_values(self):
        assert AnalysisStage.INITIALIZED.value == "initialized"
        assert AnalysisStage.ANALYZING.value == "analyzing"
        assert AnalysisStage.COMPLETED.value == "completed"
        assert AnalysisStage.FAILED.value == "failed"
        assert AnalysisStage.CANCELLED.value == "cancelled"


class TestProgressTracker:
    @pytest.fixture
    def tracker(self):
        return ProgressTracker(document_id=uuid4(), total_steps=4)

    def test_initial_state(self, tracker):
        progress = tracker.get_progress()
        
        assert progress.stage == AnalysisStage.INITIALIZED
        assert progress.progress_percent == 0.0
        assert progress.completed_steps == 0
        assert progress.total_steps == 4

    def test_start_stage(self, tracker):
        tracker.start_stage(AnalysisStage.PREPROCESSING, "Preparing document")
        
        progress = tracker.get_progress()
        assert progress.stage == AnalysisStage.PREPROCESSING
        assert progress.current_step == "Preparing document"

    def test_complete_step(self, tracker):
        tracker.start_stage(AnalysisStage.ANALYZING, "Analyzing")
        tracker.complete_step("Next step")
        
        progress = tracker.get_progress()
        assert progress.completed_steps == 1
        assert progress.current_step == "Next step"
        assert progress.progress_percent == 25.0

    def test_complete_multiple_steps(self, tracker):
        for i in range(4):
            tracker.complete_step(f"Step {i+1}")
        
        progress = tracker.get_progress()
        assert progress.completed_steps == 4
        assert progress.progress_percent == 100.0

    def test_add_error(self, tracker):
        tracker.add_error("Something went wrong")
        
        progress = tracker.get_progress()
        assert "Something went wrong" in progress.errors

    def test_add_warning(self, tracker):
        tracker.add_warning("Minor issue")
        
        progress = tracker.get_progress()
        assert "Minor issue" in progress.warnings

    def test_complete(self, tracker):
        tracker.complete()
        
        progress = tracker.get_progress()
        assert progress.stage == AnalysisStage.COMPLETED
        assert progress.completed_steps == 4

    def test_fail(self, tracker):
        tracker.fail("Critical error")
        
        progress = tracker.get_progress()
        assert progress.stage == AnalysisStage.FAILED
        assert "Critical error" in progress.errors

    def test_cancel(self, tracker):
        tracker.cancel()
        
        progress = tracker.get_progress()
        assert progress.stage == AnalysisStage.CANCELLED
        assert tracker.is_cancelled

    def test_cannot_proceed_after_cancel(self, tracker):
        tracker.cancel()
        
        with pytest.raises(AnalysisCancelledException):
            tracker.start_stage(AnalysisStage.ANALYZING, "Try to analyze")

    def test_callback_notification(self, tracker):
        notifications = []
        
        def callback(progress: AnalysisProgress):
            notifications.append(progress)
        
        tracker.add_callback(callback)
        tracker.start_stage(AnalysisStage.ANALYZING, "Starting")
        tracker.complete_step("Done")
        
        assert len(notifications) == 2
        assert notifications[0].stage == AnalysisStage.ANALYZING
        assert notifications[1].completed_steps == 1

    def test_remove_callback(self, tracker):
        notifications = []
        
        def callback(progress: AnalysisProgress):
            notifications.append(progress)
        
        tracker.add_callback(callback)
        tracker.start_stage(AnalysisStage.ANALYZING, "Step 1")
        
        tracker.remove_callback(callback)
        tracker.complete_step("Step 2")
        
        assert len(notifications) == 1

    def test_analysis_id(self, tracker):
        assert tracker.analysis_id is not None


class TestAnalysisProgress:
    def test_to_dict(self):
        doc_id = uuid4()
        progress = AnalysisProgress(
            analysis_id=uuid4(),
            document_id=doc_id,
            stage=AnalysisStage.ANALYZING,
            progress_percent=50.0,
            current_step="Analyzing content",
            total_steps=4,
            completed_steps=2,
            started_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        
        result = progress.to_dict()
        
        assert result["document_id"] == str(doc_id)
        assert result["stage"] == "analyzing"
        assert result["progress_percent"] == 50.0
        assert result["completed_steps"] == 2
