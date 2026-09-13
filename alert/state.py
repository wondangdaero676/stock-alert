import json
from pathlib import Path

SENT_FILE = Path("state/sent.json")


def load_sent() -> dict[str, str]:
    """규칙 키 → 마지막으로 알림을 보낸 거래일"""
    if not SENT_FILE.exists():
        return {}
    return json.loads(SENT_FILE.read_text(encoding="utf-8"))


def save_sent(sent: dict[str, str]) -> None:
    SENT_FILE.parent.mkdir(exist_ok=True)
    SENT_FILE.write_text(json.dumps(sent, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
