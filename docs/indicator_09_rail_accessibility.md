# Accessibility to active passenger rail gateways

## Why the implementation uses a versioned reference snapshot

The public RFI national station catalogue is dynamically rendered in the web
browser. A simple HTTP client does not reliably receive the full station table,
which makes automated scraping fragile.

For reproducibility, this project therefore stores a small, versioned reference
snapshot of **active passenger rail gateways relevant to the Canavese study
area**, verified against official RFI station pages and SFM Torino service
information.

The current snapshot includes nearby active gateways on the RFI/SFM network.
It deliberately excludes stations on the Rivarolo-Pont section while that
section is operated by replacement bus rather than passenger rail.

The SFM Torino page states that the Rivarolo-Chieri section of SFM1 is operated
by train, while Rivarolo-Pont Canavese is currently managed by bus.

## Indicator

For each of the 27 municipalities:

1. resolve official ISTAT municipality codes;
2. restrict candidate destinations to the validated active rail-gateway
   snapshot;
3. select the minimum ISTAT `TEP_TOT` road travel time;
4. retain `KM_TOT` as route-distance metadata.

This is a territorial access-to-rail indicator, not an indicator of rail
service quality.

## Limitations

The gateway snapshot should be reviewed whenever the regional railway timetable
or infrastructure operating status changes.

The indicator does not include:
- train frequency;
- journey time after boarding;
- timetable compatibility;
- replacement bus quality;
- access from individual hamlets.

Run:

`python scripts/finalize_rail_accessibility.py`

Outputs:

- `data/reference/canavese_active_rail_gateways.csv`
- `data/indicators/rail_accessibility_minutes.csv`
- `data/indicators/rail_accessibility_summary.csv`
