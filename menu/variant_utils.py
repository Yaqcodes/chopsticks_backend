"""Normalise MenuItem variant dimensions for product-scoped uniqueness checks.

Zmall apparel uses one ``size`` per SKU row and ``colors`` JSON. Two SKUs are
considered duplicates within a single grouped Product only when at least one
(size, colour) pair overlaps.
"""


def _normalise_token(value):
    if value is None:
        return ''
    return str(value).strip().lower()


def _list_from_value(value):
    """Coerce a JSONField value (list / string / None) into a list of strings."""
    if value is None:
        return []
    if isinstance(value, str):
        v = value.strip()
        return [v] if v else []
    if isinstance(value, (list, tuple, set)):
        out = []
        for v in value:
            if isinstance(v, dict):
                name = v.get('name')
                if name and str(name).strip():
                    out.append(str(name))
            elif v is not None and str(v).strip():
                out.append(str(v))
        return out
    return []


def _sizes(menuitem):
    t = _normalise_token(getattr(menuitem, 'size', ''))
    return [t] if t else ['']


def _colours(menuitem):
    colours = _list_from_value(getattr(menuitem, 'colors', None))
    seen = set()
    out = []
    for c in colours:
        n = _normalise_token(c)
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out or ['']


def variant_keys(menuitem):
    """Set of (size, colour) pairs the SKU represents.

    A SKU with no size/colour metadata still occupies a single ``('', '')``
    slot so two such SKUs collide if linked to the same Product.
    """
    sizes = _sizes(menuitem)
    colours = _colours(menuitem)
    return {(s, c) for s in sizes for c in colours}


def variant_keys_overlap(a, b):
    """True if any (size, colour) pair is shared by both SKUs."""
    return bool(variant_keys(a) & variant_keys(b))


def normalized_variant_size(menuitem):
    """Backward-compatible accessor (first non-empty size)."""
    return _sizes(menuitem)[0]


def primary_color_name_normalized(menuitem):
    """Backward-compatible accessor (first non-empty colour)."""
    return _colours(menuitem)[0]


def normalized_variant_tuple(menuitem):
    """Backward-compatible accessor (legacy single-pair key)."""
    return (normalized_variant_size(menuitem), primary_color_name_normalized(menuitem))
