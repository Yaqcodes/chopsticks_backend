/**
 * Fixes the edit (pencil) / view / delete links for autocomplete (Select2) FK fields in ZMall admin.
 *
 * 1) Django's RelatedObjectLookups.updateRelatedObjectLinks() uses $(select).nextAll('.change-related')
 *    which only works when the <select> is a direct sibling of those links. Unfold (and AutocompleteSelect)
 *    wrap the select, so nextAll finds nothing — href is never set. We patch the global updater to
 *    resolve links from .closest('.related-widget-wrapper').
 *
 * 2) The popup click handler always preventDefault(); if href is still empty, nothing happens even though
 *    data-href-template plus select value are valid. We sync href in the capture phase before that handler.
 *
 * 3) Select2 may not emit a bubbling change; we still listen for select2:* and change on the real <select>.
 */
(function ($) {
    'use strict';
    if (typeof $ === 'undefined') {
        return;
    }

    function readSelectValue(selectEl) {
        var v = $(selectEl).val();
        if (v == null || v === '') {
            return '';
        }
        if (Array.isArray(v)) {
            return v.length ? String(v[0]) : '';
        }
        return String(v);
    }

    function applyTemplates($wrapper, pk) {
        if (!$wrapper || !$wrapper.length) {
            return;
        }
        $wrapper.find('.change-related, .view-related, .delete-related').each(function () {
            var $link = $(this);
            var template = $link.attr('data-href-template');
            if (!template) {
                return;
            }
            if (pk) {
                $link.attr('href', template.split('__fk__').join(pk));
            } else {
                $link.removeAttr('href');
            }
        });
    }

    function updateRelatedLinks(selectEl) {
        var $select = $(selectEl);
        var $wrapper = $select.closest('.related-widget-wrapper');
        if (!$wrapper.length) {
            return;
        }
        applyTemplates($wrapper, readSelectValue(selectEl));
    }

    /** Patch Django global so change-triggered updates work with nested selects (Unfold layout). */
    function patchDjangoUpdateRelatedObjectLinks() {
        if (typeof window.updateRelatedObjectLinks !== 'function') {
            return false;
        }
        if (window.updateRelatedObjectLinks.__zmallPatched) {
            return true;
        }
        var original = window.updateRelatedObjectLinks;
        window.updateRelatedObjectLinks = function (triggeringLink) {
            var $t = $(triggeringLink);
            var $wrap = $t.closest('.related-widget-wrapper');
            if ($wrap.length) {
                applyTemplates($wrap, readSelectValue(triggeringLink));
                return;
            }
            return original.call(this, triggeringLink);
        };
        window.updateRelatedObjectLinks.__zmallPatched = true;
        return true;
    }

    function tryPatchDjangoUpdater() {
        var attempts = 0;
        function tick() {
            if (patchDjangoUpdateRelatedObjectLinks()) {
                $('.related-widget-wrapper select').each(function () {
                    updateRelatedLinks(this);
                });
                return;
            }
            attempts += 1;
            if (attempts < 60) {
                setTimeout(tick, 50);
            }
        }
        tick();
    }

    /** Run before RelatedObjectLookups' delegated click (bubble) so this.href is set. */
    document.addEventListener(
        'click',
        function (ev) {
            var el = ev.target;
            if (!el || !el.closest) {
                return;
            }
            var a = el.closest(
                'a.related-widget-wrapper-link[data-popup="yes"][data-href-template], ' +
                    'a.change-related[data-href-template], ' +
                    'a.view-related[data-href-template], ' +
                    'a.delete-related[data-href-template]'
            );
            if (!a) {
                return;
            }
            var wrap = a.closest('.related-widget-wrapper');
            if (!wrap) {
                return;
            }
            var sel = wrap.querySelector('select');
            if (!sel) {
                return;
            }
            updateRelatedLinks(sel);
        },
        true
    );

    $(document).ready(function () {
        tryPatchDjangoUpdater();
        // Initial (also runs again inside tryPatch after Django's updater exists)
        $('.related-widget-wrapper select').each(function () {
            updateRelatedLinks(this);
        });
        $(document).on(
            'select2:select select2:unselect select2:clear',
            '.related-widget-wrapper select',
            function () {
                updateRelatedLinks(this);
            }
        );
        $(document).on('change', '.related-widget-wrapper select', function () {
            updateRelatedLinks(this);
        });
        // Re-sync when user moves toward the pencil (covers race with Select2 blur).
        $(document).on(
            'mousedown pointerdown focusin',
            '.related-widget-wrapper .change-related, .related-widget-wrapper .view-related, .related-widget-wrapper .delete-related',
            function () {
                var wrap = $(this).closest('.related-widget-wrapper');
                var sel = wrap.find('select').get(0);
                if (sel) {
                    updateRelatedLinks(sel);
                }
            }
        );
    });
})(django.jQuery);
