"""
Funciones de utilidad y validación para la Plataforma (Hardening Fase 3)
Mapeado desde el antiguo utils.py para mejor organización.
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
    Valida la fortaleza de una contraseña.
    Retorna (True, "") si es válida o (False, "mensaje de error") si no lo es.
    """
    if len(password) < 8:
        return False, "La contraseña debe tener al menos 8 caracteres."
    if not any(c.isupper() for c in password):
        return False, "La contraseña debe tener al menos una letra mayúscula."
    if not any(c.isdigit() for c in password):
        return False, "La contraseña debe tener al menos un número."
    if not any(c in "!@#$%^&*()-_+=[]{}|;:,.<>?/" for c in password):
        return False, "La contraseña debe tener al menos un carácter especial."
    return True, ""
