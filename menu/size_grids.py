"""
Size grid helpers.

All grid definitions live in the ``SizeGrid`` model (admin-managed).
These thin helpers read from a Category's FK and merge with variant sizes.
"""


def get_size_grid_values(category, gender=None):
    """
    Return the fixed display sizes for a category, or None when flexible.

    Accepts a Category instance (reads its ``size_grid`` FK).
    """
    grid = getattr(category, 'size_grid', None) if category else None
    if grid is None:
        return None
    sizes = getattr(grid, 'sizes', None)
    if not sizes or not isinstance(sizes, list):
        return None
    return list(sizes)


def get_size_grid_key(category):
    """Return the slug key for the API, or empty string."""
    grid = getattr(category, 'size_grid', None) if category else None
    if grid is None:
        return ''
    return getattr(grid, 'key', '') or ''


def uses_fixed_size_grid(category, gender=None):
    return get_size_grid_values(category, gender) is not None


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
