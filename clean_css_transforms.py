import re
import os

file_path = os.path.join(os.getcwd(), 'static', 'css', 'style.css')
print(f"Reading: {file_path}")

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Patrón para eliminar transform: translateY(...) o scale(...)
    pattern_transform = r'\s*transform:\s*(?:translateY\([^)]+\)|scale\([^)]+\));'
    
    matches = re.findall(pattern_transform, content)
    print(f"Found {len(matches)} instances of transform animations")
    
    # Reemplazar con cadena vacía
    content = re.sub(pattern_transform, '', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Successfully removed hover transforms.")
except Exception as e:
    print(f"Error: {e}")
