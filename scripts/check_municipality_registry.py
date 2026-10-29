"""Validate the canonical 27 municipality ISTAT codes without network access."""
from pathlib import Path
from epah_diagnosis.cli import read_municipality_codes

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    mapping = read_municipality_codes(ROOT / "data" / "municipalities.csv")
    if len(mapping) != 27:
        raise ValueError(f"Expected 27 municipalities, found {len(mapping)}")
    print(f"Municipality registry: {len(mapping)} unique names and six-digit ISTAT codes")


if __name__ == "__main__":
    main()
