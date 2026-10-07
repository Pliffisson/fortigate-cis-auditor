"""
CIS Benchmark Rule Base Classes
=================================
Defines the base rule structure, result types, and severity/level enums.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List



class CISLevel(Enum):
    """CIS Benchmark levels."""
    LEVEL_1 = 1  # Basic security settings applicable to most organizations
    LEVEL_2 = 2  # Advanced settings for high-security environments


class RuleSeverity(Enum):
    """Risk severity levels."""
    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

    @property
    def weight(self) -> int:
        weights = {
            "Critical": 10,
            "High": 7,
            "Medium": 4,
            "Low": 1,
        }
        return weights.get(self.value, 1)

    @property
    def color(self) -> str:
        colors = {
            "Critical": "#dc3545",
            "High": "#fd7e14",
            "Medium": "#ffc107",
            "Low": "#28a745",
        }
        return colors.get(self.value, "#6c757d")


@dataclass
class RuleResult:
    """Result of a CIS rule evaluation."""
    rule_id: str
    title: str
    level: CISLevel
    severity: RuleSeverity
    passed: bool
    description: str
    expected_value: str
    actual_value: str
    remediation: str
    category: str = ""
    cis_section: str = ""
    remediation_cli: str = ""
    references: List[str] = field(default_factory=list)
    evaluation_status: str = ""
    assessment: str = "Automated"
    source_page: int = 0
    affected_objects: List[dict] = field(default_factory=list)
    controls_safeguards: List[dict] = field(default_factory=list)

    @property
    def status(self) -> str:
        return self.evaluation_status or ("PASS" if self.passed else "FAIL")

    @property
    def severity_value(self) -> str:
        return self.severity.value

    @property
    def level_value(self) -> int:
        return self.level.value

    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "title": self.title,
            "level": self.level.value,
            "severity": self.severity.value,
            "status": self.status,
            "passed": self.passed,
            "description": self.description,
            "expected_value": self.expected_value,
            "actual_value": self.actual_value,
            "remediation": self.remediation,
            "remediation_cli": self.remediation_cli,
            "category": self.category,
            "cis_section": self.cis_section,
            "references": self.references,
            "assessment": self.assessment,
            "source_page": self.source_page,
            "affected_objects": self.affected_objects,
            "controls_safeguards": self.controls_safeguards,
        }


class CISRule:
    """
    Base class for CIS Benchmark rules.
    
    Subclass and implement `evaluate()` for each CIS control.
    """

    def __init__(
        self,
        rule_id: str,
        title: str,
        level: CISLevel,
        severity: RuleSeverity,
        description: str,
        expected_value: str,
        remediation: str,
        category: str = "",
        cis_section: str = "",
        remediation_cli: str = "",
        references: Optional[List[str]] = None,
    ):
        self.rule_id = rule_id
        self.title = title
        self.level = level
        self.severity = severity
        self.description = description
        self.expected_value = expected_value
        self.remediation = remediation
        self.category = category
        self.cis_section = cis_section
        self.remediation_cli = remediation_cli
        self.references = references or []

    def evaluate(self, config) -> RuleResult:
        """
        Evaluate this rule against a FortiGateConfig.
        Must be overridden in subclasses or use the factory pattern.
        """
        raise NotImplementedError("Subclasses must implement evaluate()")

    def _make_result(self, passed: bool, actual_value: str) -> RuleResult:
        """Helper to create a RuleResult with this rule's metadata."""
        return RuleResult(
            rule_id=self.rule_id,
            title=self.title,
            level=self.level,
            severity=self.severity,
            passed=passed,
            description=self.description,
            expected_value=self.expected_value,
            actual_value=actual_value,
            remediation=self.remediation if not passed else "No action needed",
            category=self.category,
            cis_section=self.cis_section,
            remediation_cli=self.remediation_cli if not passed else "",
            references=self.references,
        )

