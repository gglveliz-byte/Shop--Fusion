import os
import re

directories = ['static/css', 'templates']
files_to_clean = []

for d in directories:
    for root, dirs, files in os.walk(d):
        for file in files:
            if file.endswith('.css') or file.endswith('.html'):
                files_to_clean.append(os.path.join(root, file))

patterns_to_remove = [
    r'\s*-webkit-background-clip:\s*text;?',
    r'\s*-webkit-text-fill-color:\s*transparent;?',
    r'\s*background-clip:\s*text;?'
]

for file_path in files_to_clean:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content
        
        # Eliminar las propiedades de text-fill-color y background-clip
        for pattern in patterns_to_remove:
            content = re.sub(pattern, '', content)
        
        # También vamos a buscar donde el background sea un linear gradient y cambiarlo a color sólido
        # en el caso de textos, puede que quede sin color. Vamos a forzar el color de texto a primary si estaba usando background gradient para texto.
        # Pero es más seguro solo quitar el background-clip y el text-fill-color. El color normal de fallback aplicará.
        # En los HTML a veces hay 'background: linear-gradient(...);' inline junto al webkit-text-fill-color.
        
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Cleaned {file_path}")
            
    except Exception as e:
        print(f"Error reading {file_path}: {e}")

print("Global cleanup complete.")
