"""Explicitly requested historical rental preview; original counts stay untouched."""
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
import hashlib
from .tenure_source_review_v0_5 import metadata_profile, inspect_response

EXPECTED_RESIDUALS = {"001091": "0.000001", "001107": "0.000001", "001121": "-0.000001", "001212": "-0.000001", "001238": "-0.000001", "001288": "0.000001"}


def calculate_review(review):
    """Calculate only the reviewed same-year, same-universe fraction."""
    if (review['source_periods'] != ['2021'] or not review['denominator_note_present']
            or review['denominator_universe']['id'] != 'TIT_POSSESSO__ALL_N1'
            or set(review['review_issues']) - {'partition_not_exact_no_tolerance_applied'}):
        raise ValueError('Rental preview requires the reviewed 2021 universe and no new source issues')
    observations = review['observations']
    values = {o['source_key']['TENURE_STATUS_HOU']: o['value_as_received'] for o in observations}
    if (len(observations) != 4 or set(values) != {'ALL', 'RENT', 'OWN', 'OTH_OR'}
            or any(o['period'] != '2021' for o in observations)
            or any(not isinstance(v, str) for v in values.values())):
        raise ValueError('Four explicit same-year source counts required')
    numbers = {k: Decimal(v) for k, v in values.items()}
    if (any(not v.is_finite() or v < 0 for v in numbers.values())
            or numbers['ALL'] <= 0 or numbers['RENT'] > numbers['ALL']):
        raise ValueError('Invalid rental numerator or denominator')
    with localcontext() as ctx:
        ctx.prec = 50
        ctx.rounding = ROUND_HALF_EVEN
        # Preserve source precision; refuse inputs beyond this preview implementation.
        if any(len(v.as_tuple().digits) + abs(v.as_tuple().exponent) > 40 for v in numbers.values()):
            raise ValueError('Source precision requires review')
        residual = numbers['ALL'] - sum((numbers[k] for k in ['OWN', 'RENT', 'OTH_OR']), Decimal(0))
        if residual != Decimal(review['partition_difference_as_received']):
            raise ValueError('Residual differs from inspected source')
        value = str(100 * numbers['RENT'] / numbers['ALL'])
    return {'period': '2021', 'rent': values['RENT'], 'all': values['ALL'],
            'own': values['OWN'], 'oth_or': values['OTH_OR'], 'value': value,
            'residual': review['partition_difference_as_received'], 'has_residual': residual != 0}


def derive(pack, snapshot, source_url):
    hashes = {}
    def read(relative):
        raw = (pack / relative).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if snapshot['source_sha256'].get(relative) != digest:
            raise ValueError('Rental original changed since source audit')
        hashes[relative] = digest
        return raw
    profile = metadata_profile(read('sources/tenure/inputs/metadata.xml'))
    rows, diagnostics = [], []
    municipalities = snapshot['municipalities']
    if len(municipalities) != 27 or len({m['istat_code'] for m in municipalities}) != 27:
        raise ValueError('Rental preview requires the exact audited 27 municipalities')
    for m in municipalities:
        code = m['istat_code']
        review = inspect_response(read(f'sources/tenure/raw/{code}.xml'), code, profile)
        result = {**calculate_review(review), 'geo_code': code, 'geo_name': m['municipality']}
        diagnostics.append(result)
        rows.append(dict(indicator_id='V05-19', geo_code=code, geo_name=m['municipality'],
                         scope='municipality_target_not_verified', period='2021',
                         series='Anteprima tecnica 100 × RENT / ALL', unit='percent',
                         value=result['value'], missing_reason=None, source_url=source_url,
                         source_note=f"Calcolo tecnico 2021; RENT={result['rent']}; ALL={result['all']}; residuo ALL−(OWN+RENT+OTH_OR)={result['residual']}. Nessuna correzione. Universo: famiglie senza tetto escluse; conteggi decimali da chiarire. Non è il 2025 né una prevalenza di povertà energetica."))
    residuals = {r['geo_code']: r['residual'] for r in diagnostics if r['has_residual']}
    if residuals != EXPECTED_RESIDUALS:
        raise ValueError('Residual pattern changed: this preview authorizes only the six reviewed residuals')
    return rows, {'formula': '100 * RENT / ALL', 'period': '2021', 'target_analysis_year': 2025,
                  'decimal_precision': 50, 'rounding': 'ROUND_HALF_EVEN',
                  'residual_definition': 'ALL - (OWN + RENT + OTH_OR)',
                  'residual_count': len(residuals), 'source_sha256': hashes,
                  'universe': profile['denominator_note'], 'rows': diagnostics,
                  'authorization_scope': 'Anteprima tecnica richiesta esplicitamente il 2026-11-24; nessuna approvazione scientifica o pubblicazione.'}
