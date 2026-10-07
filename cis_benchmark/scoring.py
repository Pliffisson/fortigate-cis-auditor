"""Offline compliance scores with explicit coverage and unresolved controls."""
from dataclasses import dataclass, field
from typing import Dict, List
from .rules.base import RuleResult, RuleSeverity
from .benchmark import NAME


@dataclass
class CategoryScore:
    category: str
    total: int = 0
    passed: int = 0
    failed: int = 0

    @property
    def evaluated(self):
        return self.passed + self.failed

    @property
    def percentage(self):
        return round(100 * self.passed / self.evaluated, 1) if self.evaluated else 0.0


@dataclass
class ComplianceReport:
    total_rules: int = 0
    passed_rules: int = 0
    failed_rules: int = 0
    evaluated_rules: int = 0
    manual_review_rules: int = 0
    not_applicable_rules: int = 0
    error_rules: int = 0
    coverage_percentage: float = 0.0
    overall_percentage: float = 0.0
    risk_rating: str = "Unknown"
    risk_color: str = "#6c757d"
    level1_total: int = 0
    level1_evaluated: int = 0
    level1_passed: int = 0
    level1_percentage: float = 0.0
    level2_total: int = 0
    level2_evaluated: int = 0
    level2_passed: int = 0
    level2_percentage: float = 0.0
    critical_total: int = 0
    critical_passed: int = 0
    critical_percentage: float = 0.0
    high_total: int = 0
    high_passed: int = 0
    high_percentage: float = 0.0
    medium_total: int = 0
    medium_passed: int = 0
    medium_percentage: float = 0.0
    low_total: int = 0
    low_passed: int = 0
    low_percentage: float = 0.0
    weighted_score: float = 0.0
    category_scores: Dict[str, CategoryScore] = field(default_factory=dict)
    results: List[RuleResult] = field(default_factory=list)
    failed_results: List[RuleResult] = field(default_factory=list)
    passed_results: List[RuleResult] = field(default_factory=list)
    pending_results: List[RuleResult] = field(default_factory=list)
    critical_failures: List[RuleResult] = field(default_factory=list)
    high_failures: List[RuleResult] = field(default_factory=list)
    medium_failures: List[RuleResult] = field(default_factory=list)
    low_failures: List[RuleResult] = field(default_factory=list)
    benchmark: str = NAME
    fortios_version: str = ""
    source_document: str = ""
    source_sha256: str = ""
    assessment_method: str = "Offline configuration review; not CIS-CAT or CIS certification"
    parse_warnings: List[str] = field(default_factory=list)
    controls_alignment: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "benchmark": {"name": self.benchmark, "fortios_version": self.fortios_version,
                          "source_document": self.source_document, "source_sha256": self.source_sha256,
                          "assessment_method": self.assessment_method},
            "summary": {k: getattr(self, k) for k in (
                "total_rules", "evaluated_rules", "passed_rules", "failed_rules", "manual_review_rules",
                "not_applicable_rules", "error_rules", "coverage_percentage", "overall_percentage", "weighted_score", "risk_rating")},
            "parse_warnings": self.parse_warnings,
            "controls_alignment": self.controls_alignment,
            "scoring_policy": "PASS/(PASS+FAIL); coverage=(PASS+FAIL)/(total-NOT_APPLICABLE). Weights are project-defined.",
            "level_breakdown": {f"level{level}": {"total": getattr(self, f"level{level}_total"),
                "evaluated": getattr(self, f"level{level}_evaluated"), "passed": getattr(self, f"level{level}_passed"),
                "percentage": getattr(self, f"level{level}_percentage")} for level in (1, 2)},
            "severity_breakdown": {severity: {"total": getattr(self, severity + "_total"),
                "passed": getattr(self, severity + "_passed"), "percentage": getattr(self, severity + "_percentage")}
                for severity in ("critical", "high", "medium", "low")},
            "category_breakdown": {name: {"total": cs.total, "evaluated": cs.evaluated, "passed": cs.passed,
                "failed": cs.failed, "percentage": cs.percentage} for name, cs in self.category_scores.items()},
            "results": [r.to_dict() for r in self.results],
        }


class ComplianceScorer:
    RISK_RATINGS = [(0, 40, "Critical", "#dc3545"), (40, 60, "High", "#fd7e14"),
                    (60, 80, "Medium", "#ffc107"), (80, 101, "Low", "#28a745")]

    def calculate(self, results):
        report = ComplianceReport(results=results, total_rules=len(results))
        report.passed_results = [r for r in results if r.status == "PASS"]
        report.failed_results = [r for r in results if r.status == "FAIL"]
        report.pending_results = [r for r in results if r.status in ("MANUAL_REVIEW", "ERROR")]
        report.passed_rules = len(report.passed_results)
        report.failed_rules = len(report.failed_results)
        report.manual_review_rules = sum(r.status == "MANUAL_REVIEW" for r in results)
        report.error_rules = sum(r.status == "ERROR" for r in results)
        report.not_applicable_rules = sum(r.status == "NOT_APPLICABLE" for r in results)
        evaluated = [r for r in results if r.status in ("PASS", "FAIL")]
        report.evaluated_rules = len(evaluated)
        report.overall_percentage = self.percent(report.passed_rules, len(evaluated))
        report.coverage_percentage = self.percent(len(evaluated), len(results) - report.not_applicable_rules)
        for level in (1, 2):
            group = [r for r in results if r.level.value == level]
            done = [r for r in group if r.status in ("PASS", "FAIL")]
            count = sum(r.status == "PASS" for r in done)
            setattr(report, f"level{level}_total", len(group))
            setattr(report, f"level{level}_evaluated", len(done))
            setattr(report, f"level{level}_passed", count)
            setattr(report, f"level{level}_percentage", self.percent(count, len(done)))
        for severity in RuleSeverity:
            prefix = severity.value.lower()
            group = [r for r in evaluated if r.severity == severity]
            count = sum(r.status == "PASS" for r in group)
            setattr(report, prefix + "_total", len(group))
            setattr(report, prefix + "_passed", count)
            setattr(report, prefix + "_percentage", self.percent(count, len(group)))
            setattr(report, prefix + "_failures", [r for r in group if r.status == "FAIL"])
        for r in results:
            cs = report.category_scores.setdefault(r.category or "Uncategorized", CategoryScore(r.category or "Uncategorized"))
            cs.total += 1
            cs.passed += r.status == "PASS"
            cs.failed += r.status == "FAIL"
        report.category_scores = dict(sorted(report.category_scores.items()))
        report.weighted_score = self.percent(sum(r.severity.weight for r in evaluated if r.status == "PASS"),
                                             sum(r.severity.weight for r in evaluated))
        if report.pending_results:
            report.risk_rating = "Incomplete"
        elif evaluated:
            for low, high, rating, color in self.RISK_RATINGS:
                if low <= report.weighted_score < high:
                    report.risk_rating, report.risk_color = rating, color
                    break
        return report

    @staticmethod
    def percent(numerator, denominator):
        return round(100 * numerator / denominator, 1) if denominator else 0.0
