"""
Explicit link/unlink of MenuItem variants to Product (no auto-linking).
"""

from django.db import transaction

from .models import MenuItem
from .variant_utils import variant_keys


def link_menu_items_to_product(product, menu_items_iter, *, dry_run=False):
    """
    Validate and optionally link MenuItems to ``product``.
    If any SKU fails validation, no links are written (strict batch).
    """
    errors = []
    skipped_ids = []
    todo = []

    for mi in menu_items_iter:
        if mi.restaurant_settings_id != product.restaurant_settings_id:
            errors.append(
                {'menu_item_id': mi.pk, 'message': 'SKU belongs to another business.'},
            )
            continue
        if mi.product_id and mi.product_id != product.pk:
            errors.append(
                {
                    'menu_item_id': mi.pk,
                    'message': 'SKU is already linked to another catalog product.',
                },
            )
            continue
        if mi.product_id == product.pk:
            skipped_ids.append(mi.pk)
            continue
        todo.append(mi)

    if errors:
        out = {'errors': errors, 'linked_ids': [], 'skipped_ids': skipped_ids}
        if dry_run:
            out['dry_run'] = True
            out['approved_ids'] = []
        return out

    keys_by_id = {
        m.pk: variant_keys(m)
        for m in MenuItem.objects.filter(product_id=product.pk)
    }
    for mi in todo:
        new_keys = variant_keys(mi)
        clash_pk = next(
            (pk for pk, ks in keys_by_id.items() if pk != mi.pk and ks & new_keys),
            None,
        )
        if clash_pk is not None:
            errors.append(
                {
                    'menu_item_id': mi.pk,
                    'message': 'Duplicate size/colour combination for this catalog product.',
                },
            )
            continue
        keys_by_id[mi.pk] = new_keys

    if errors:
        out = {'errors': errors, 'linked_ids': [], 'skipped_ids': skipped_ids}
        if dry_run:
            out['dry_run'] = True
            out['approved_ids'] = []
        return out

    if dry_run:
        return {
            'dry_run': True,
            'errors': [],
            'approved_ids': [m.pk for m in todo],
            'skipped_ids': skipped_ids,
        }

    linked_ids = []
    linked_events = []
    with transaction.atomic():
        for mi in todo:
            previous_product_id = mi.product_id
            mi.product = product
            mi.full_clean()
            mi.save(update_fields=['product'])
            linked_ids.append(mi.pk)
            linked_events.append((mi.pk, previous_product_id))

    return {
        'errors': [],
        'linked_ids': linked_ids,
        'skipped_ids': skipped_ids,
        'linked_events': linked_events,
    }


def unlink_menu_item_from_product(product, menu_item):
    """Remove FK if menu_item is linked to product; validates tenant."""
    if menu_item.restaurant_settings_id != product.restaurant_settings_id:
        return False, 'SKU belongs to another business.'
    if menu_item.product_id != product.pk:
        return False, 'SKU is not linked to this catalog product.'
    menu_item.product = None
    menu_item.save(update_fields=['product'])
    return True, None
