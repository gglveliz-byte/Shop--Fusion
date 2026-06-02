from models import db, TicketSoporte, ComentarioTicket
from datetime import datetime

# ──────────────────────────────────────────────
# MÓDULO DE SOPORTE — utils/support.py
# Patrón: funciones puras con try/except + rollback,
# idéntico a utils/crm.py
# ──────────────────────────────────────────────

def create_ticket(subject, description, priority='media', contact_name=None, contact_email=None, canal='chat'):
    """
    Paso 2.1: Crea un nuevo ticket de soporte en la BD.
    Retorna {"success": True, "ticket_id": X, "numero": "TKT-XXXX"}
    """
    try:
        prioridades_validas = ('baja', 'media', 'alta', 'critica')
        if priority not in prioridades_validas:
            return {"success": False, "error": f"Prioridad '{priority}' no válida. Usa: {prioridades_validas}"}

        ticket = TicketSoporte(
            asunto=subject,
            descripcion=description,
            prioridad=priority,
            canal=canal,
            estado='abierto',
            escalado=False
        )

        # Los setters del modelo cifran automáticamente el PII
        if contact_name:
            ticket.contacto_nombre = contact_name
        if contact_email:
            ticket.contacto_email = contact_email

        db.session.add(ticket)
        db.session.commit()

        return {
            "success": True,
            "ticket_id": ticket.id,
            "numero": ticket.numero,
            "mensaje": f"Ticket {ticket.numero} creado correctamente con prioridad '{priority}'."
        }

    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}


def get_ticket_status(ticket_id):
    """
    Paso 2.2: Consulta el estado actual de un ticket y sus últimos comentarios.
    Retorna {"success": True, "ticket": {...}, "comentarios": [...]}
    """
    try:
        ticket = TicketSoporte.query.get(ticket_id)
        if not ticket:
            return {"success": False, "error": f"Ticket #{ticket_id} no encontrado."}

        comentarios = [c.to_dict() for c in ticket.comentarios[-5:]]  # Últimos 5

        return {
            "success": True,
            "ticket": ticket.to_dict(),
            "comentarios": comentarios
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def add_comment(ticket_id, content, author='ia'):
    """
    Paso 2.3: Añade un comentario a un ticket.
    author: 'ia' | 'admin' | 'usuario'
    """
    try:
        ticket = TicketSoporte.query.get(ticket_id)
        if not ticket:
            return {"success": False, "error": f"Ticket #{ticket_id} no encontrado."}

        comentario = ComentarioTicket(
            ticket_id=ticket_id,
            autor=author,
            contenido=content
        )
        db.session.add(comentario)

        # Actualizar timestamp del ticket
        ticket.actualizado_en = datetime.utcnow()
        db.session.commit()

        return {
            "success": True,
            "ticket_id": ticket_id,
            "numero": ticket.numero,
            "mensaje": f"Comentario añadido al ticket {ticket.numero}."
        }

    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}


def escalate_ticket(ticket_id):
    """
    Paso 2.4: Escala un ticket al equipo humano.
    Marca escalado=True, sube prioridad mínima a 'alta' y notifica al equipo.
    """
    try:
        ticket = TicketSoporte.query.get(ticket_id)
        if not ticket:
            return {"success": False, "error": f"Ticket #{ticket_id} no encontrado."}

        if ticket.escalado:
            return {"success": True, "mensaje": f"El ticket {ticket.numero} ya estaba escalado.", "numero": ticket.numero}

        ticket.escalado = True
        ticket.estado = 'en_progreso'

        # Subir prioridad a 'alta' si estaba en 'baja' o 'media'
        if ticket.prioridad in ('baja', 'media'):
            ticket.prioridad = 'alta'

        ticket.actualizado_en = datetime.utcnow()
        db.session.commit()

        # Notificar al equipo (Fase 3 — si falla el email no bloquea el flujo)
        try:
            notify_team(ticket)
        except Exception as notify_err:
            print(f"[SOPORTE] Advertencia: No se pudo enviar notificación de email: {notify_err}")

        return {
            "success": True,
            "ticket_id": ticket.id,
            "numero": ticket.numero,
            "prioridad": ticket.prioridad,
            "mensaje": f"Ticket {ticket.numero} escalado al equipo humano. Se ha enviado una notificación."
        }

    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}


def notify_team(ticket):
    """
    Paso 3.3 (Fase 3): Envía notificación por email al equipo de soporte.
    Si MAIL_SERVER no está configurado, registra en log y continúa sin error.
    """
    import os
    from flask import current_app

    support_email = os.environ.get('SUPPORT_EMAIL')
    mail_server   = os.environ.get('MAIL_SERVER')

    if not mail_server or not support_email:
        print(f"[SOPORTE] Ticket {ticket.numero} escalado. Email pendiente (MAIL_SERVER o SUPPORT_EMAIL no configurado).")
        return

    try:
        from app import mail
        from flask_mail import Message

        prioridad_emoji = {'baja': '🟢', 'media': '🟡', 'alta': '🔴', 'critica': '🚨'}.get(ticket.prioridad, '📋')

        msg = Message(
            subject=f"[Shop Fusion] {prioridad_emoji} Nuevo ticket escalado: {ticket.numero}",
            recipients=[support_email],
            html=f"""
            <div style="font-family: sans-serif; max-width: 600px; margin: auto; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                <div style="background: #1e293b; color: white; padding: 20px;">
                    <h2 style="margin: 0;">🎫 Ticket de Soporte Escalado</h2>
                </div>
                <div style="padding: 24px;">
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr><td style="padding: 8px; color: #6b7280; width: 140px;">Número</td><td style="padding: 8px; font-weight: bold;">{ticket.numero}</td></tr>
                        <tr style="background:#f9fafb;"><td style="padding: 8px; color: #6b7280;">Prioridad</td><td style="padding: 8px;">{prioridad_emoji} {ticket.prioridad.upper()}</td></tr>
                        <tr><td style="padding: 8px; color: #6b7280;">Estado</td><td style="padding: 8px;">{ticket.estado}</td></tr>
                        <tr style="background:#f9fafb;"><td style="padding: 8px; color: #6b7280;">Canal</td><td style="padding: 8px;">{ticket.canal}</td></tr>
                        <tr><td style="padding: 8px; color: #6b7280;">Asunto</td><td style="padding: 8px;">{ticket.asunto}</td></tr>
                        <tr style="background:#f9fafb;"><td style="padding: 8px; color: #6b7280;">Descripción</td><td style="padding: 8px;">{ticket.descripcion or 'Sin descripción'}</td></tr>
                        <tr><td style="padding: 8px; color: #6b7280;">Creado</td><td style="padding: 8px;">{ticket.creado_en.strftime('%Y-%m-%d %H:%M') if ticket.creado_en else '-'}</td></tr>
                    </table>
                    <div style="margin-top: 20px; padding: 12px; background: #fef3c7; border-radius: 6px; border-left: 4px solid #f59e0b;">
                        <strong>⚠️ Este ticket requiere atención humana.</strong> Por favor revísalo a la brevedad.
                    </div>
                </div>
                <div style="background: #f3f4f6; padding: 12px; text-align: center; font-size: 12px; color: #9ca3af;">
                    Shop Fusion — Sistema de Soporte Automatizado
                </div>
            </div>
            """
        )
        mail.send(msg)
        current_app.logger.info(f"[SOPORTE] Email enviado para ticket {ticket.numero} a {support_email}")

    except Exception as e:
        # Nunca bloquear el flujo del negocio por un fallo de email
        print(f"[SOPORTE] Error al enviar email para ticket {ticket.numero}: {e}")

