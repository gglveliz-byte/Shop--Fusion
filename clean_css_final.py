import re
import os

file_path = os.path.join(os.getcwd(), 'static', 'css', 'style.css')
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix remaining linear-gradient
content = re.sub(r'background:\s*linear-gradient\([^;]+;', 'background: var(--bg-surface);', content)

# Fix nav links colors
content = content.replace('color: white;', 'color: var(--text-primary);')
content = content.replace('background: rgba(255, 255, 255, 0.15);', 'background: var(--light-color);')

# Write back
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed CSS completely.")
