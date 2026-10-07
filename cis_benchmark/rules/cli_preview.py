"""Bind known object identifiers without inventing operational parameters."""
import json

OBJECTS = {
    '1.3': ('system interface', '<INTERFACE_WAN>'),
    '2.4.2': ('system admin', '<CONTA_ADMINISTRATIVA>'),
    '2.4.5': ('system interface', '<INTERFACE_AFETADA>'),
    '2.4.8': ('firewall local-in-policy', '<ID_LOCAL_IN_POLICY>'),
    '3.2': ('firewall policy', '<ID_POLITICA>'),
    '3.4': ('firewall policy', '<ID_POLITICA>'),
    '4.1.1': ('firewall policy', '<ID_POLITICA>'),
    '4.2.2': ('firewall policy', '<ID_POLITICA>'),
    '4.2.3': ('antivirus profile', '<PERFIL_ANTIVIRUS>'),
    '4.3.2': ('dnsfilter profile', '<PERFIL_DNS_FILTER>'),
    '4.3.3': ('firewall policy', '<ID_POLITICA>'),
    '4.5.2': ('application list', '<PERFIL_APPLICATION_CONTROL>'),
}


def bind_objects(config, rule_id, affected_objects, template):
    if rule_id not in OBJECTS:
        return template
    kind, placeholder = OBJECTS[rule_id]
    scripts = []
    for parent in config.get_blocks(kind):
        for obj in parent.entries():
            target = {'kind': obj.block_type, 'name': obj.name, 'scope': obj.scope}
            if target not in affected_objects:
                continue
            # JSON quoting preserves spaces and prevents names becoming CLI syntax.
            quoted = json.dumps(obj.name, ensure_ascii=False)
            script = template.replace(f'"{placeholder}"', quoted).replace(placeholder, quoted)
            if obj.scope.startswith('vdom:'):
                vdom = json.dumps(obj.scope.split(':', 1)[1], ensure_ascii=False)
                script = f'config vdom\n    edit {vdom}\n{script}\n    next\nend'
            elif config.vdom_names:
                script = f'config global\n{script}\nend'
            scripts.append(script)
            if len(scripts) == 32:
                return '\n\n'.join(scripts) + '\n# Limite de 32 objetos: revise os demais na evidência.'
    return '\n\n'.join(scripts) if scripts else template
