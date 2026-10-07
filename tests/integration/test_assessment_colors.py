import pytest
from flask import render_template
from cis_benchmark.scoring import ComplianceReport


@pytest.mark.parametrize('percentage,color,label', [
    (0, 'red', 'Conformidade muito baixa'),
    (39.9, 'red', 'Conformidade muito baixa'),
    (40, 'orange', 'Baixa conformidade'),
    (59.9, 'orange', 'Baixa conformidade'),
    (60, 'yellow', 'Conformidade moderada'),
    (79.9, 'yellow', 'Conformidade moderada'),
    (80, 'green', 'Alta conformidade'),
    (100, 'green', 'Alta conformidade'),
])
def test_conformity_thresholds_apply_to_each_level(app, percentage, color, label):
    report = ComplianceReport(total_rules=64, evaluated_rules=35, coverage_percentage=57.4,
                              overall_percentage=percentage, level1_percentage=percentage,
                              level2_percentage=percentage, level1_evaluated=21, level2_evaluated=14)
    with app.test_request_context('/'):
        html = render_template('dashboard.html', audit={'report': report})
    assert html.count(f'class="detail {color}"') == 3
    assert html.count(label) == 3
    assert 'class="value coverage-value"' in html
    assert 'Avaliação parcial' in html
    assert 'não definidos pelo CIS' in html


def test_no_evaluated_controls_does_not_receive_a_compliance_rating(app):
    report = ComplianceReport(total_rules=64, manual_review_rules=64)
    with app.test_request_context('/'):
        html = render_template('dashboard.html', audit={'report': report})
    assert html.count('class="value score-neutral"') == 3
    assert html.count('Sem controles avaliados') == 3


def test_complete_coverage_does_not_receive_partial_label(app):
    report = ComplianceReport(total_rules=64, evaluated_rules=61, not_applicable_rules=3,
                              coverage_percentage=100)
    with app.test_request_context('/'):
        html = render_template('dashboard.html', audit={'report': report})
    assert 'Avaliação parcial' not in html
    assert 'class="value coverage-value"' in html
