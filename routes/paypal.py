"""
Sub-rutas de integración con PayPal (pagos y webhooks).
Extraído de routes/tienda.py en Fase 3.3 (Modularización).
"""
import requests
import base64
from flask import request, redirect, url_for, session, current_app, jsonify
from decimal import Decimal
from models import db
from routes.tienda import bp
from utils.rate_limit import limiter
from utils.security_logger import log_security_event
from utils.accounting import register_transaction


# ==================== PAYPAL INTEGRATION ====================

def get_paypal_access_token():
    """Obtener token de acceso de PayPal"""
    client_id = current_app.config['PAYPAL_CLIENT_ID']
    client_secret = current_app.config['PAYPAL_SECRET']
    mode = current_app.config['PAYPAL_MODE']

    if mode == 'live':
        url = "https://api-m.paypal.com/v1/oauth2/token"
    else:
        url = "https://api-m.sandbox.paypal.com/v1/oauth2/token"

    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        response = requests.post(url, headers=headers, data="grant_type=client_credentials", timeout=10)

        if response.status_code == 200:
            return response.json()['access_token']

        # Manejo granular de errores (Logs detallados)
        if response.status_code == 401:
            current_app.logger.error("PayPal Error 401: Credenciales inválidas o expiradas (Verificar Client ID/Secret).")
        elif response.status_code == 429:
            current_app.logger.error("PayPal Error 429: Rate limit excedido (Demasiadas peticiones a la API).")
        elif response.status_code >= 500:
            current_app.logger.error(f"PayPal Error {response.status_code}: Error temporal en servidores de PayPal. Detalle: {response.text}")
        else:
            current_app.logger.error(f"PayPal Error {response.status_code}: Error HTTP inesperado. Detalle: {response.text}")

    except requests.exceptions.RequestException as e:
        current_app.logger.error(f"PayPal Network Error: Fallo de conexión de red. Detalle: {str(e)}")

    return None


@bp.route('/api/paypal/create-order', methods=['POST'])
@limiter.limit("3 per minute", error_message='Demasiados intentos de pago. Por seguridad, espera un momento.')
def paypal_create_order():
    """Crear orden de PayPal"""
    from models import Producto

    try:
        data = request.get_json()
        carrito = data.get('carrito', [])

        if not carrito:
            return jsonify({'error': 'Carrito vacío'}), 400

        # Calcular total
        total = Decimal('0.00')
        items = []

        #INICIA LOS CAMBIOS INDICADOS EN FASE 3
        # RECALCULO DE SEGURIDAD (Mitiga E42): Uso de precio oficial desde DB
        for item in carrito:
            producto = Producto.query.get(item['id'])
            if producto and producto.activo:
                precio = producto.precio_venta()
                cantidad = item['cantidad']
                subtotal = precio * cantidad
                total += subtotal

                items.append({
                    "name": producto.nombre[:127],
                    "quantity": str(cantidad),
                    "unit_amount": {
                        "currency_code": "USD",
                        "value": f"{float(precio):.2f}"
                    }
                })
        #FIN DE LOS CAMBIOS INDICADOS EN FASE 3

        # Agregar comisión PayPal (5.4%)
        comision_paypal = Decimal('5.4')
        total_con_comision = total * (Decimal('1') + (comision_paypal / Decimal('100')))
        recargo_paypal = total_con_comision - total

        # Agregar el recargo como item separado en PayPal
        items.append({
            "name": f"Comisión PayPal/Tarjeta ({comision_paypal}%)",
            "quantity": "1",
            "unit_amount": {
                "currency_code": "USD",
                "value": f"{float(recargo_paypal):.2f}"
            }
        })

        # Obtener token de PayPal
        access_token = get_paypal_access_token()
        if not access_token:
            return jsonify({'error': 'Error de autenticación con PayPal'}), 500

        mode = current_app.config['PAYPAL_MODE']
        if mode == 'live':
            url = "https://api-m.paypal.com/v2/checkout/orders"
        else:
            url = "https://api-m.sandbox.paypal.com/v2/checkout/orders"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        order_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": f"{float(total_con_comision):.2f}",
                    "breakdown": {
                        "item_total": {
                            "currency_code": "USD",
                            "value": f"{float(total_con_comision):.2f}"
                        }
                    }
                },
                "items": items
            }]
        }

        response = requests.post(url, headers=headers, json=order_data)

        if response.status_code in [200, 201]:
            return jsonify(response.json())
        else:
            return jsonify({'error': 'Error creando orden en PayPal'}), 500

    except Exception as e:
        current_app.logger.exception(f"Error fatal creando orden de PayPal: {e}")
        return jsonify({'error': 'Error interno al procesar el pago'}), 500


@bp.route('/api/paypal/capture-order', methods=['POST'])
def paypal_capture_order():
    """Capturar pago de PayPal y crear pedido"""
    from models import Producto, Pedido, Afiliado
    from app import db

    try:
        data = request.get_json()
        order_id = data.get('orderID')
        nombre = data.get('nombre')
        telefono = data.get('telefono')
        direccion = data.get('direccion')
        carrito = data.get('carrito', [])

        if not all([order_id, nombre, telefono, direccion, carrito]):
            return jsonify({'error': 'Datos incompletos'}), 400

        # Capturar el pago en PayPal
        access_token = get_paypal_access_token()
        if not access_token:
            return jsonify({'error': 'Error de autenticación con PayPal'}), 500

        mode = current_app.config['PAYPAL_MODE']
        if mode == 'live':
            url = f"https://api-m.paypal.com/v2/checkout/orders/{order_id}/capture"
        else:
            url = f"https://api-m.sandbox.paypal.com/v2/checkout/orders/{order_id}/capture"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        # Asegurarnos de enviar un cuerpo vacío (json={}) para evitar error 400/415 de PayPal
        response = requests.post(url, headers=headers, json={})

        if response.status_code not in [200, 201]:
            error_details = response.text
            print(f"DEBUG PAYPAL CAPTURE ERROR: {error_details}")
            return jsonify({'error': f'Error capturando pago con PayPal. Detalles internos: {error_details}'}), 500

        paypal_response = response.json()

        if paypal_response.get('status') != 'COMPLETED':
            return jsonify({'error': 'Pago no completado'}), 400

        # Calcular total y preparar productos
        productos_pedido = []
        total = Decimal('0.00')

        #INICIA LOS CAMBIOS INDICADOS EN FASE 3
        # RECALCULO DE SEGURIDAD (Mitiga E42): Uso de precio oficial desde DB
        for item in carrito:
            producto = Producto.query.get(item['id'])
            if producto and producto.activo:
                precio = producto.precio_venta()
                cantidad = item['cantidad']
                subtotal = precio * cantidad

                productos_pedido.append({
                    'id': producto.id,
                    'nombre': producto.nombre,
                    'cantidad': cantidad,
                    'precio': float(precio),
                    'subtotal': float(subtotal)
                })

                total += subtotal
        #FIN DE LOS CAMBIOS INDICADOS EN FASE 3

        # Calcular total con comisión PayPal (5.4%)
        comision_paypal = Decimal('5.4')
        total_con_comision = total * (Decimal('1') + (comision_paypal / Decimal('100')))

        # Obtener afiliado si existe
        afiliado_id = None
        afiliado_codigo = session.get('afiliado_codigo')
        if afiliado_codigo:
            afiliado = Afiliado.query.filter_by(codigo=afiliado_codigo, activo=True).first()
            if afiliado:
                afiliado_id = afiliado.id

        # Crear pedido marcado como pagado (PayPal ya procesó el pago)
        pedido = Pedido(
            cliente_nombre=nombre,
            cliente_telefono=telefono,
            cliente_direccion=direccion,
            productos_json=productos_pedido,
            total=total_con_comision,  # Total con comisión PayPal
            afiliado_id=afiliado_id,
            estado='pagado'  # Ya está pagado con PayPal
        )

        db.session.add(pedido)
        db.session.commit()

        # Si tiene vendedor, marcar como pagado y validar automáticamente
        if afiliado_id:
            pedido.marcar_como_pagado()
            # Validar automáticamente para que admin lo vea (PayPal es pago confirmado)
            pedido.validar_para_admin()
        else:
            # Pedido sin vendedor (tienda principal), solo marcar como pagado
            pedido.marcar_como_pagado()

        # --- SINCRONIZACIÓN CONTABLE AUTOMÁTICA ---
        # 1. Registrar el Ingreso Bruto
        monto_bruto = float(total_con_comision)
        register_transaction(
            tipo='ingreso',
            monto=monto_bruto,
            categoria='venta',
            fuente='paypal',
            descripcion=f"Venta PayPal - Pedido #{pedido.id}",
            referencia_id=paypal_response.get('id')
        )

        # 2. Registrar el Gasto por Comisión de PayPal (Recargo)
        monto_comision = float(total_con_comision - total)
        if monto_comision > 0:
            register_transaction(
                tipo='gasto',
                monto=monto_comision,
                categoria='comision',
                fuente='paypal',
                descripcion=f"Comisión PayPal - Pedido #{pedido.id}",
                referencia_id=f"FEE-{paypal_response.get('id')}"
            )

        # 3. Generar Factura Automática
        from utils.billing import calculate_invoice_data
        from models import Factura
        try:
            datos_fac = calculate_invoice_data(pedido)
            nueva_f = Factura(
                numero_factura=Factura.generar_numero_correlativo(),
                pedido_id=pedido.id,
                subtotal=datos_fac['subtotal'],
                iva_porcentaje=datos_fac['iva_porcentaje'],
                iva_monto=datos_fac['iva_monto'],
                total=datos_fac['total']
            )
            db.session.add(nueva_f)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Error Factura Automática: {str(e)}")

        # Limpiar carrito de sesión
        session['carrito'] = []

        return jsonify({
            'success': True,
            'pedido_id': pedido.id,
            'total': float(total_con_comision),
            'paypal_transaction_id': paypal_response.get('id')
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.exception(f"Error fatal capturando orden de PayPal: {e}")
        return jsonify({'error': 'No se pudo confirmar el pago. Contacta a soporte.'}), 500


#INICIA LOS CAMBIOS INDICADOS EN FASE 3
@bp.route('/paypal-webhook', methods=['POST'])
def paypal_webhook():
    """
    [FASE 4 / E43 - ERRORES MEDIOS] Blindaje Transaccional
    Maneja notificaciones asíncronas de PayPal para evitar pérdida de pedidos.
    ¡SEGURIDAD CRÍTICA APLICADA!: Verificación criptográfica de la firma del webhook.
    """
    from models import Pedido
    from app import db

    # 1. Extraer cabeceras criptográficas de PayPal
    auth_algo = request.headers.get('PAYPAL-AUTH-ALGO')
    cert_url = request.headers.get('PAYPAL-CERT-URL')
    transmission_id = request.headers.get('PAYPAL-TRANSMISSION-ID')
    transmission_sig = request.headers.get('PAYPAL-TRANSMISSION-SIG')
    transmission_time = request.headers.get('PAYPAL-TRANSMISSION-TIME')

    # 2. Validación: Si falta alguna cabecera, bloquear el intento (posible spoofing)
    if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time]):
        log_security_event('PAYPAL_WEBHOOK', 'BLOCKED', details="Intento de webhook sin cabeceras criptográficas válidas.")
        return jsonify({'error': 'Violación de seguridad: Faltan firmas criptográficas'}), 403

    try:
        data = request.get_json()
        if not data:
            current_app.logger.warning("Webhook de PayPal recibido sin datos JSON")
            return jsonify({'status': 'no_data'}), 400

        # 3. Verificación Criptográfica mediante API oficial de PayPal
        access_token = get_paypal_access_token()
        webhook_id = current_app.config.get('PAYPAL_WEBHOOK_ID')

        if not access_token:
            current_app.logger.error("No se pudo obtener el token de PayPal para verificar el webhook")
            return jsonify({'error': 'Error de autenticación interna'}), 500

        if not webhook_id:
            current_app.logger.error("VULNERABILIDAD CRÍTICA: PAYPAL_WEBHOOK_ID no está configurado. Rechazando webhook por seguridad.")
            return jsonify({'error': 'Sistema no configurado para validación criptográfica'}), 500

        # Validación estricta obligatoria contra PayPal
        mode = current_app.config.get('PAYPAL_MODE', 'sandbox')
        verify_url = "https://api-m.paypal.com/v1/notifications/verify-webhook-signature" if mode == 'live' else "https://api-m.sandbox.paypal.com/v1/notifications/verify-webhook-signature"

        verify_payload = {
            "auth_algo": auth_algo,
            "cert_url": cert_url,
            "transmission_id": transmission_id,
            "transmission_sig": transmission_sig,
            "transmission_time": transmission_time,
            "webhook_id": webhook_id,
            "webhook_event": data
        }

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        resp = requests.post(verify_url, headers=headers, json=verify_payload)
        if resp.status_code == 200:
            verification_status = resp.json().get('verification_status')
            if verification_status != 'SUCCESS':
                log_security_event('PAYPAL_WEBHOOK', 'BLOCKED', details="Firma criptográfica manipulada (rechazada por PayPal)")
                return jsonify({'error': 'Firma criptográfica inválida. Pago falso detectado.'}), 403
        else:
            current_app.logger.error(f"Fallo verificando firma de PayPal: {resp.text}")
            return jsonify({'error': 'Error comunicando con PayPal para validación'}), 502

        # 4. Procesamiento Seguro del Evento
        event_type = data.get('event_type')
        resource = data.get('resource', {})
        current_app.logger.info(f"Webhook PayPal recibido y validado: {event_type}")

        # Verificamos eventos de pago completado
        if event_type in ['PAYMENT.CAPTURE.COMPLETED', 'CHECKOUT.ORDER.APPROVED']:
            paypal_id = resource.get('id')
            custom_id = resource.get('custom_id')

            if custom_id:
                pedido = Pedido.query.get(custom_id)
                if pedido and pedido.estado != 'pagado':
                    pedido.estado = 'pagado'
                    pedido.marcar_como_pagado()
                    db.session.commit()
                    current_app.logger.info(f"Pedido {custom_id} actualizado a 'pagado' vía Webhook Seguro")

            return jsonify({'status': 'procesado_seguro'}), 200

        return jsonify({'status': 'evento_no_critico'}), 200

    except Exception as e:
        current_app.logger.error(f"Error procesando Webhook de PayPal: {e}")
        return jsonify({'status': 'error_interno'}), 500
#FIN DE LOS CAMBIOS INDICADOS EN FASE 4