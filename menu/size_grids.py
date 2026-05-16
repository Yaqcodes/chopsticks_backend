"""
Canonical storefront size grids for categories that use fixed EU shoe or S–XL letter sizing.

Other categories keep flexible sizing (perfume volume, ONE SIZE, etc.) — size_grid blank.
"""

SIZE_GRID_NONE = ''
SIZE_GRID_SHOE_EU = 'shoe_eu'
SIZE_GRID_CLOTHING_S_XL = 'clothing_s_xl'

SIZE_GRID_CHOICES = [
    (SIZE_GRID_NONE, 'Flexible (sizes from variants only)'),
    (SIZE_GRID_SHOE_EU, 'Shoes — EU 40–47'),
    (SIZE_GRID_CLOTHING_S_XL, 'Apparel — S, M, L, XL'),
]

SHOE_EU_DISPLAY_GRID = ['40', '41', '42', '43', '44', '45', '46', '47']
CLOTHING_S_XL_DISPLAY_GRID = ['S', 'M', 'L', 'XL']

_SIZE_GRID_VALUES = {
    SIZE_GRID_SHOE_EU: SHOE_EU_DISPLAY_GRID,
    SIZE_GRID_CLOTHING_S_XL: CLOTHING_S_XL_DISPLAY_GRID,
}

# Default backfill when migrating existing Zmall categories (slug → size_grid).
DEFAULT_SIZE_GRID_BY_CATEGORY_SLUG = {
    'shoes': SIZE_GRID_SHOE_EU,
    'pants': SIZE_GRID_CLOTHING_S_XL,
    'dresses': SIZE_GRID_CLOTHING_S_XL,
    'shirts': SIZE_GRID_CLOTHING_S_XL,
}


def get_size_grid_values(size_grid):
    """Return fixed display sizes for a grid key, or None when flexible."""
    key = (size_grid or '').strip()
    if not key:
        return None
    values = _SIZE_GRID_VALUES.get(key)
    return list(values) if values else None


def uses_fixed_size_grid(size_grid):
    return get_size_grid_values(size_grid) is not None


def merge_display_sizes(fixed_grid, variant_sizes):
    """
    Fixed grid order first, then any variant-only sizes not in the grid (sorted).
    """
    if not fixed_grid:
        return list(variant_sizes or [])
    seen = {str(s).strip().lower() for s in fixed_grid}
    out = list(fixed_grid)
    extras = []
    for sz in variant_sizes or []:
        s = str(sz).strip()
        if not s:
            continue
        if s.lower() not in seen:
            seen.add(s.lower())
            extras.append(s)
    if extras:
        from .size_sort import size_sort_key

        extras.sort(key=size_sort_key)
        out.extend(extras)
    return out
