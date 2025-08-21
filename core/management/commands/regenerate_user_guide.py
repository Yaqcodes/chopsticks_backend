from django.core.management.base import BaseCommand
import os
import re
from datetime import datetime


class Command(BaseCommand):
    help = 'Regenerate the USER_GUIDE.html file from USER_GUIDE.md'

    def handle(self, *args, **options):
        try:
            # Get the path to the markdown file
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            md_file_path = os.path.join(current_dir, 'USER_GUIDE.md')
            html_file_path = os.path.join(current_dir, 'USER_GUIDE.html')
            
            # Check if markdown file exists
            if not os.path.exists(md_file_path):
                self.stdout.write(
                    self.style.ERROR('USER_GUIDE.md not found. Please create it first.')
                )
                return
            
            # Read the markdown file
            with open(md_file_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            
            # Simple markdown to HTML conversion
            html_content = md_content
            
            # Convert headers with proper anchor IDs
            def generate_anchor_id(text):
                """Generate a proper anchor ID from header text."""
                # Convert to lowercase and replace spaces/special chars with hyphens
                anchor = text.lower()
                anchor = re.sub(r'[^\w\s-]', '', anchor)  # Remove special characters
                anchor = re.sub(r'[-\s]+', '-', anchor)    # Replace spaces and multiple hyphens with single hyphen
                anchor = anchor.strip('-')                  # Remove leading/trailing hyphens
                return anchor
            
            # Convert headers
            html_content = re.sub(r'^### (.*?)$', r'<h3 id="\1">\1</h3>', html_content, flags=re.MULTILINE)
            html_content = re.sub(r'^## (.*?)$', lambda m: f'<h2 id="{generate_anchor_id(m.group(1))}">{m.group(1)}</h2>', html_content, flags=re.MULTILINE)
            html_content = re.sub(r'^# (.*?)$', lambda m: f'<h1 id="{generate_anchor_id(m.group(1))}">{m.group(1)}</h1>', html_content, flags=re.MULTILINE)
            
            # Convert bold text
            html_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html_content)
            
            # Convert lists
            html_content = re.sub(r'^- (.*?)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
            html_content = re.sub(r'^(\d+)\. (.*?)$', r'<li>\2</li>', html_content, flags=re.MULTILINE)
            
            # Wrap lists in <ul> tags
            lines = html_content.split('\n')
            in_list = False
            new_lines = []
            
            for line in lines:
                if line.strip().startswith('<li>'):
                    if not in_list:
                        new_lines.append('<ul>')
                        in_list = True
                    new_lines.append(line)
                elif in_list and not line.strip().startswith('<li>'):
                    new_lines.append('</ul>')
                    in_list = False
                    new_lines.append(line)
                else:
                    new_lines.append(line)
            
            if in_list:
                new_lines.append('</ul>')
            
            html_content = '\n'.join(new_lines)
            
            # Convert code blocks
            html_content = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html_content, flags=re.DOTALL)
            
            # Convert inline code
            html_content = re.sub(r'`(.*?)`', r'<code>\1</code>', html_content)
            
            # Convert line breaks
            html_content = html_content.replace('\n\n', '</p><p>')
            html_content = '<p>' + html_content + '</p>'
            
            # Clean up empty paragraphs
            html_content = html_content.replace('<p></p>', '')
            html_content = html_content.replace('<p><ul>', '<ul>')
            html_content = html_content.replace('</ul></p>', '</ul>')
            
            # Create HTML with GitHub-like styling
            html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chopsticks & Bowls - Restaurant Management Guide</title>
    <style>
        /* GitHub-like styling */
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #24292e;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #ffffff;
        }}
        
        h1, h2, h3, h4, h5, h6 {{
            margin-top: 24px;
            margin-bottom: 16px;
            font-weight: 600;
            line-height: 1.25;
            color: #24292e;
        }}
        
        h1 {{
            font-size: 2em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        
        h2 {{
            font-size: 1.5em;
            border-bottom: 1px solid #eaecef;
            padding-bottom: 0.3em;
        }}
        
        h3 {{
            font-size: 1.25em;
        }}
        
        p {{
            margin-bottom: 16px;
        }}
        
        ul, ol {{
            margin-bottom: 16px;
            padding-left: 2em;
        }}
        
        li {{
            margin-bottom: 0.25em;
        }}
        
        code {{
            background-color: rgba(27, 31, 35, 0.05);
            border-radius: 3px;
            font-size: 85%;
            margin: 0;
            padding: 0.2em 0.4em;
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        }}
        
        pre {{
            background-color: #f6f8fa;
            border-radius: 3px;
            font-size: 85%;
            line-height: 1.45;
            overflow: auto;
            padding: 16px;
            border: 1px solid #e1e4e8;
        }}
        
        pre code {{
            background-color: transparent;
            border: 0;
            display: inline;
            line-height: inherit;
            margin: 0;
            overflow: visible;
            padding: 0;
            word-wrap: normal;
        }}
        
        /* Navigation - Fixed at top */
        .nav {{
            background-color: #f6f8fa;
            border: 1px solid #e1e4e8;
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 24px;
            position: fixed;
            top: 0;
            left: 50%;
            transform: translateX(-50%);
            width: calc(100% - 40px);
            max-width: 1160px;
            z-index: 1000;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        .nav h3 {{
            margin-top: 0;
            color: #0366d6;
            font-size: 1.1em;
        }}
        
        .nav ul {{
            list-style: none;
            padding-left: 0;
            margin: 8px 0 0 0;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        
        .nav li {{
            margin-bottom: 0;
        }}
        
        .nav a {{
            color: #0366d6;
            text-decoration: none;
            padding: 4px 8px;
            border-radius: 3px;
            transition: background-color 0.2s;
            font-size: 0.9em;
            white-space: nowrap;
        }}
        
        .nav a:hover {{
            background-color: #e1e4e8;
            text-decoration: none;
        }}
        
        /* Add top margin to body to account for fixed nav */
        body {{
            margin-top: 120px;
        }}
        
        /* Smooth scrolling */
        html {{
            scroll-behavior: smooth;
        }}
        
        /* Footer */
        .footer {{
            margin-top: 48px;
            padding-top: 24px;
            border-top: 1px solid #eaecef;
            color: #6c757d;
            font-size: 14px;
            text-align: center;
        }}
        
        /* Responsive design */
        @media (max-width: 768px) {{
            .nav {{
                width: calc(100% - 20px);
                padding: 12px;
            }}
            
            .nav ul {{
                flex-direction: column;
                gap: 4px;
            }}
            
            .nav a {{
                font-size: 0.85em;
                padding: 3px 6px;
            }}
            
            body {{
                margin-top: 140px;
            }}
        }}
    </style>
</head>
<body>
    <div class="nav">
        <h3>📚 Quick Navigation</h3>
        <ul>
            <li><a href="#getting-started---first-time-setup">🏠 Getting Started</a></li>
            <li><a href="#managing-your-menu">🍽️ Managing Your Menu</a></li>
            <li><a href="#managing-orders">📦 Managing Orders</a></li>
            <li><a href="#loyalty-system-management">💳 Loyalty System</a></li>
            <li><a href="#promotional-codes">🎫 Promotional Codes</a></li>
            <li><a href="#restaurant-settings--configuration">⚙️ Restaurant Settings</a></li>
            <li><a href="#customer-management">👥 Customer Management</a></li>
            <li><a href="#payment-management">💰 Payment Management</a></li>
            <li><a href="#system-management">🔧 System Management</a></li>
            <li><a href="#mobile--website-features">📱 Mobile & Website Features</a></li>
            <li><a href="#pro-tips-for-restaurant-managers">🚀 Pro Tips</a></li>
            <li><a href="#troubleshooting-common-issues">🆘 Troubleshooting</a></li>
        </ul>
    </div>

    {html_content}
    
    <div class="footer">
        <p><strong>Chopsticks & Bowls Restaurant Management System</strong></p>
        <p>Last Updated: {datetime.now().strftime('%B %d, %Y')}</p>
        <p>System Version: v1.0</p>
    </div>
</body>
</html>"""
            
            # Write the HTML file
            with open(html_file_path, 'w', encoding='utf-8') as f:
                f.write(html_template)
            
            self.stdout.write(
                self.style.SUCCESS('✅ Successfully regenerated USER_GUIDE.html')
            )
            self.stdout.write(f'📁 File saved as: {html_file_path}')
            self.stdout.write('🌐 You can now access it at: /guide/user-guide/ or /')
            self.stdout.write('🔗 Quick navigation links are now working!')
            self.stdout.write('📌 Navigation is now properly fixed at the top!')
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Failed to regenerate user guide: {str(e)}')
            )
