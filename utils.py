"""
Funciones de utilidad compartidas para Shop Fusion (Error E7)
"""

def format_whatsapp(num):
    """
    Formatea un número de teléfono para que sea compatible con los enlaces de WhatsApp.
    Centraliza la lógica para evitar duplicidad (Mitiga E7).
    """
    if not num:
        return ""
    
    num = str(num).strip().replace(" ", "").replace("-", "").replace("+", "")
    
    if num.startswith('0'):
        return '593' + num[1:]
    elif not num.startswith('593'):
        return '593' + num
        
    return num

def validate_whatsapp(num):
    """
    Valida si el formato de número es aceptable (mínimo 9 dígitos después de limpiar).
    """
    if not num:
        return False
    num_clean = "".join(filter(str.isdigit, num))
    return len(num_clean) >= 9

def is_strong_password(password):
    """
    Verifica si una contraseña cumple con requisitos mínimos (Mitiga E36).
    - Mínimo 8 caracteres.
    - Al menos un número.
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if not any(char.isdigit() for char in password):
        return False, "La contraseña debe incluir al menos un número."
    return True, ""