"""Safeguard identity, evidence limits and independent organizational scope."""
from dataclasses import replace
from cis_benchmark.audit import audit_content
from cis_benchmark.controls import build_alignment, load_controls
from cis_benchmark.scoring import ComplianceScorer
from tests import FIXTURE_PATH


def test_catalog_versions_groups_and_unique_relationships():
    catalog, mapping = load_controls()
    assert catalog['version'] == '8.1.2'
    assert len(catalog['safeguards']) == 153
    assert len({item['id'] for item in catalog['safeguards']}) == 153
    assert {group: sum(group in item['implementation_groups'] for item in catalog['safeguards'])
            for group in ('IG1', 'IG2', 'IG3')} == {'IG1': 56, 'IG2': 130, 'IG3': 153}
    assert len(mapping['mappings']) == 16
    assert all(item['pdf_page'] == item['source_page'] + 6 for item in catalog['safeguards'])


def test_all_pass_never_proves_organizational_compliance_or_double_counts():
    report = audit_content(FIXTURE_PATH.read_text())
    passed = [replace(result, evaluation_status='PASS', passed=True) for result in report.results]
    alignment = build_alignment(passed)
    assert alignment['groups']['IG3']['mapped_safeguards'] == 16
    assert alignment['groups']['IG3']['pending_review'] == 16
    assert alignment['groups']['IG3']['not_evaluated'] == 137
    items = {item['id']: item for item in alignment['safeguards']}
    assert items['12.2']['technical_passed'] == 4
    assert items['12.2']['organizational_status'] == 'PENDING_REVIEW'
    assert items['4.4']['organizational_status'] == 'NOT_EVALUATED'
    assert all(item['organizational_status'] in ('PENDING_REVIEW', 'NOT_EVALUATED') for item in items.values())


def test_alignment_retains_technical_failures_and_pending_results():
    report = audit_content(FIXTURE_PATH.read_text())
    by_id = {result.rule_id: result for result in report.results}
    results = [replace(by_id['2.4.5'], evaluation_status='FAIL'), replace(by_id['2.1.10'], evaluation_status='MANUAL_REVIEW')]
    alignment = build_alignment(results)
    item = next(item for item in alignment['safeguards'] if item['id'] == '4.6')
    assert item['evaluation_status'] == 'TECHNICAL_EVIDENCE'
    assert item['technical_failed'] == 1
    assert item['technical_passed'] == 0
    assert [ref['status'] for ref in item['benchmark_references']] == ['FAIL', 'MANUAL_REVIEW']


def test_level_selection_and_alignment_do_not_modify_technical_score():
    report = audit_content(FIXTURE_PATH.read_text(), level='1')
    assert report.to_dict()['summary'] == ComplianceScorer().calculate(report.results).to_dict()['summary']
    item = next(item for item in report.controls_alignment['safeguards'] if item['id'] == '12.2')
    assert next(ref for ref in item['benchmark_references'] if ref['benchmark_rule_id'] == '2.5.1')['status'] == 'NOT_SELECTED'
    assert item['organizational_status'] == 'PENDING_REVIEW'
    related = next(result for result in report.results if result.rule_id == '2.4.5')
    assert {item['safeguard_id'] for item in related.controls_safeguards} == {'4.2', '4.6', '12.3'}
