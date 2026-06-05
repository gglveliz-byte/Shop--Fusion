import os
import markdown
from flask import current_app, render_template

def send_email(to_email, subject, template_name='general.html', context=None):
    """
    Envía un correo electrónico usando plantillas HTML.
    Si se pasa 'body_content' en el context, se procesará con Markdown (útil para general.html).
    """
    if not to_email:
        return {"success": False, "error": "Destinatario no especificado."}

    mail_server = os.environ.get('MAIL_SERVER')
    if not mail_server:
        return {"success": False, "error": "Servidor de correo no configurado en el servidor."}

    try:
        from app import mail
        from flask_mail import Message

        if context is None:
            context = {}

        # Convertir Markdown a HTML si usamos la plantilla general
        if 'body_content' in context:
            context['body_content'] = markdown.markdown(context['body_content'])

        # Renderizar la plantilla elegida
        html_body = render_template(f"emails/{template_name}", **context)

        msg = Message(
            subject=subject,
            recipients=[to_email],
            html=html_body
        )
        
        mail.send(msg)
        
        if current_app:
            current_app.logger.info(f"[COMUNICACIONES] Correo enviado a {to_email} con plantilla {template_name}")
            
        return {"success": True, "message": f"Correo enviado exitosamente a {to_email}."}

    except Exception as e:
        if current_app:
            current_app.logger.error(f"[COMUNICACIONES] Error al enviar correo a {to_email}: {e}")
        return {"success": False, "error": str(e)}
