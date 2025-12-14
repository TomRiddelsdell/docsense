"""
Tests for value object DDD compliance.

Tests that value objects are immutable and aggregates use them correctly,
preventing mutation of internal state.
"""
import pytest
from uuid import uuid4

from src.domain.value_objects import FeedbackItem, FeedbackStatus, Policy, RequirementType
from src.domain.aggregates.feedback_session import FeedbackSession
from src.domain.aggregates.policy_repository import PolicyRepository as PolicyRepositoryAggregate


class TestFeedbackItemValueObject:
    """Test FeedbackItem value object immutability and behavior."""

    def test_feedback_item_is_frozen(self):
        """Test that FeedbackItem is immutable (frozen dataclass)."""
        item = FeedbackItem.create_pending(
            feedback_id=uuid4(),
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.9,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        # Should raise AttributeError when trying to modify
        with pytest.raises(AttributeError):
            item.status = FeedbackStatus.ACCEPTED  # type: ignore

    def test_create_pending_feedback_item(self):
        """Test creating a pending feedback item."""
        feedback_id = uuid4()
        item = FeedbackItem.create_pending(
            feedback_id=feedback_id,
            issue_description="Missing requirement",
            suggested_change="Add requirement X",
            confidence_score=0.85,
            policy_reference="SEC-Rule-10b5",
            section_reference="Section 3"
        )

        assert item.feedback_id == feedback_id
        assert item.issue_description == "Missing requirement"
        assert item.suggested_change == "Add requirement X"
        assert item.confidence_score == 0.85
        assert item.policy_reference == "SEC-Rule-10b5"
        assert item.section_reference == "Section 3"
        assert item.status == FeedbackStatus.PENDING
        assert item.applied_change is None
        assert item.rejection_reason is None
        assert item.modified_change is None

    def test_accept_creates_new_instance(self):
        """Test that accepting feedback creates a new instance."""
        original = FeedbackItem.create_pending(
            feedback_id=uuid4(),
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.9,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        accepted = original.accept("Applied change text")

        # Original is unchanged
        assert original.status == FeedbackStatus.PENDING
        assert original.applied_change is None

        # New instance has updated status
        assert accepted.status == FeedbackStatus.ACCEPTED
        assert accepted.applied_change == "Applied change text"
        assert accepted.feedback_id == original.feedback_id

    def test_reject_creates_new_instance(self):
        """Test that rejecting feedback creates a new instance."""
        original = FeedbackItem.create_pending(
            feedback_id=uuid4(),
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.9,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        rejected = original.reject("Not applicable")

        # Original is unchanged
        assert original.status == FeedbackStatus.PENDING
        assert original.rejection_reason is None

        # New instance has updated status
        assert rejected.status == FeedbackStatus.REJECTED
        assert rejected.rejection_reason == "Not applicable"

    def test_modify_creates_new_instance(self):
        """Test that modifying feedback creates a new instance."""
        original = FeedbackItem.create_pending(
            feedback_id=uuid4(),
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.9,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        modified = original.modify("Modified change text")

        # Original is unchanged
        assert original.status == FeedbackStatus.PENDING
        assert original.modified_change is None

        # New instance has updated status
        assert modified.status == FeedbackStatus.MODIFIED
        assert modified.modified_change == "Modified change text"

    def test_confidence_score_validation(self):
        """Test that confidence score must be between 0.0 and 1.0."""
        # Valid scores
        FeedbackItem.create_pending(
            feedback_id=uuid4(),
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.0,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        FeedbackItem.create_pending(
            feedback_id=uuid4(),
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=1.0,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        # Invalid scores
        with pytest.raises(ValueError):
            FeedbackItem.create_pending(
                feedback_id=uuid4(),
                issue_description="Issue",
                suggested_change="Change",
                confidence_score=-0.1,
                policy_reference="POL-1",
                section_reference="SEC-1"
            )

        with pytest.raises(ValueError):
            FeedbackItem.create_pending(
                feedback_id=uuid4(),
                issue_description="Issue",
                suggested_change="Change",
                confidence_score=1.1,
                policy_reference="POL-1",
                section_reference="SEC-1"
            )

    def test_accepted_feedback_must_have_applied_change(self):
        """Test that accepted feedback validation requires applied_change."""
        with pytest.raises(ValueError, match="applied_change"):
            FeedbackItem(
                feedback_id=uuid4(),
                issue_description="Issue",
                suggested_change="Change",
                confidence_score=0.9,
                policy_reference="POL-1",
                section_reference="SEC-1",
                status=FeedbackStatus.ACCEPTED,
                applied_change=None  # Invalid
            )

    def test_rejected_feedback_must_have_rejection_reason(self):
        """Test that rejected feedback validation requires rejection_reason."""
        with pytest.raises(ValueError, match="rejection_reason"):
            FeedbackItem(
                feedback_id=uuid4(),
                issue_description="Issue",
                suggested_change="Change",
                confidence_score=0.9,
                policy_reference="POL-1",
                section_reference="SEC-1",
                status=FeedbackStatus.REJECTED,
                rejection_reason=None  # Invalid
            )

    def test_modified_feedback_must_have_modified_change(self):
        """Test that modified feedback validation requires modified_change."""
        with pytest.raises(ValueError, match="modified_change"):
            FeedbackItem(
                feedback_id=uuid4(),
                issue_description="Issue",
                suggested_change="Change",
                confidence_score=0.9,
                policy_reference="POL-1",
                section_reference="SEC-1",
                status=FeedbackStatus.MODIFIED,
                modified_change=None  # Invalid
            )

    def test_to_dict_and_from_dict_roundtrip(self):
        """Test that to_dict and from_dict preserve all data."""
        original = FeedbackItem(
            feedback_id=uuid4(),
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.9,
            policy_reference="POL-1",
            section_reference="SEC-1",
            status=FeedbackStatus.ACCEPTED,
            applied_change="Applied"
        )

        dict_form = original.to_dict()
        restored = FeedbackItem.from_dict(dict_form)

        assert restored.feedback_id == original.feedback_id
        assert restored.issue_description == original.issue_description
        assert restored.suggested_change == original.suggested_change
        assert restored.confidence_score == original.confidence_score
        assert restored.policy_reference == original.policy_reference
        assert restored.section_reference == original.section_reference
        assert restored.status == original.status
        assert restored.applied_change == original.applied_change


class TestPolicyValueObject:
    """Test Policy value object immutability and behavior."""

    def test_policy_is_frozen(self):
        """Test that Policy is immutable (frozen dataclass)."""
        policy = Policy(
            policy_id=uuid4(),
            policy_name="Test Policy",
            policy_content="Content",
            requirement_type=RequirementType.MUST
        )

        # Should raise AttributeError when trying to modify
        with pytest.raises(AttributeError):
            policy.policy_name = "New Name"  # type: ignore

    def test_create_policy(self):
        """Test creating a policy value object."""
        policy_id = uuid4()
        policy = Policy(
            policy_id=policy_id,
            policy_name="SEC Rule 10b-5",
            policy_content="No insider trading...",
            requirement_type=RequirementType.MUST
        )

        assert policy.policy_id == policy_id
        assert policy.policy_name == "SEC Rule 10b-5"
        assert policy.policy_content == "No insider trading..."
        assert policy.requirement_type == RequirementType.MUST

    def test_policy_name_cannot_be_empty(self):
        """Test that policy name validation requires non-empty name."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Policy(
                policy_id=uuid4(),
                policy_name="",
                policy_content="Content",
                requirement_type=RequirementType.MUST
            )

        with pytest.raises(ValueError, match="cannot be empty"):
            Policy(
                policy_id=uuid4(),
                policy_name="   ",  # Only whitespace
                policy_content="Content",
                requirement_type=RequirementType.MUST
            )

    def test_policy_content_cannot_be_empty(self):
        """Test that policy content validation requires non-empty content."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Policy(
                policy_id=uuid4(),
                policy_name="Name",
                policy_content="",
                requirement_type=RequirementType.MUST
            )

    def test_is_must_requirement(self):
        """Test is_must_requirement method."""
        must_policy = Policy(
            policy_id=uuid4(),
            policy_name="MUST Policy",
            policy_content="Content",
            requirement_type=RequirementType.MUST
        )

        should_policy = Policy(
            policy_id=uuid4(),
            policy_name="SHOULD Policy",
            policy_content="Content",
            requirement_type=RequirementType.SHOULD
        )

        assert must_policy.is_must_requirement()
        assert not should_policy.is_must_requirement()

    def test_is_should_requirement(self):
        """Test is_should_requirement method."""
        must_policy = Policy(
            policy_id=uuid4(),
            policy_name="MUST Policy",
            policy_content="Content",
            requirement_type=RequirementType.MUST
        )

        should_policy = Policy(
            policy_id=uuid4(),
            policy_name="SHOULD Policy",
            policy_content="Content",
            requirement_type=RequirementType.SHOULD
        )

        assert not must_policy.is_should_requirement()
        assert should_policy.is_should_requirement()

    def test_to_dict_and_from_dict_roundtrip(self):
        """Test that to_dict and from_dict preserve all data."""
        original = Policy(
            policy_id=uuid4(),
            policy_name="Test Policy",
            policy_content="Policy content",
            requirement_type=RequirementType.SHOULD
        )

        dict_form = original.to_dict()
        restored = Policy.from_dict(dict_form)

        assert restored.policy_id == original.policy_id
        assert restored.policy_name == original.policy_name
        assert restored.policy_content == original.policy_content
        assert restored.requirement_type == original.requirement_type


class TestFeedbackSessionWithImmutableValueObjects:
    """Test that FeedbackSession correctly uses immutable FeedbackItem value objects."""

    def test_feedback_session_stores_feedback_items(self):
        """Test that FeedbackSession stores FeedbackItem value objects."""
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4()
        )

        feedback_id = uuid4()
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.9,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        assert len(session.feedback_items) == 1
        item = session.feedback_items[0]
        assert isinstance(item, FeedbackItem)
        assert item.feedback_id == feedback_id
        assert item.status == FeedbackStatus.PENDING

    def test_accepting_feedback_creates_new_list(self):
        """Test that accepting feedback creates new list (immutable update)."""
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4()
        )

        feedback_id = uuid4()
        session.add_feedback(
            feedback_id=feedback_id,
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.9,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        # Get reference to original list
        original_items = session._feedback_items
        original_item = original_items[0]

        # Accept the feedback
        session.accept_change(feedback_id, "user", "Applied")

        # List reference should be different (new list created)
        assert session._feedback_items is not original_items

        # Original item should be unchanged (immutable)
        assert original_item.status == FeedbackStatus.PENDING

        # New list has updated item
        new_item = session._feedback_items[0]
        assert new_item.status == FeedbackStatus.ACCEPTED
        assert new_item.applied_change == "Applied"

    def test_feedback_items_property_returns_copy(self):
        """Test that feedback_items property returns a copy."""
        session = FeedbackSession.create_for_document(
            session_id=uuid4(),
            document_id=uuid4()
        )

        session.add_feedback(
            feedback_id=uuid4(),
            issue_description="Issue",
            suggested_change="Change",
            confidence_score=0.9,
            policy_reference="POL-1",
            section_reference="SEC-1"
        )

        items1 = session.feedback_items
        items2 = session.feedback_items

        # Should be different list objects (copies)
        assert items1 is not items2
        assert items1 is not session._feedback_items


class TestPolicyRepositoryWithImmutableValueObjects:
    """Test that PolicyRepository correctly uses immutable Policy value objects."""

    def test_policy_repository_stores_policies(self):
        """Test that PolicyRepository stores Policy value objects."""
        repo = PolicyRepositoryAggregate.create(
            repository_id=uuid4(),
            name="SEC Rules",
            description="Securities regulations",
            created_by="admin"
        )

        policy_id = uuid4()
        repo.add_policy(
            policy_id=policy_id,
            policy_name="Rule 10b-5",
            policy_content="No insider trading",
            requirement_type="MUST",
            added_by="admin"
        )

        assert len(repo.policies) == 1
        policy = repo.policies[0]
        assert isinstance(policy, Policy)
        assert policy.policy_id == policy_id
        assert policy.policy_name == "Rule 10b-5"

    def test_policies_property_returns_copy(self):
        """Test that policies property returns a copy."""
        repo = PolicyRepositoryAggregate.create(
            repository_id=uuid4(),
            name="SEC Rules",
            description="Securities regulations",
            created_by="admin"
        )

        repo.add_policy(
            policy_id=uuid4(),
            policy_name="Rule 1",
            policy_content="Content",
            requirement_type="MUST",
            added_by="admin"
        )

        policies1 = repo.policies
        policies2 = repo.policies

        # Should be different list objects (copies)
        assert policies1 is not policies2
        assert policies1 is not repo._policies

    def test_assigned_documents_property_returns_copy(self):
        """Test that assigned_documents property returns a copy."""
        repo = PolicyRepositoryAggregate.create(
            repository_id=uuid4(),
            name="SEC Rules",
            description="Securities regulations",
            created_by="admin"
        )

        doc_id = uuid4()
        repo.assign_document(doc_id, "admin")

        docs1 = repo.assigned_documents
        docs2 = repo.assigned_documents

        # Should be different set objects (copies)
        assert docs1 is not docs2
        assert docs1 is not repo._assigned_documents
