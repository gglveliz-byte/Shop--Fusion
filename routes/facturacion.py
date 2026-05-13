from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from models import db, Pedido, Factura
from utils.billing import calculate_invoice_data
from datetime import datetime
from functools import wraps

bp = Blueprint('facturacion', __name__, url_prefix='/facturacion')

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Asumimos que el modelo Admin tiene una forma de identificarse o se usa la sesión
        if not hasattr(current_user, 'username'): # Verificación simple para Admin
             return jsonify({"error": "Acceso denegado. Se requiere rol administrativo."}), 403
        return f(*args, **kwargs)
    return decorated_function

@bp.route('/generar/<int:pedido_id>', methods=['POST'])
@admin_required
def generar_factura(pedido_id):
    """
    Paso 3.1: Genera una factura oficial a partir de un pedido pagado.
    """
    pedido = Pedido.query.get_or_404(pedido_id)

    # Validaciones de seguridad
    if pedido.estado != 'pagado':
        return jsonify({"error": "No se puede facturar un pedido que no esté pagado."}), 400
    
    if pedido.factura:
        return jsonify({
            "error": "Este pedido ya tiene una factura asociada.",
            "factura_id": pedido.factura.id,
            "numero": pedido.factura.numero_factura
        }), 400

    try:
        # 1. Usar el Motor de Impuestos (Paso 2)
        datos_calculados = calculate_invoice_data(pedido)

        # 2. Crear la Factura en la BD (Paso 1)
        nueva_factura = Factura(
            numero_factura=Factura.generar_numero_correlativo(),
            pedido_id=pedido.id,
            subtotal=datos_calculados['subtotal'],
            iva_porcentaje=datos_calculados['iva_porcentaje'],
            iva_monto=datos_calculados['iva_monto'],
            total=datos_calculados['total'],
            estado='emitida'
        )

        db.session.add(nueva_factura)
        db.session.commit()

        return jsonify({
            "success": True,
            "mensaje": f"Factura {nueva_factura.numero_factura} generada exitosamente.",
            "numero": nueva_factura.numero_factura,
            "factura_id": nueva_factura.id
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Error al generar factura: {str(e)}"}), 500

@bp.route('/<int:factura_id>', methods=['GET'])
@admin_required
def obtener_factura(factura_id):
    """
    Paso 3.2: Consulta de factura por ID (para humanos e IA).
    """
    factura = Factura.query.get_or_404(factura_id)
    
    return jsonify({
        "id": factura.id,
        "numero": factura.numero_factura,
        "pedido_id": factura.pedido_id,
        "cliente": factura.pedido.cliente_nombre,
        "subtotal": float(factura.subtotal),
        "iva_porcentaje": float(factura.iva_porcentaje),
        "iva_monto": float(factura.iva_monto),
        "total": float(factura.total),
        "estado": factura.estado,
        "fecha": factura.creado_en.strftime('%Y-%m-%d %H:%M:%S')
    })

@bp.route('/lista', methods=['GET'])
@admin_required
def listar_facturas():
    """
    Paso 3.3: Listado de todas las facturas del sistema.
    """
    facturas = Factura.query.order_by(Factura.creado_en.desc()).all()
    resultado = []
    for f in facturas:
        resultado.append({
            "id": f.id,
            "numero": f.numero_factura,
            "total": float(f.total),
            "estado": f.estado
        })
    return jsonify(resultado)
@bp.route('/ver_documento/<int:factura_id>')
@login_required
def ver_documento(factura_id):
    """
    Paso 3.3.2: Renderiza la factura con diseño profesional para impresión.
    """
    from flask import render_template
    factura = Factura.query.get_or_404(factura_id)
    return render_template('billing/factura_estilo.html', factura=factura)
