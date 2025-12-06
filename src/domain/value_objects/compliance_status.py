from enum import Enum


class ComplianceStatus(Enum):
    PENDING = "PENDING"
    COMPLIANT = "COMPLIANT"
    PARTIAL = "PARTIAL"
    NON_COMPLIANT = "NON_COMPLIANT"

    def is_analyzed(self) -> bool:
        return self != ComplianceStatus.PENDING

    def is_passing(self) -> bool:
        return self == ComplianceStatus.COMPLIANT
