"""Compatibility entry point for the unchanged UTCI heat source audit."""
from epah_diagnosis.utci_heat_source_v0_5 import THRESHOLDS, digest, inspect, main

if __name__ == '__main__':
    raise SystemExit(main())
