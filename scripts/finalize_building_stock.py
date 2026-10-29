"""Legacy dual-source building-stock pipeline: intentionally disabled.

Use scripts/prepare_building_stock.py followed by independently reviewed
scripts/finalize_building_stock_single_source.py. This script must not update
verification_matrix.csv without a current documented review.
"""
raise SystemExit(
    "Legacy building-stock finalizer disabled. Use "
    "scripts/prepare_building_stock.py followed by "
    "scripts/finalize_building_stock_single_source.py --approval FILE."
)
