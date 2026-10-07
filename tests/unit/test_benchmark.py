"""Regression cases grounded in the supplied 7.4.x PDF and offline limitations."""
import json
from tests import FIXTURE_PATH
import pytest
from cis_benchmark.audit import audit_content
from cis_benchmark.benchmark import detect_fortios_version
from cis_benchmark.config_parser import FortiGateConfigParser, cli_values
from cis_benchmark.rules import get_all_rules, get_level1_rules, get_level2_rules
from cis_benchmark.rules.base import RuleResult, CISLevel, RuleSeverity
from cis_benchmark.rules.guidance import EXPECTED
from cis_benchmark.scoring import ComplianceScorer
from cis_benchmark.reporting import HTMLReportGenerator, JSONReportGenerator

HEADER = '#config-version=FG200F-7.4.8-FW-build1234-test\n'


def section(kind, settings):
    return f'config {kind}\n{settings}\nend\n'


def edit(name, settings):
    return f'    edit "{name}"\n{settings}\n    next\n'


def result(rid, raw, **options):
    rule = next(r for r in get_all_rules('7.4', options=options) if r.rule_id == rid)
    return rule.evaluate(FortiGateConfigParser().parse_content(raw))


def test_pdf_inventory_and_renumbering():
    rules = get_all_rules('7.4')
    assert len(rules) == 64
    assert len(get_level1_rules('7.4')) == 39
    assert len(get_level2_rules('7.4')) == 25
    ids = {r.rule_id for r in rules}
    assert ids == set(EXPECTED)
    assert {'2.1.13', '2.3.3', '2.3.4', '2.5.4', '4.2.7', '7.3.2', '7.3.3'} <= ids
    assert {'4.4.2', '4.4.3', '4.4.4', '6.2.1'}.isdisjoint(ids)
    assert next(r for r in rules if r.rule_id == '4.4.1').title == 'Create a Web Filtering Profile'
    assert next(r for r in rules if r.rule_id == '4.5.1').item['assessment'] == 'Manual'
    assert all(r.item['source_page'] > 0 for r in rules)


@pytest.mark.parametrize('version,family', [('7.4.8','7.4.8'), ('7.04','7.4'), ('7.0.19','7.0.19')])
def test_header_version(version, family):
    assert detect_fortios_version(HEADER.replace('7.4.8', version)) == family


@pytest.mark.parametrize('version', ['7.0.19', '7.2.8', '7.6.1', '8.0.0'])
def test_incompatible_family_rejected(version):
    with pytest.raises(ValueError, match='sem benchmark'):
        audit_content(HEADER.replace('7.4.8', version) + section('system global', 'set hostname test'))


def test_untrusted_embedded_version_cannot_select_benchmark():
    with pytest.raises(ValueError):
        audit_content(section('system global', 'set hostname "FortiOS v7.4.8"'))


@pytest.mark.parametrize('rid,kind,setting,ok,bad', [
    ('2.1.1','system global','pre-login-banner','enable','disable'),
    ('2.1.2','system global','post-login-banner','enable','disable'),
    ('2.1.8','system global','ssl-static-key-ciphers','disable','enable'),
    ('2.1.9','system global','strong-crypto','enable','disable'),
    ('2.1.10','system global','admin-https-ssl-versions','tlsv1-3','tlsv1-2 tlsv1-3'),
    ('2.1.11','system global','gui-cdn-usage','enable','disable'),
    ('2.1.12','system global','log-single-cpu-high','enable','disable'),
    ('2.1.13','system global','gui-display-hostname','disable','enable'),
    ('2.4.4','system global','admintimeout','15','16'),
    ('4.2.4','antivirus settings','machine-learning-detection','enable','disable'),
    ('4.2.5','antivirus settings','grayware','enable','disable'),
])
def test_exact_settings_positive_and_negative(rid, kind, setting, ok, bad):
    assert result(rid, section(kind, f'set {setting} {ok}')).status == 'PASS'
    assert result(rid, section(kind, f'set {setting} {bad}')).status == 'FAIL'
    assert result(rid, '').status == 'MANUAL_REVIEW'


@pytest.mark.parametrize('length,scope,status', [
    (14, 'admin-password ipsec-preshared-key', 'PASS'),
    (13, 'admin-password ipsec-preshared-key', 'FAIL'),
    (20, 'admin-password', 'FAIL'),
])
def test_password_criteria(length, scope, status):
    raw = section('system password-policy', f'set status enable\nset minimum-length {length}\nset apply-to {scope}')
    assert result('2.2.1', raw).status == status


def test_default_admin_removal_and_incomplete_inventory():
    assert result('2.4.1', section('system admin', edit('admin', 'set password ENC FAKE'))).status == 'FAIL'
    assert result('2.4.1', section('system admin', edit('operator', 'set accprofile super_admin'))).status == 'PASS'
    assert result('2.4.1', '').status == 'MANUAL_REVIEW'


@pytest.mark.parametrize('hosts,status', [('','FAIL'), ('set trusthost1 0.0.0.0 0.0.0.0','FAIL'),
                                        ('set trusthost1 10.0.0.0 255.255.255.0','MANUAL_REVIEW')])
def test_admin_trusted_hosts(hosts, status):
    assert result('2.4.2', section('system admin', edit('operator', hosts))).status == status


def test_ntp_requires_runtime_evidence():
    assert result('2.1.4', section('system ntp', 'set ntpsync disable')).status == 'FAIL'
    assert result('2.1.4', section('system ntp', 'set ntpsync enable')).status == 'MANUAL_REVIEW'


def test_syslog_cannot_borrow_interface_status():
    raw = section('log syslogd setting', 'set status disable\nset server 192.0.2.1')
    raw += section('system interface', edit('lan', 'set status enable'))
    assert result('7.2.1', raw).status == 'FAIL'


def test_virtual_patch_checks_every_permissive_policy():
    raw = section('firewall local-in-policy', edit('1', 'set action accept\nset virtual-patch enable') + edit('2','set action accept\nset virtual-patch disable'))
    assert result('2.4.8', raw).status == 'FAIL'
    assert result('2.4.8', raw.replace('virtual-patch disable', 'virtual-patch enable')).status == 'PASS'


def test_ha_modes_and_nested_management():
    standalone = section('system ha', 'set mode standalone')
    assert result('2.5.1', standalone).status == 'FAIL'
    assert result('2.5.3', standalone).status == 'NOT_APPLICABLE'
    raw = section('system ha', 'set mode a-p\nset group-id 0\nset ha-mgmt-status enable\n' + section('ha-mgmt-interfaces', edit('1','set interface mgmt\nset gateway 192.0.2.1')))
    assert result('2.5.3', raw).status == 'PASS'
    assert result('2.5.4', raw).status == 'FAIL'
    assert result('2.5.4', raw.replace('group-id 0','group-id 10')).status == 'PASS'


def test_ha_does_not_expose_password():
    raw = section('system ha','set mode a-p\nset group-name cluster\nset password ENC TEST_SECRET\nset hbdev port10 50')
    r = result('2.5.1', raw)
    assert r.status == 'MANUAL_REVIEW'
    assert 'TEST_SECRET' not in json.dumps(r.to_dict())


def test_vdom_scoping_and_duplicate_policy_ids():
    def vdom(name, service):
        return edit(name, section('firewall policy', edit('1',f'set action accept\nset service "{service}"')))
    raw = section('vdom', vdom('root','HTTPS') + vdom('customer','ALL'))
    c = FortiGateConfigParser().parse_content(raw)
    assert len(c.get_blocks('firewall policy')) == 2
    r = result('3.2', raw)
    assert r.status == 'FAIL'
    assert 'vdom:customer/1' in r.actual_value
    assert 'vdom:root/1' not in r.actual_value


def test_multivalue_quoting_and_nested_profiles():
    raw = section('application list', edit('profile with spaces', section('entries', edit('1','set category 2 6\nset action block'))))
    p = FortiGateConfigParser().parse_content(raw).get_block('application list').entries()[0]
    assert p.name == 'profile with spaces'
    assert p.get_sub_block('entries').entries()[0].get('action') == 'block'
    assert 'action' not in p.settings
    assert cli_values('"wan one" "wan two"') == ['wan one','wan two']


@pytest.mark.parametrize('raw', ['config system global\nset hostname test',
                               'config system global\nedit admin\nend', 'next'])
def test_malformed_configs_are_rejected(raw):
    with pytest.raises(ValueError):
        FortiGateConfigParser().parse_content(raw)


def test_multiline_certificate_does_not_create_config_blocks():
    raw = section('vpn certificate local', edit('cert','set certificate "line1\nconfig system global\nline3"'))
    c = FortiGateConfigParser().parse_content(raw)
    assert not c.get_blocks('system global')
    assert 'config system global' in c.get_block('vpn certificate local').entries()[0].get('certificate')


def test_missing_vdom_policy_export_is_pending():
    raw = section('vdom', edit('root', section('firewall policy', edit('1','set action accept\nset service HTTPS'))) + edit('missing',''))
    assert result('3.2', raw).status == 'MANUAL_REVIEW'


def test_profiles_need_utm_and_same_vdom_definition():
    policy = edit('1','set action accept\nset application-list profile\nset utm-status disable')
    raw = section('firewall policy', policy) + section('application list', edit('profile','set enforce-default-app-port enable'))
    assert result('4.5.4', raw).status == 'FAIL'
    assert result('4.5.4', raw.replace('utm-status disable','utm-status enable')).status == 'MANUAL_REVIEW'


def test_snmp_per_user_query_and_agent():
    raw = section('system snmp user', edit('v3', 'set queries enable'))
    assert result('2.3.3', raw).status == 'FAIL'
    assert result('2.3.3', raw.replace('queries enable','queries disable')).status == 'PASS'
    assert result('2.3.1', section('system snmp sysinfo','set status disable')).status == 'FAIL'


def test_pdf_ambiguities_never_auto_pass():
    for rid in ('2.3.4','7.3.2','7.3.3'):
        assert result(rid, '').status == 'MANUAL_REVIEW'


def test_time_zone_expected_context():
    raw = section('system global','set timezone 12')
    assert result('2.1.3', raw).status == 'MANUAL_REVIEW'
    assert result('2.1.3', raw, expected_timezone='12').status == 'PASS'
    assert result('2.1.3', raw, expected_timezone='5').status == 'FAIL'


def test_scoring_coverage_and_pending_not_failed():
    statuses = ['PASS','FAIL','MANUAL_REVIEW','NOT_APPLICABLE','ERROR']
    results = [RuleResult(str(i),'test',CISLevel.LEVEL_1,RuleSeverity.MEDIUM,s=='PASS','desc','expected','actual','fix',evaluation_status=s) for i,s in enumerate(statuses)]
    r = ComplianceScorer().calculate(results)
    assert r.total_rules == 5 and r.evaluated_rules == 2
    assert r.failed_rules == 1 and len(r.failed_results) == 1
    assert r.overall_percentage == 50 and r.coverage_percentage == 50
    assert r.risk_rating == 'Incomplete'
    assert r.manual_review_rules == r.not_applicable_rules == r.error_rules == 1


def test_service_report_metadata_and_escaping():
    r = audit_content(HEADER + section('system global','set hostname "<script>alert(1)</script>"'))
    assert r.total_rules == 64
    assert r.source_sha256 and r.fortios_version == '7.4.8'
    html = HTMLReportGenerator().generate(r, config_file='<img src=x>')
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html and '&lt;img src=x&gt;' in html
    assert '7.4.x v1.0.1' in html
    data = json.loads(JSONReportGenerator().generate(r))
    assert data['metadata']['benchmark'] == r.benchmark
    assert all(x['source_page'] > 0 for x in data['compliance']['results'])


def test_service_level_filter_and_validation():
    raw = HEADER + section('system global','set hostname test')
    assert audit_content(raw,'1').total_rules == 39
    assert audit_content(raw,'2').total_rules == 25
    with pytest.raises(ValueError):
        audit_content(raw,'invalid')


def test_fixture_evaluates_every_pdf_control_without_internal_errors():
    content = FIXTURE_PATH.read_text()
    report = audit_content(content)
    assert len(report.results) == 64
    assert report.error_rules == 0
    assert report.manual_review_rules > 0
    assert report.passed_rules + report.failed_rules + report.manual_review_rules + report.not_applicable_rules == 64


def test_outbreak_prevention_checks_protocol_action():
    def profile(action):
        return section('antivirus profile', edit('av', section('http', 'set outbreak-prevention ' + action)))
    assert result('4.2.3', profile('block')).status == 'PASS'
    assert result('4.2.3', profile('monitor')).status == 'FAIL'


def test_sandbox_requires_global_and_per_protocol_enforcement():
    raw = section('system fortiguard','set sandbox-inline-scan enable')
    raw += section('firewall policy', edit('1','set action accept\nset utm-status enable\nset av-profile av'))
    raw += section('antivirus profile', edit('av', 'set feature-set proxy\nset fortisandbox-mode inline\n' + section('http','set fortisandbox block')))
    assert result('4.2.6',raw).status == 'PASS'
    assert result('4.2.6',raw.replace('fortisandbox block','fortisandbox monitor')).status == 'FAIL'
    assert result('4.2.6',raw.replace('sandbox-inline-scan enable','sandbox-inline-scan disable')).status == 'FAIL'


def test_ssl_vpn_tls_and_explicit_nonapplicability():
    raw = section('vpn ssl settings','set status enable\nset ssl-min-proto-ver tls1-2\nset ssl-max-proto-ver tls1-3\nset algorithm high')
    assert result('6.1.2',raw).status == 'PASS'
    assert result('6.1.2',raw.replace('tls1-2','tls1-1')).status == 'FAIL'
    assert result('6.1.2',raw.replace('status enable','status disable')).status == 'NOT_APPLICABLE'
    assert result('6.1.1',section('vpn ssl settings','set servercert company-cert')).status == 'MANUAL_REVIEW'


def test_known_defaults_and_unknown_omissions():
    assert result('2.1.9',section('system global','')).status == 'PASS'
    assert result('2.1.10',section('system global','')).status == 'FAIL'
    assert result('2.1.4',section('system ntp','')).status == 'MANUAL_REVIEW'
    assert result('2.1.9','').status == 'MANUAL_REVIEW'


def test_profile_override_cannot_bypass_admin_timeout():
    raw = section('system global','set admintimeout 5')
    raw += section('system accprofile',edit('override','set admintimeout-override enable\nset admintimeout 60'))
    assert result('2.4.4',raw).status == 'FAIL'


def test_remediation_only_for_confirmed_failures_and_admin_template_requires_review():
    r = result('2.1.10',section('system global','set admin-https-ssl-versions tlsv1-2'))
    assert 'set admin-https-ssl-versions tlsv1-3' in r.remediation_cli
    assert not result('2.1.10','').remediation_cli
    admin = result('2.4.1',section('system admin',edit('admin','set password ENC FAKE')))
    assert '<NOVO_ADMIN>' in admin.remediation_cli
    assert 'após testar o acesso' in admin.remediation_cli


def test_compromised_host_requires_linked_enabled_stitch():
    raw = section('system automation-trigger',edit('Compromised Host - High',''))
    raw += section('system automation-action',edit('quarantine','set action-type quarantine'))
    raw += section('system automation-stitch',edit('host-quarantine','set status enable\nset trigger "Compromised Host - High"\n' + section('actions',edit('1','set action quarantine'))))
    assert result('5.1.1',raw).status == 'PASS'
    assert result('5.1.1',raw.replace('status enable','status disable')).status == 'FAIL'
    assert result('5.1.1',raw.replace('set action quarantine','set action missing')).status == 'FAIL'


@pytest.mark.parametrize('rid', ['3.4', '4.1.1', '4.2.2', '4.2.3', '4.2.6', '4.3.2', '4.3.3', '4.5.2', '5.1.1', '6.1.1'])
def test_additional_cli_templates_only_attached_to_failures(rid, monkeypatch):
    from cis_benchmark.rules import registry
    from cis_benchmark.remediation import RemediationEngine
    config = FortiGateConfigParser().parse_content(HEADER)
    rule = next(r for r in get_all_rules() if r.rule_id == rid)
    monkeypatch.setattr(registry, 'evaluate', lambda *args: ('FAIL', 'fixture violation'))
    failure = rule.evaluate(config)
    assert 'config ' in failure.remediation_cli
    assert '<' in failure.remediation_cli
    assert 'Substitua todos' in failure.remediation
    script = RemediationEngine().generate_script([failure])
    assert all(not line or line.startswith('#') for line in script.splitlines())
    monkeypatch.setattr(registry, 'evaluate', lambda *args: ('MANUAL_REVIEW', 'pending evidence'))
    assert not rule.evaluate(config).remediation_cli
