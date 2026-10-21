def affected_rows(result: object) -> int:
    rowcount = getattr(result, "rowcount", 0)
    return int(rowcount or 0)
