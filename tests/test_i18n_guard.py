import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = ("handlers", "keyboards")
CYRILLIC = re.compile(r"[А-Яа-яЁё]")
STRING_LITERAL = re.compile(r"""(['"])(?:(?=(\\?))\2.)*?\1""")


def _is_excluded_line(line: str) -> bool:
    stripped = line.strip()
    return (
        not stripped
        or stripped.startswith("#")
        or "print(" in line
        or "logger." in line
    )


def _find_offenders() -> list[str]:
    offenders: list[str] = []
    for dirname in SCAN_DIRS:
        for path in sorted((ROOT / dirname).rglob("*.py")):
            for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if _is_excluded_line(line):
                    continue
                for match in STRING_LITERAL.finditer(line):
                    if CYRILLIC.search(match.group(0)):
                        rel = path.relative_to(ROOT)
                        offenders.append(f"{rel}:{lineno}: {line.strip()}")
                        break
    return offenders


def test_no_hardcoded_cyrillic_in_handlers_and_keyboards() -> None:
    offenders = _find_offenders()
    assert not offenders, "Move UI strings to locales/:\n" + "\n".join(offenders[:40])
