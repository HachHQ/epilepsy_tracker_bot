from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_oferta_source_describes_server_storage_and_user_control() -> None:
    text = (ROOT / "assets" / "oferta.txt").read_text(encoding="utf-8")
    assert "виртуальном сервере" in text
    assert "Удалить все данные навсегда" in text
    assert "Принимаю условия" in text
    assert "__SEIZURE_RETENTION_DAYS__" in text
    assert "__USER_RETENTION_DAYS__" in text
    assert "локальном сервере" not in text
    assert "публичной сети" not in text


def test_oferta_pdf_is_built() -> None:
    data = (ROOT / "assets" / "oferta.pdf").read_bytes()
    assert data.startswith(b"%PDF")
    assert b"__SEIZURE_RETENTION_DAYS__" not in data
    assert b"__USER_RETENTION_DAYS__" not in data
    assert len(data) > 5_000
