"""Select only a benchmark matching the detected FortiOS family."""
import re
import json
from dataclasses import dataclass
from pathlib import Path

FAMILY = "7.4"
NAME = "CIS FortiGate 7.4.x v1.0.1"
SOURCE_DOCUMENT = "CIS_FortiGate_7.4.x_Benchmark_v1.0.1.pdf"
SOURCE_SHA256 = "639f91a8fb583246d4850d1d2a91c582057e7adb65db6ce9aff25c8dd523c723"
CATALOG = json.loads((Path(__file__).parent / "rules/catalog.json").read_text(encoding="utf-8"))


@dataclass(frozen=True)
class BenchmarkSelection:
    supported: bool
    fortios_version: str
    benchmark: str
    message: str


def detect_fortios_version(raw_config):
    header = re.split(r'(?im)^\s*config\s+', raw_config[:20000], maxsplit=1)[0]
    patterns = [r'(?m)^#config-version=[\w-]+?-([\d.]+)-FW-',
                r'(?m)^\s*FortiOS\s+v?(\d+\.\d+\.\d+)',
                r'(?m)^\s*Version:\s*FortiGate[^\n]*?\bv(\d+\.\d+\.\d+)']
    for pattern in patterns:
        m = re.search(pattern, header, re.I)
        if m:
            version = m[1]
            # Compact backup headers: 7.4.8 can be encoded as 7.4 or 7.04.
            pieces = version.split('.')
            if len(pieces) >= 2:
                return '.'.join(str(int(p)) for p in pieces)
    return ""


def select_benchmark(raw_config):
    version = detect_fortios_version(raw_config)
    family = '.'.join(version.split('.')[:2])
    if family == FAMILY:
        return BenchmarkSelection(True, version, NAME, "Benchmark selecionado pela família FortiOS.")
    return BenchmarkSelection(False, version or "unknown", "unsupported",
                              "Versão desconhecida ou sem benchmark implementado. Exporte o cabeçalho do backup; suportado: 7.4.x. Não aplicar regras 7.4 a outra família.")
