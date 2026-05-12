import re


CLOTHING_SIZE_ORDER = [
    ('XXS', '2XS', 'XX SMALL', 'EXTRA EXTRA SMALL'),
    ('XS', 'X SMALL', 'EXTRA SMALL'),
    ('S', 'SM', 'SMALL'),
    ('M', 'MED', 'MEDIUM'),
    ('L', 'LG', 'LARGE'),
    ('XL', 'X LARGE', 'EXTRA LARGE'),
    ('XXL', '2XL', 'XX LARGE', 'EXTRA EXTRA LARGE'),
    ('XXXL', '3XL', 'XXX LARGE', 'EXTRA EXTRA EXTRA LARGE'),
    ('ONE SIZE', 'ONESIZE', 'OS', 'O/S', 'FREE SIZE'),
]


def _normalize_size_label(value):
    return re.sub(r'\s+', ' ', re.sub(r'[_-]+', ' ', str(value or '').strip().upper()))


CLOTHING_SIZE_RANK = {
    _normalize_size_label(alias): rank
    for rank, aliases in enumerate(CLOTHING_SIZE_ORDER)
    for alias in aliases
}


def _natural_parts(value):
    parts = []
    for part in re.split(r'(\d+(?:\.\d+)?)', str(value or '').strip().lower()):
        if not part:
            continue
        if re.fullmatch(r'\d+(?:\.\d+)?', part):
            parts.append((1, float(part)))
        else:
            parts.append((0, part))
    return tuple(parts)


def size_sort_key(value):
    normalized = _normalize_size_label(value)
    rank = CLOTHING_SIZE_RANK.get(normalized)
    if rank is not None:
        return (0, rank, normalized)
    return (1, _natural_parts(value), normalized)
