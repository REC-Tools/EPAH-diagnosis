"""Keep untrusted source text literal in spreadsheet-oriented exports."""


def spreadsheet_safe_cell(value):
    if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + value
    return value
