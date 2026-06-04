from datetime import datetime
from models import db, Recordatorio

def createReminder(text, datetime_str):
    """
    Crea un nuevo recordatorio en la base de datos.
    datetime_str debe ser un string en formato ISO o YYYY-MM-DD HH:MM:SS.
    """
    try:
        # Normalizar string de fecha para evitar errores de parseo de la IA
        clean_str = str(datetime_str).replace(' ', 'T').replace('Z', '')
        fecha_hora = datetime.fromisoformat(clean_str)
    except Exception as e:
        return {"success": False, "error": f"Formato de fecha inválido. Usa YYYY-MM-DDTHH:MM:SS. Detalle: {e}"}

    nuevo_recordatorio = Recordatorio(
        texto_tarea=text,
        fecha_hora_programada=fecha_hora,
        completado=False
    )
    
    db.session.add(nuevo_recordatorio)
    db.session.commit()
    
    return {
        "success": True, 
        "message": "Recordatorio guardado con éxito.",
        "reminder_id": nuevo_recordatorio.id,
        "scheduled_for": fecha_hora.strftime("%Y-%m-%d %H:%M:%S")
    }

def listTodayReminders():
    """
    Obtiene los recordatorios pendientes de HOY y cualquier tarea atrasada 
    que no haya sido completada.
    """
    # Calculamos el final del día de hoy (23:59:59)
    hoy = datetime.utcnow()
    fin_de_hoy = hoy.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Buscamos tareas no completadas cuya fecha programada sea igual o menor al final de hoy
    recordatorios = Recordatorio.query.filter(
        Recordatorio.completado == False,
        Recordatorio.fecha_hora_programada <= fin_de_hoy
    ).order_by(Recordatorio.fecha_hora_programada.asc()).all()
    
    if not recordatorios:
        return {"success": True, "message": "No tienes recordatorios pendientes para hoy.", "reminders": []}
        
    lista = []
    for r in recordatorios:
        # Formatear la fecha para que la IA la lea fácil
        fecha_str = r.fecha_hora_programada.strftime("%Y-%m-%d %H:%M:%S")
        estado_tiempo = "ATRASADO" if r.fecha_hora_programada < hoy else "PENDIENTE"
        
        lista.append({
            "id": r.id,
            "tarea": r.texto_tarea,
            "programado_para": fecha_str,
            "estado_tiempo": estado_tiempo
        })
        
    return {
        "success": True,
        "reminders": lista
    }

def markDone(reminderId):
    """
    Marca un recordatorio específico como completado.
    """
    # Por seguridad, intentamos convertir el ID a entero por si la IA envía un string
    try:
        reminder_id = int(reminderId)
    except ValueError:
        return {"success": False, "error": "El reminderId debe ser un número entero."}

    recordatorio = Recordatorio.query.get(reminder_id)
    
    if not recordatorio:
        return {"success": False, "error": f"No se encontró un recordatorio con el ID {reminder_id}."}
        
    if recordatorio.completado:
        return {"success": False, "error": "Este recordatorio ya había sido marcado como completado anteriormente."}
        
    recordatorio.completado = True
    db.session.commit()
    
    return {
        "success": True,
        "message": f"Recordatorio #{reminder_id} marcado como completado exitosamente."
    }