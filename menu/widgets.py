"""Custom widgets for ZMall apparel admin."""

from django import forms
from django.utils.html import escape
from django.utils.safestring import mark_safe
import json


class ColorPickerWidget(forms.Widget):
    """Widget for colors: name (optional) + HTML5 color picker per row. Add/remove rows."""

    def __init__(self, attrs=None):
        super().__init__(attrs)
        if attrs is None:
            attrs = {}
        self.attrs.setdefault('data-widget', 'color-picker')

    def _parse_value(self, value):
        if isinstance(value, list):
            return value
        if value is None:
            return []
        # DB/form may pass str (needs parsing) or already-deserialized list/dict
        if isinstance(value, (dict, bytes, bytearray)):
            return [value] if isinstance(value, dict) else []
        try:
            v = json.loads(value) if isinstance(value, str) else value
            return v if isinstance(v, list) else []
        except (TypeError, json.JSONDecodeError):
            return []

    def render(self, name, value, attrs=None, renderer=None):
        items = self._parse_value(value)
        attrs = attrs or {}
        attrs.setdefault('id', f'id_{name}')
        widget_id = attrs.get('id', name)

        rows = []
        for i, item in enumerate(items):
            item_name = escape(item.get('name', '') if isinstance(item, dict) else '')
            item_hex = escape(item.get('hex', '#000000') if isinstance(item, dict) else '#000000')
            rows.append(
                f'<div class="color-row" data-index="{i}">'
                f'<input type="text" name="{name}_name_{i}" value="{item_name}" placeholder="Name (optional)" '
                f'class="vTextField" style="width:140px;margin-right:8px;">'
                f'<input type="color" name="{name}_hex_{i}" value="{item_hex}" '
                f'title="Pick colour" style="width:40px;height:28px;padding:2px;cursor:pointer;vertical-align:middle;">'
                f'<input type="text" name="{name}_hex_display_{i}" value="{item_hex}" readonly '
                f'class="vTextField" style="width:70px;margin-left:4px;font-size:11px;" '
                f'data-hex-target="{name}_hex_{i}">'
                f'<button type="button" class="color-remove" style="margin-left:8px;">Remove</button>'
                f'</div>'
            )
        rows_html = ''.join(rows)

        script = f'''
        <script>
        (function() {{
            var container = document.getElementById('color-picker-container-{widget_id}');
            if (!container) return;
            var addBtn = container.querySelector('.color-add');
            var rowsContainer = container.querySelector('.color-rows');
            var nameBase = '{name}';
            var idx = {len(items)};

            function syncHexDisplay(row) {{
                var colorInput = row.querySelector('input[type="color"]');
                var displayInput = row.querySelector('input[readonly]');
                if (colorInput && displayInput) displayInput.value = colorInput.value;
            }}

            container.querySelectorAll('.color-row').forEach(function(row) {{
                var colorInput = row.querySelector('input[type="color"]');
                if (colorInput) {{
                    colorInput.addEventListener('input', function() {{ syncHexDisplay(row); }});
                    syncHexDisplay(row);
                }}
                row.querySelector('.color-remove').addEventListener('click', function() {{
                    row.remove();
                }});
            }});

            if (addBtn) {{
                addBtn.addEventListener('click', function() {{
                    var div = document.createElement('div');
                    div.className = 'color-row';
                    div.setAttribute('data-index', idx);
                    div.innerHTML = '<input type="text" name="' + nameBase + '_name_' + idx + '" placeholder="Name (optional)" class="vTextField" style="width:140px;margin-right:8px;">' +
                        '<input type="color" name="' + nameBase + '_hex_' + idx + '" value="#000000" title="Pick colour" style="width:40px;height:28px;padding:2px;cursor:pointer;vertical-align:middle;">' +
                        '<input type="text" name="' + nameBase + '_hex_display_' + idx + '" value="#000000" readonly class="vTextField" style="width:70px;margin-left:4px;font-size:11px;">' +
                        '<button type="button" class="color-remove" style="margin-left:8px;">Remove</button>';
                    rowsContainer.appendChild(div);
                    var colorInput = div.querySelector('input[type="color"]');
                    var displayInput = div.querySelector('input[readonly]');
                    colorInput.addEventListener('input', function() {{ displayInput.value = colorInput.value; }});
                    div.querySelector('.color-remove').addEventListener('click', function() {{ div.remove(); }});
                    idx++;
                }});
            }}
        }})();
        </script>
        '''

        html = f'''
        <div id="color-picker-container-{widget_id}" class="color-picker-widget">
            <div class="color-rows">{rows_html}</div>
            <div style="margin-top:8px;">
                <button type="button" class="color-add">Add colour</button>
            </div>
            {script}
        </div>
        '''
        return mark_safe(html)

    def value_from_datadict(self, data, files, name):
        """Collect from name_N and hex_N. Return JSON string so JSONField form field receives str (avoids TypeError: json.loads got list)."""
        items = []
        i = 0
        while True:
            n = data.get(f'{name}_name_{i}')
            h = data.get(f'{name}_hex_{i}')
            if n is None and h is None:
                break
            hex_val = (h or '').strip()
            if not hex_val:
                hex_val = '#000000'
            if not hex_val.startswith('#'):
                hex_val = '#' + hex_val
            items.append({'name': (n or '').strip(), 'hex': hex_val})
            i += 1
        return json.dumps(items) if items else '[]'


# Clothing sizes (non-shoe categories)
CLOTHING_SIZE_CHOICES = [
    ('XS', 'XS'),
    ('S', 'S'),
    ('M', 'M'),
    ('L', 'L'),
    ('XL', 'XL'),
    ('XXL', 'XXL'),
    ('ONE SIZE', 'ONE SIZE'),
]

# Shoe sizes (when category is Shoes)
SHOE_SIZE_CHOICES = [
    ('36', '36'),
    ('37', '37'),
    ('38', '38'),
    ('39', '39'),
    ('40', '40'),
    ('41', '41'),
    ('42', '42'),
    ('43', '43'),
    ('44', '44'),
    ('45', '45'),
    ('46', '46'),
]

# All sizes (legacy / combined)
SIZE_CHOICES = CLOTHING_SIZE_CHOICES + SHOE_SIZE_CHOICES


class SizeSectionWidget(forms.CheckboxSelectMultiple):
    """CheckboxSelectMultiple wrapped in a div with id for category-based show/hide."""
    wrapper_id = 'zmall-size-section'

    def render(self, name, value, attrs=None, renderer=None):
        inner = super().render(name, value, attrs, renderer)
        return mark_safe(f'<div id="{self.wrapper_id}" class="zmall-size-section">{inner}</div>')


class ClothingSizeWidget(SizeSectionWidget):
    wrapper_id = 'zmall-size-clothing'


class ShoeSizeWidget(SizeSectionWidget):
    wrapper_id = 'zmall-size-shoes'


class MultipleFileInput(forms.FileInput):
    """Renders <input type="file" multiple> for uploading several files at once."""
    def __init__(self, attrs=None):
        super().__init__(attrs)
        if attrs is None:
            attrs = {}
        self.attrs.setdefault('multiple', True)

    def value_from_datadict(self, data, files, name):
        # Django's MultiValueField would need a different approach; we handle files in admin save_model.
        return None
