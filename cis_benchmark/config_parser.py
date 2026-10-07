"""Parse FortiGate exports while preserving config/edit hierarchy and VDOM scope."""
import logging
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
MAX_CONFIG_SIZE_MB = 50
MAX_CONFIG_SIZE_BYTES = MAX_CONFIG_SIZE_MB * 1024 * 1024


@dataclass
class ConfigBlock:
    block_type: str
    name: str = ""
    settings: Dict[str, str] = field(default_factory=dict)
    sub_blocks: List["ConfigBlock"] = field(default_factory=list)
    raw_text: str = ""
    scope: str = "global"
    is_edit: bool = False

    def get(self, key, default=""):
        return self.settings.get(key, default)

    def has(self, key):
        return key in self.settings

    def get_sub_block(self, block_type):
        return next((b for b in self.sub_blocks if b.block_type.lower() == block_type.lower()), None)

    def entries(self):
        return [b for b in self.sub_blocks if b.is_edit]


@dataclass
class FortiGateConfig:
    raw_content: str
    version: str = ""
    build: str = ""
    model: str = ""
    hostname: str = ""
    blocks: Dict[str, List[ConfigBlock]] = field(default_factory=dict)
    vdom_names: List[str] = field(default_factory=list)
    parse_warnings: List[str] = field(default_factory=list)

    def get_blocks(self, block_type):
        return self.blocks.get(' '.join(block_type.lower().split()), [])

    def get_block(self, block_type):
        return next(iter(self.get_blocks(block_type)), None)

    def get_global_setting(self, key, default=""):
        b = self.get_block("system global")
        return b.get(key, default) if b else default

    def has_global_setting(self, key):
        b = self.get_block("system global")
        return b.has(key) if b else False

    def get_policy_blocks(self):
        return self.get_blocks("firewall policy")

    def get_interface_blocks(self):
        return self.get_blocks("system interface")

    def get_admin_blocks(self):
        return self.get_blocks("system admin")

    def search(self, pattern, flags=re.I | re.M):
        try:
            return bool(re.search(pattern, self.raw_content, flags))
        except re.error:
            return False

    def search_value(self, pattern, group=1, flags=re.I | re.M):
        try:
            m = re.search(pattern, self.raw_content, flags)
            return m.group(group) if m else None
        except (re.error, IndexError):
            return None


def cli_values(value):
    return shlex.split(str(value), comments=False, posix=True)


def decode_config(data):
    """Decode terminal exports, including Windows Unicode text files."""
    if data.startswith((b'\xff\xfe\x00\x00', b'\x00\x00\xfe\xff')):
        encoding = 'utf-32'
    elif data.startswith((b'\xff\xfe', b'\xfe\xff')):
        encoding = 'utf-16'
    else:
        encoding = 'utf-8-sig'
    try:
        return data.decode(encoding)
    except UnicodeDecodeError:
        if encoding != 'utf-8-sig':
            raise ValueError("Arquivo Unicode inválido; salve novamente como texto UTF-8.")
        return data.decode('latin-1')


class FortiGateConfigParser:
    FORTIGATE_MARKERS = [r'(?m)^\s*config\s+system\s+global\s*$', r'(?m)^\s*config\s+system\s+interface\s*$',
                        r'(?m)^\s*config\s+firewall\s+policy\s*$', r'(?m)^\s*config\s+system\s+admin\s*$',
                        r'(?m)^\s*set\s+hostname\s+', r'(?m)^\s*#config-version=']

    def validate_config(self, content):
        return sum(bool(re.search(m, content, re.I)) for m in self.FORTIGATE_MARKERS) >= 2

    def parse_file(self, filepath):
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {filepath}")
        if not path.is_file():
            raise ValueError(f"Path is not a file: {filepath}")
        if path.stat().st_size > MAX_CONFIG_SIZE_BYTES:
            raise ValueError("Config file too large; maximum: 50MB")
        if not path.stat().st_size:
            raise ValueError("Config file is empty")
        data = path.read_bytes()
        content = decode_config(data)
        return self.parse_content(content)

    def parse_content(self, content):
        if len(content.encode("utf-8")) > MAX_CONFIG_SIZE_BYTES:
            raise ValueError("Config content too large; maximum: 50MB")
        content = content.lstrip('\ufeff').replace('\x00', '')
        config = FortiGateConfig(raw_content=content)
        m = re.search(r'#config-version=([\w-]+?)-([\d.]+)-FW-build(\d+)', content)
        if m:
            config.model, config.version, config.build = m.groups()
        self._warnings = []
        config.blocks = self._parse_all_blocks(content)
        config.parse_warnings = self._warnings
        config.hostname = config.get_global_setting("hostname")
        config.vdom_names = [e.name for b in config.get_blocks("vdom") for e in b.entries()]
        return config

    def _parse_all_blocks(self, content):
        self._warnings = []
        blocks = {}
        stack = []
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('#'):
                i += 1
                continue
            start = re.match(r'^config\s+(.+)$', line, re.I)
            edit = re.match(r'^edit\s+(.+)$', line, re.I)
            if start:
                if len(stack) >= 128:
                    raise ValueError("Config nesting exceeds 128 levels")
                kind = " ".join(start[1].lower().split())
                scope = stack[-1][0].scope if stack else "global"
                b = ConfigBlock(block_type=kind, scope=scope)
                if stack:
                    stack[-1][0].sub_blocks.append(b)
                blocks.setdefault(kind, []).append(b)
                stack.append((b, i))
            elif edit:
                if not stack or stack[-1][0].is_edit:
                    raise ValueError(f"Unexpected edit at line {i + 1}")
                parent = stack[-1][0]
                names = cli_values(edit[1])
                if len(names) != 1:
                    raise ValueError(f"Invalid edit name at line {i + 1}")
                scope = f"vdom:{names[0]}" if parent.block_type == "vdom" else parent.scope
                b = ConfigBlock(parent.block_type, name=names[0], scope=scope, is_edit=True)
                parent.sub_blocks.append(b)
                stack.append((b, i))
            elif line.lower() in ("next", "end"):
                if not stack:
                    raise ValueError(f"Unexpected {line} at line {i + 1}")
                b, first = stack[-1]
                if (line.lower() == "next") != b.is_edit:
                    raise ValueError(f"Unclosed config/edit before {line} at line {i + 1}")
                b.raw_text = '\n'.join(lines[first:i + 1])
                stack.pop()
            elif re.match(r'^(set|unset)\s+', line, re.I):
                if not stack:
                    raise ValueError(f"Setting outside config at line {i + 1}")
                parts = line.split(None, 2)
                key = parts[1].lower()
                value = parts[2] if len(parts) > 2 else ""
                if parts[0].lower() == "unset":
                    # Omitted and unset values have the same version-specific default.
                    stack[-1][0].settings.pop(key, None)
                else:
                    while True:
                        try:
                            tokens = cli_values(value)
                            break
                        except ValueError:
                            i += 1
                            if i >= len(lines):
                                raise ValueError("Unterminated quoted value")
                            value += '\n' + lines[i]
                    stack[-1][0].settings[key] = tokens[0] if len(tokens) == 1 else value
            else:
                # Terminal status/prompt lines outside configuration are harmless.
                if stack and len(self._warnings) < 100:
                    self._warnings.append(f"Linha {i + 1}: comando não interpretado em {stack[-1][0].block_type}.")
            i += 1
        if stack:
            raise ValueError("Configuration contains unclosed config/edit blocks")
        return blocks

    def extract_section_text(self, content, section_name):
        return '\n'.join(b.raw_text for b in self._parse_all_blocks(content).get(section_name.lower(), []))

    def get_all_edit_entries(self, config, block_type):
        return [e for b in config.get_blocks(block_type) for e in b.entries()]
