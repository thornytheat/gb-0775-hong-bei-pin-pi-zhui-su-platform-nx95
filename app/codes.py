INFORMATIONAL = frozenset({'RECEIPT_VARIANCE'})


def blocking(codes):
    return [code for code in codes if code not in INFORMATIONAL]


def is_blocked(codes):
    return bool(blocking(codes))
