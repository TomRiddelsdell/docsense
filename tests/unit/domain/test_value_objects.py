import pytest
from uuid import uuid4, UUID
from hypothesis import given, strategies as st

from src.domain.value_objects.document_id import DocumentId
from src.domain.value_objects.version_number import VersionNumber
from src.domain.value_objects.confidence_score import ConfidenceScore
from src.domain.value_objects.requirement_type import RequirementType
from src.domain.value_objects.compliance_status import ComplianceStatus
from src.domain.value_objects.document_status import DocumentStatus
from src.domain.value_objects.feedback_status import FeedbackStatus
from src.domain.value_objects.section import Section


class TestDocumentId:
    def test_create_from_uuid(self):
        uuid = uuid4()
        doc_id = DocumentId(uuid)
        assert doc_id.value == uuid

    def test_generate_creates_unique_ids(self):
        id1 = DocumentId.generate()
        id2 = DocumentId.generate()
        assert id1 != id2

    def test_from_string_parses_valid_uuid(self):
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        doc_id = DocumentId.from_string(uuid_str)
        assert str(doc_id.value) == uuid_str

    def test_from_string_raises_on_invalid_uuid(self):
        with pytest.raises(ValueError):
            DocumentId.from_string("not-a-uuid")

    def test_equality_based_on_value(self):
        uuid = uuid4()
        id1 = DocumentId(uuid)
        id2 = DocumentId(uuid)
        assert id1 == id2

    def test_str_returns_uuid_string(self):
        uuid = uuid4()
        doc_id = DocumentId(uuid)
        assert str(doc_id) == str(uuid)

    def test_is_immutable(self):
        doc_id = DocumentId.generate()
        with pytest.raises(AttributeError):
            doc_id.value = uuid4()


class TestVersionNumber:
    def test_create_with_defaults(self):
        version = VersionNumber()
        assert version.major == 1
        assert version.minor == 0
        assert version.patch == 0

    def test_create_with_values(self):
        version = VersionNumber(2, 3, 4)
        assert version.major == 2
        assert version.minor == 3
        assert version.patch == 4

    def test_from_string_parses_valid_version(self):
        version = VersionNumber.from_string("1.2.3")
        assert version.major == 1
        assert version.minor == 2
        assert version.patch == 3

    def test_from_string_raises_on_invalid_format(self):
        with pytest.raises(ValueError):
            VersionNumber.from_string("invalid")

    def test_str_returns_semver_format(self):
        version = VersionNumber(1, 2, 3)
        assert str(version) == "1.2.3"

    def test_increment_patch(self):
        version = VersionNumber(1, 2, 3)
        new_version = version.increment_patch()
        assert new_version.patch == 4
        assert version.patch == 3  # Original unchanged

    def test_increment_minor_resets_patch(self):
        version = VersionNumber(1, 2, 3)
        new_version = version.increment_minor()
        assert new_version.minor == 3
        assert new_version.patch == 0

    def test_increment_major_resets_minor_and_patch(self):
        version = VersionNumber(1, 2, 3)
        new_version = version.increment_major()
        assert new_version.major == 2
        assert new_version.minor == 0
        assert new_version.patch == 0

    def test_comparison_operators(self):
        v1 = VersionNumber(1, 0, 0)
        v2 = VersionNumber(1, 1, 0)
        v3 = VersionNumber(2, 0, 0)
        assert v1 < v2 < v3
        assert v3 > v2 > v1

    def test_rejects_negative_values(self):
        with pytest.raises(ValueError):
            VersionNumber(-1, 0, 0)

    @given(st.integers(0, 100), st.integers(0, 100), st.integers(0, 100))
    def test_roundtrip_string_conversion(self, major, minor, patch):
        version = VersionNumber(major, minor, patch)
        parsed = VersionNumber.from_string(str(version))
        assert parsed == version


class TestConfidenceScore:
    def test_create_valid_score(self):
        score = ConfidenceScore(0.85)
        assert score.value == 0.85

    def test_rejects_below_zero(self):
        with pytest.raises(ValueError):
            ConfidenceScore(-0.1)

    def test_rejects_above_one(self):
        with pytest.raises(ValueError):
            ConfidenceScore(1.1)

    def test_accepts_boundary_values(self):
        zero = ConfidenceScore(0.0)
        one = ConfidenceScore(1.0)
        assert zero.value == 0.0
        assert one.value == 1.0

    def test_is_high_confidence_above_threshold(self):
        high = ConfidenceScore(0.8)
        low = ConfidenceScore(0.5)
        assert high.is_high_confidence()
        assert not low.is_high_confidence()

    def test_equality_based_on_value(self):
        s1 = ConfidenceScore(0.85)
        s2 = ConfidenceScore(0.85)
        assert s1 == s2

    @given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    def test_accepts_valid_range(self, value):
        score = ConfidenceScore(value)
        assert 0.0 <= score.value <= 1.0


class TestRequirementType:
    def test_must_requirement(self):
        req = RequirementType.MUST
        assert req.is_mandatory()
        assert not req.is_optional()

    def test_should_requirement(self):
        req = RequirementType.SHOULD
        assert not req.is_mandatory()
        assert not req.is_optional()

    def test_may_requirement(self):
        req = RequirementType.MAY
        assert not req.is_mandatory()
        assert req.is_optional()

    def test_from_string(self):
        assert RequirementType.from_string("MUST") == RequirementType.MUST
        assert RequirementType.from_string("must") == RequirementType.MUST
        assert RequirementType.from_string("Should") == RequirementType.SHOULD


class TestComplianceStatus:
    def test_all_statuses_exist(self):
        assert ComplianceStatus.PENDING
        assert ComplianceStatus.COMPLIANT
        assert ComplianceStatus.PARTIAL
        assert ComplianceStatus.NON_COMPLIANT

    def test_is_analyzed(self):
        assert not ComplianceStatus.PENDING.is_analyzed()
        assert ComplianceStatus.COMPLIANT.is_analyzed()
        assert ComplianceStatus.PARTIAL.is_analyzed()
        assert ComplianceStatus.NON_COMPLIANT.is_analyzed()

    def test_is_passing(self):
        assert ComplianceStatus.COMPLIANT.is_passing()
        assert not ComplianceStatus.NON_COMPLIANT.is_passing()
        assert not ComplianceStatus.PARTIAL.is_passing()


class TestDocumentStatus:
    def test_all_statuses_exist(self):
        assert DocumentStatus.DRAFT
        assert DocumentStatus.UPLOADED
        assert DocumentStatus.CONVERTED
        assert DocumentStatus.ANALYZING
        assert DocumentStatus.ANALYZED
        assert DocumentStatus.EXPORTED

    def test_can_analyze_only_when_converted(self):
        assert not DocumentStatus.DRAFT.can_analyze()
        assert not DocumentStatus.UPLOADED.can_analyze()
        assert DocumentStatus.CONVERTED.can_analyze()
        assert not DocumentStatus.ANALYZING.can_analyze()
        assert DocumentStatus.ANALYZED.can_analyze()


class TestFeedbackStatus:
    def test_all_statuses_exist(self):
        assert FeedbackStatus.PENDING
        assert FeedbackStatus.ACCEPTED
        assert FeedbackStatus.REJECTED
        assert FeedbackStatus.MODIFIED

    def test_is_resolved(self):
        assert not FeedbackStatus.PENDING.is_resolved()
        assert FeedbackStatus.ACCEPTED.is_resolved()
        assert FeedbackStatus.REJECTED.is_resolved()
        assert FeedbackStatus.MODIFIED.is_resolved()


class TestSection:
    def test_create_section(self):
        section = Section(
            heading="Overview",
            content="This is the overview content",
            level=1
        )
        assert section.heading == "Overview"
        assert section.content == "This is the overview content"
        assert section.level == 1

    def test_section_with_subsections(self):
        subsection = Section(heading="Details", content="Details content", level=2)
        section = Section(
            heading="Overview",
            content="Overview content",
            level=1,
            subsections=[subsection]
        )
        assert len(section.subsections) == 1
        assert section.subsections[0].heading == "Details"

    def test_word_count(self):
        section = Section(heading="Test", content="This has five words here", level=1)
        assert section.word_count() == 5

    def test_is_empty(self):
        empty = Section(heading="Empty", content="", level=1)
        non_empty = Section(heading="Full", content="Has content", level=1)
        assert empty.is_empty()
        assert not non_empty.is_empty()

    def test_rejects_invalid_level(self):
        with pytest.raises(ValueError):
            Section(heading="Test", content="Content", level=0)
        with pytest.raises(ValueError):
            Section(heading="Test", content="Content", level=7)
