import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction
from menu.models import MenuItem

class Command(BaseCommand):
    help = 'Import MenuItems from an Excel file.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the .xlsx file')

    def get_color_hex(self, color_name):
        """Map provided color strings to approximate hex codes."""
        if pd.isna(color_name) or not str(color_name).strip():
            return []

        color_str = str(color_name).strip().upper()
        
        # Color mapping based on the provided list
        color_map = {
            'BLACK': '#000000', 'BROWN': '#A52A2A', 'BLUE': '#0000FF', 
            'MUSTARD': '#FFDB58', 'TAUPE GREY': '#8B8589', 'GREY': '#808080', 
            'COGNAC BROWN': '#9A463D', 'SAND BROWN': '#F4A460', 'MULTI-COLOUR': '#FFFFFF', 
            'GREEN': '#008000', 'RED': '#FF0000', 'WHITE': '#FFFFFF', 
            'PURPLE': '#800080', 'YELLOW': '#FFFF00', 'NUDE': '#F3E5AB', 
            'ORANGE': '#FFA500', 'SILVER': '#C0C0C0', 'GOLD': '#FFD700', 
            'CREAM': '#FFFDD0', 'SKY BLUE': '#87CEEB', 'NAVY BLUE': '#000080', 
            'SAND': '#C2B280', 'PEACH': '#FFE5B4', 'PINK': '#FFC0CB', 
            'CAMEL': '#C19A6B', 'BEIGE': '#F5F5DC', 'BURGUNDY': '#800020', 
            'LIGHT GREEN': '#90EE90', 'LIGHT BROWN': '#B5651D', 'BRICK': '#B22222', 
            'ECRU': '#C2B280', 'LIGHT GREY': '#D3D3D3', 'DARK GREY': '#A9A9A9', 
            'LIGHT BLUE': '#ADD8E6', 'DARK BROWN': '#654321', 'DARK GREEN': '#006400', 
            'MID-BLUE': '#0000CD', 'FADED BLUE': '#7B9095', 'CARPENTER BLUE': '#5C7B9E', 
            'DARK BLUE': '#00008B', 'BURNT ORANGE': '#CC5500', 'LACIVERT': '#000080', 
            'SIYAH': '#000000', 'KHAKI': '#F0E68C', 'CHARCOAL': '#36454F', 
            'RASPBERRY': '#E30B5D', 'BLUE GREY': '#6699CC', 'DARK PURPLE': '#301934', 
            'GREY STRIPE': '#808080', 'INDIGO': '#4B0082'
        }

        # Handle split/combo colors (e.g., 'WHITE/BLUE') by taking the first color's hex, 
        # or fall back to gray if the color isn't in the map at all.
        primary_color = color_str.split('/')[0].strip()
        hex_code = color_map.get(primary_color, color_map.get(color_str, '#808080'))

        return [{"name": color_str.title(), "hex": hex_code}]

    def handle(self, *args, **kwargs):
        file_path = kwargs['file_path']
        
        self.stdout.write(f"Loading data from {file_path}...")
        
        try:
            df = pd.read_excel(file_path)
            # FIX: Replace any newlines or weird spacing INSIDE the headers with a single space, then strip ends
            df.columns = df.columns.str.replace(r'\s+', ' ', regex=True).str.strip()
        except Exception as e:
            self.stderr.write(f"Error reading file: {e}")
            return

        CATEGORY_ID = 20
        RESTAURANT_SETTINGS_ID = 4

        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for index, row in df.iterrows():
                # 1. Parse Name
                name = str(row.get('Name', '')).strip()
                if not name or pd.isna(row.get('Name')):
                    continue

                # 2. Parse Price
                price_n = row.get('Price N', 0)
                price = float(price_n) if not pd.isna(price_n) else 0.0

                # 3. Parse Is Available
                is_inactive = row.get('Is Inactive')
                is_available = False if str(is_inactive).strip() in ['1', '1.0', 'True', 'Yes'] else True

                # 4. Parse Barcode
                barcode = str(row.get('Barcode', '')).strip()
                if pd.isna(row.get('Barcode')) or not barcode or barcode == 'nan':
                    barcode = None

                # 5. Parse Color
                color_raw = row.get('Color')
                colors_json = self.get_color_hex(color_raw)

                # 6. Parse Size (for the list)
                excel_size = str(row.get('Size', '')).strip()
                if pd.isna(row.get('Size')) or excel_size.lower() == 'nan':
                    excel_size = None

                # 7. FIX 2: Parse SKU Safely
                raw_qty = row.get('Quantity On Hand')
                try:
                    # Cast to float first to handle cases where Excel exports "10.0" as text
                    sku = int(float(raw_qty)) if pd.notna(raw_qty) else 0
                except (ValueError, TypeError):
                    sku = 0
                
                sku = max(0, sku) # Snap any negative numbers to 0

                # 8. Fetch or Initialize Item
                created = False
                if barcode:
                    item = MenuItem.objects.filter(barcode=barcode).first()
                    identifier = f"Barcode: {barcode}"
                else:
                    # Without a barcode, find by Name and Category
                    item = MenuItem.objects.filter(name=name, category_id=CATEGORY_ID).first()
                    identifier = f"Name: {name}"

                if not item:
                    # Create a new, unsaved instance
                    item = MenuItem(
                        barcode=barcode,
                        name=name,
                        category_id=CATEGORY_ID,
                        restaurant_settings_id=RESTAURANT_SETTINGS_ID,
                        sizes=[] # Initialize the list
                    )
                    created = True

                # 9. Update the standard fields
                item.price = price
                item.is_available = is_available
                item.colors = colors_json
                item.sku = sku
                
                # We leave item.size blank as it's no longer the target field
                item.size = ''

                # 10. Append the size to the JSON array
                if excel_size:
                    # Ensure it's a list just in case an old entry had it stored as null/dict
                    if not isinstance(item.sizes, list):
                        item.sizes = []
                    
                    # Only append if it isn't already in the list
                    if excel_size not in item.sizes:
                        item.sizes.append(excel_size)

                # Save the changes
                item.save()

                # Logging
                if created:
                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Line {index + 2}: [+] Created -> {name} ({identifier}) [SKU: {sku}]"))
                else:
                    updated_count += 1
                    self.stdout.write(self.style.WARNING(f"Line {index + 2}: [~] Updated -> {name} ({identifier}) [SKU: {sku}]"))

        self.stdout.write(self.style.SUCCESS(
            f"\n--- IMPORT COMPLETE ---\nSuccessfully processed Excel file.\nCreated: {created_count}\nUpdated: {updated_count}"
        ))
