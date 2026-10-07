"""Generate commented CLI previews for confirmed configuration failures."""
from .timezone import local_now
from collections import defaultdict


class RemediationEngine:
    def generate_script(self, failed_results):
        commands = [r for r in failed_results if r.status == "FAIL" and r.remediation_cli]
        lines = ["# FortiGate CIS Remediation Preview",
                 f"# Generated: {local_now().isoformat(timespec='seconds')}",
                 f"# Controls with commands: {len(commands)}",
                 "# Review commands, test in a lab and back up the configuration.",
                 "# All commands are commented; the auditor never executes them."]
        categories = defaultdict(list)
        for result in commands:
            categories[result.category or "General"].append(result)
        for category, results in sorted(categories.items()):
            lines.extend(["", *self._comments(f"Category: {category}")])
            for result in results:
                lines.extend(["", *self._comments(f"Rule {result.rule_id}: {result.title}"),
                              *self._comments(f"Current: {result.actual_value}"),
                              *self._comments(f"Expected: {result.expected_value}")])
                lines.extend(f"# [DRY-RUN] {line}" for line in result.remediation_cli.splitlines())
        return '\n'.join(lines) + '\n'

    @staticmethod
    def _comments(text):
        return [f"# {line}" for line in text.splitlines()]
