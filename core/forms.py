import json

from django import forms
from django.core.exceptions import ValidationError

from .models import RestaurantSettings

OPENING_HOURS_ADMIN_HELP = (
    'Optional. Use a JSON object with keys monday, tuesday, wednesday, thursday, friday, '
    'saturday, sunday. Each value is a time as "HH:MM" (24-hour) or null if closed that day. '
    'Leave blank if you only use Opening time and Closing time above. '
    'Example: {"monday": "09:00", "tuesday": "09:00", "wednesday": "09:00", '
    '"thursday": "09:00", "friday": "09:00", "saturday": "10:00", "sunday": null}'
)


class RestaurantSettingsAdminForm(forms.ModelForm):
    """Business settings admin: optional opening_hours JSON with clear format guidance."""

    class Meta:
        model = RestaurantSettings
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field = self.fields.get('opening_hours')
        if field is not None:
            field.required = False
            field.help_text = OPENING_HOURS_ADMIN_HELP

    def clean_opening_hours(self):
        value = self.cleaned_data.get('opening_hours')
        if value is None or value == '':
            return {}
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return {}
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValidationError(f'Invalid JSON: {exc}') from exc
        if not isinstance(value, dict):
            raise ValidationError(
                'Opening hours must be a JSON object, e.g. {"monday": "09:00", "sunday": null}.'
            )
        return value
