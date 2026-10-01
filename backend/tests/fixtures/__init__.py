from pathlib import Path

FIXTURES = Path(__file__).parent
CRICSHEET = FIXTURES / "cricsheet"
FINAL, SUPER_OVER, DLS, NO_RESULT = 1535465, 1529281, 1529293, 1527685
ALL_MATCHES = (FINAL, SUPER_OVER, DLS, NO_RESULT)


def cricsheet_json(match_id: int) -> bytes:
    return (CRICSHEET / f"{match_id}.json").read_bytes()
