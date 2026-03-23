(function() {
    var SHOES_SLUG = 'shoes';

    function getSlugsFromHidden() {
        var input = document.querySelector('input[name="_zmall_category_slugs"]') || document.querySelector('input[name$="_zmall_category_slugs"]');
        if (!input || !input.value) return {};
        try {
            return JSON.parse(input.value);
        } catch (e) {
            return {};
        }
    }

    function run() {
        var slugs = getSlugsFromHidden();
        var categorySelect = document.querySelector('select[name="category"]') || document.querySelector('select[name$="category"]');
        var clothingDiv = document.getElementById('zmall-size-clothing');
        var shoesDiv = document.getElementById('zmall-size-shoes');
        if (!categorySelect || !clothingDiv || !shoesDiv) return;

        function updateVisibility() {
            var val = categorySelect.value;
            var slug = (slugs[val] || '').toLowerCase();
            var isShoes = slug === SHOES_SLUG.toLowerCase();
            clothingDiv.style.display = isShoes ? 'none' : '';
            shoesDiv.style.display = isShoes ? '' : 'none';
        }

        categorySelect.addEventListener('change', updateVisibility);
        updateVisibility();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', run);
    } else {
        run();
    }
})();
