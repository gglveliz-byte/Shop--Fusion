# 🟠 Severidad Alta (FASE 2)
**Nivel de Prioridad:** Alta.
**Objetivo:** Garantizar la integridad financiera del sistema, erradicando las alteraciones de los carritos de compra locales y la pérdida de pedidos post-pago por asincronía.

---

## 1. Desincronización de Precios (Fraude JS Frontal)
**El Problema:** El `index.html` utiliza una variable Javascript para calcular cuánto cobrar al usuario interactuando con la API frontal de PayPal. Como el "Backend" acepta cualquier precio enviado por el front, un maleante puede apretar `F12`, alterar a cantidad a pagar (ej: cambiar de `$1000` a `$1`) e igualmente recibir autorización criptográfica.

### Código de Solución Recomendado:
La arquitectura debe ser "The Backend is the Truth" (El backend tiene la razón). En `routes/tienda.py`:
```python
# Durante el procesamiento de PayPal en Checkout:
productos_json = request.json.get('carrito', [])

costo_real_total = 0.0
for item in productos_json:
    prod = Producto.query.get(item['id'])
    if not prod or not prod.activo:
        return jsonify({'error': 'Producto no disponible'}), 400
    
    # Priorizar ofertas vigentes directamente leyendo la BD inalterable
    precio = prod.precio_oferta if prod.precio_oferta else prod.precio_final
    costo_real_total += precio * item['cantidad']

# Enviar "costo_real_total" hacia la creacion del Request para PayPal, NO el precio JS
```

### 🔁 Alternativas:
Firmar digitalmente los "carritos" con `JWT Stateful`. Cuando el usuario agrega algo al carrito local de JS, el Servidor emite un Token firmado encriptando los precios inalterables de ese milisegundo. Esto requeriría reescribir toda la lógica de tu `index.html`. Repositar la re-verificación en el backend (como enseñado en el código) es más pragmático.

### ⚠️ Riesgos de Modificar esto:
Precisión matemática. Si el Javascript redondea un precio digamos a `$99.99` y tu base de datos flotante de Python en backend redondea a `$100.00`, el recibo que crea PayPal bloqueará la transacción arrojando `ORDER_MISMATCH_AMOUNT`. Se DEBE instruir al desarrollador para que use la libería nativa de Python `decimal.Decimal` en los costos para evitar esta colisión trágica de centavos.

---

## 2. Abandono de Interfaz ("El Dinero se cobró pero no hay Orden")
**El Problema:** La actual confirmación de compra depende de que el usuario haga click en el botón de PayPal, y que su navegador sobreviva lo suficiente para ejecutar el CallBack `onApprove` y mandar la confirmación al Backend. Si el internet del cliente se corta o este cierra la PC en ese preciso segundo de latencia, el dinero se debitará de su tarjeta pero `Shop Fusion` nunca se enterará, generando una queja contundente (Chargeback/Reembolso).

### Código de Solución Recomendado:
En `routes/tienda.py`, se debe registrar un Listener (Escuchador) para **Webhooks** asíncronos y aislarlo de la seguridad de Usuarios.
```python
# Este endpoint es llamado POR los servidores mundiales de PayPal, no por el cliente.
@bp.route('/api/webhooks/paypal', methods=['POST'])
@csrf.exempt  # ⬅️ VITAL: PayPal no tiene tu token CSRF, debes exceptuar esta ruta
def paypal_webhook():
    payload = request.json
    
    # 1. Validar el evento y el estado "Completado"
    if payload.get('event_type') == 'PAYMENT.CAPTURE.COMPLETED':
        order_guid = payload['resource']['id']
        
        # 2. Rescatar la orden en BD y cambiar el estado
        pedido_pendiente = Pedido.query.filter_by(paypal_order_id=order_guid).first()
        if pedido_pendiente:
            pedido_pendiente.estado = 'pagado'
            db.session.commit()
            
    return '', 200 # Avisar a PayPal que recibimos el mensaje
```

### 🔁 Alternativas:
Un "Mecanismo Cron" (un worker en background ejecutándose cada 5 minutos) en donde tu Servidor le pregunte forzosamente a PayPal: *"Oye, ¿esta orden vieja de id XXXX se procesó o no?"*, lo cual ahoga tu cuota Límite de las APIs y ahoga la base de datos leyendo cosas viejas, pero es inmune a las fallas de Webhooks caídos.

### ⚠️ Riesgos de Modificar esto:
Si utilizas `@csrf.exempt` para aceptar webhooks sin exigirle al desarrollador que valide las llaves criptográficas de la IP oficial de PayPal (`PAYPAL-AUTH-ALGO` headers), un hacker podría mandar un evento `POST` falso a tu web, tu sistema lo creería y soltaría mercancía gratis porque la validación estuvo mal hecha.
