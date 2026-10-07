"""Traceable, partial relationships to organizational CIS Controls safeguards."""
import json
from functools import lru_cache
from pathlib import Path

from ..benchmark import CATALOG, NAME

_ROOT = Path(__file__).parent


@lru_cache(maxsize=1)
def load_controls():
    catalog = json.loads((_ROOT / 'catalog.json').read_text(encoding='utf-8'))
    mapping = json.loads((_ROOT / 'mapping.json').read_text(encoding='utf-8'))
    safeguards = catalog['safeguards']
    identifiers = {item['id'] for item in safeguards}
    if len(identifiers) != len(safeguards):
        raise ValueError('Salvaguardas CIS Controls duplicadas.')
    if mapping['framework_version'] != catalog['version'] or mapping['benchmark'] != NAME:
        raise ValueError('Versões incompatíveis no mapeamento CIS Controls.')
    if mapping['origin'] != 'project_analysis' or mapping['review_status'] != 'candidate':
        raise ValueError('Origem do mapeamento CIS Controls não reconhecida.')
    known_rules = {rule['rule_id'] for rule in CATALOG}
    seen = set()
    for item in mapping['mappings']:
        identifier = item['safeguard_id']
        rule_ids = item['rule_ids']
        if identifier not in identifiers or identifier in seen:
            raise ValueError('Relacionamento CIS Controls inválido ou duplicado.')
        if not rule_ids or len(set(rule_ids)) != len(rule_ids) or not set(rule_ids) <= known_rules:
            raise ValueError('Recomendação FortiGate inválida no mapeamento.')
        if not item['rationale'] or not item['additional_evidence']:
            raise ValueError('Relacionamento sem justificativa ou evidência complementar.')
        seen.add(identifier)
    return catalog, mapping


def build_alignment(results):
    catalog, mapping = load_controls()
    by_rule = {result.rule_id: result for result in results}
    relationships = {item['safeguard_id']: item for item in mapping['mappings']}
    items = []
    for safeguard in catalog['safeguards']:
        relation = relationships.get(safeguard['id'])
        references = []
        if relation:
            for rule_id in relation['rule_ids']:
                result = by_rule.get(rule_id)
                references.append({'benchmark_rule_id': rule_id,
                                   'status': result.status if result else 'NOT_SELECTED',
                                   'title': result.title if result else '',
                                   'source_page': result.source_page if result else None})
        evaluated = [ref for ref in references if ref['status'] in ('PASS', 'FAIL')]
        items.append({**safeguard,
                      'mapped': relation is not None,
                      'evaluation_status': 'TECHNICAL_EVIDENCE' if evaluated else 'NOT_EVALUATED',
                      'organizational_status': 'PENDING_REVIEW' if relation else 'NOT_EVALUATED',
                      'rationale': relation['rationale'] if relation else '',
                      'additional_evidence': relation['additional_evidence'] if relation else 'Exige avaliação organizacional fora dos testes atuais do projeto.',
                      'benchmark_references': references,
                      'technical_passed': sum(ref['status'] == 'PASS' for ref in evaluated),
                      'technical_failed': sum(ref['status'] == 'FAIL' for ref in evaluated)})
    groups = {}
    for group in ('IG1', 'IG2', 'IG3'):
        subset = [item for item in items if group in item['implementation_groups']]
        groups[group] = {'total_safeguards': len(subset),
                         'mapped_safeguards': sum(item['mapped'] for item in subset),
                         'safeguards_with_technical_evidence': sum(item['evaluation_status'] == 'TECHNICAL_EVIDENCE' for item in subset),
                         'pending_review': sum(item['organizational_status'] == 'PENDING_REVIEW' for item in subset),
                         'not_evaluated': sum(item['organizational_status'] == 'NOT_EVALUATED' for item in subset)}
    return {'framework': catalog['framework'], 'version': catalog['version'],
            'source_document': catalog['source_document'], 'source_sha256': catalog['source_sha256'],
            'source_url': catalog['source_url'], 'license_url': catalog['license_url'],
            'mapping_origin': mapping['origin'], 'mapping_review_status': mapping['review_status'],
            'scope': 'Partial device configuration evidence; no organizational compliance determination.',
            'groups': groups, 'safeguards': items}
