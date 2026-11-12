"""Compatibility entry point: preview-only ERA5 CDD, never canonical promotion."""
from epah_diagnosis.experimental_previews import climate_main


def main(argv=None):
    return climate_main("cdd", argv)


if __name__ == "__main__":
    raise SystemExit(main())
