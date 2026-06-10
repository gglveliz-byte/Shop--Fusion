import re
import os

file_path = os.path.join(os.getcwd(), 'static', 'css', 'style.css')
print(f"Reading: {file_path}")

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Patrón para eliminar backdrop-filter: blur(...);
    pattern_blur = r'\s*backdrop-filter:\s*blur\([^)]+\);'
    
    matches = re.findall(pattern_blur, content)
    print(f"Found {len(matches)} instances of backdrop-filter")
    
    # Reemplazar con cadena vacía para eliminarlos
    content = re.sub(pattern_blur, '', content)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Successfully removed backdrop-filter.")
except Exception as e:
    print(f"Error: {e}")
