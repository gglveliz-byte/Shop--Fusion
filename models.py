import os
import bleach
from sqlalchemy.orm import validates
from cryptography.fernet import Fernet
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from decimal import Decimal

# Crear instancia de SQLAlchemy
db = SQLAlchemy()

# [FASE 3 / HARDENING - SANITIZACIÓN]
def sanitize_html(text):
    """Limpia el texto de cualquier etiqueta HTML peligrosa (Anti-XSS)"""
    if not text: return text
    # bleach.clean elimina etiquetas como <script>, <iframe>, etc.
    return bleach.clean(text, tags=[], attributes={}, strip=True)

# [FASE 3 / HARDENING - CIFRADO PII]

# Obtener la llave maestra desde el entorno
_fernet_key = os.environ.get('FERNET_KEY')
if not _fernet_key:
    # SEGURIDAD CRÍTICA: Jamás generar una llave efímera en memoria.
    # Si el servidor se reinicia, la llave cambia y toda la base de datos se vuelve irrecuperable.
    raise EnvironmentError(
        "ERROR CRÍTICO DE PÉRDIDA DE DATOS: FERNET_KEY no está configurada en el entorno. "
        "Debes generar una llave permanente (ej. con python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\") "
        "y guardarla en tu archivo .env para evitar destrucción de datos encriptados al reiniciar."
    )

cipher_suite = Fernet(_fernet_key.encode())

def encrypt_data(data):
    """Cifra un string y retorna el token cifrado."""
    if not data: return data
    return cipher_suite.encrypt(data.encode()).decode()

def decrypt_data(data):
    """Descifra un token y retorna el string original."""
    if not data: return data
    try:
        return cipher_suite.decrypt(data.encode()).decode()
    except Exception:
        # Si el dato no está cifrado (datos antiguos), lo devolvemos tal cual
        return data

# Modelo de Administrador
class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # [MODIFICACIÓN SEGURIDAD TC015]
    # Se añadió propiedad 'is_admin' para identificación robusta en plantillas.
    # Archivos que dependen de este cambio: templates/base.html
    @property
    def is_admin(self):
        return True

    @property
    def is_afiliado(self):
        return False

    def set_password(self, password):
        """Encriptar contraseña"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Override get_id para Flask-Login"""
        return f'admin_{self.id}'

    def __repr__(self):
        return f'<Admin {self.username}>'


# Modelo de Afiliado (Vendedor)
class Afiliado(UserMixin, db.Model):
    __tablename__ = 'afiliados'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    porcentaje_comision = db.Column(db.Numeric(5, 2), nullable=False, default=80.00)  # Default 80%
    # [MODIFICACIÓN SEGURIDAD - FASE 3]
    # Se renombró la variable interna a 'whatsapp_encrypted' pero la columna en DB sigue siendo 'whatsapp'.
    whatsapp_encrypted = db.Column('whatsapp', db.String(500), nullable=True)
    activo = db.Column(db.Boolean, default=True)

    # @property: Convierte esta función en un "atributo" falso. 
    # Cuando haces 'afiliado.whatsapp', se ejecuta esto y te devuelve el dato ya descifrado.
    @property
    def whatsapp(self):
        """Descifra el número de WhatsApp automáticamente al leerlo"""
        return decrypt_data(self.whatsapp_encrypted)

    # @whatsapp.setter: Se ejecuta cuando intentas guardar algo: 'afiliado.whatsapp = "123"'.
    # Antes de guardarlo en la base de datos, lo cifra automáticamente.
    @whatsapp.setter
    def whatsapp(self, value):
        """Cifra el número de WhatsApp automáticamente antes de guardarlo"""
        self.whatsapp_encrypted = encrypt_data(value)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # [MODIFICACIÓN SEGURIDAD TC015]
    # Se añadió propiedad 'is_afiliado' para identificación robusta en plantillas.
    # Archivos que dependen de este cambio: templates/base.html
    @property
    def is_afiliado(self):
        return True

    @property
    def is_admin(self):
        return False

    # [FASE 3 / E11 - ERRORES MEDIOS] Relaciones optimizadas con carga ansiosa
    pedidos = db.relationship('Pedido', backref='afiliado', lazy='dynamic')
    comisiones = db.relationship('Comision', backref='afiliado', lazy='dynamic')
    oportunidades = db.relationship('Oportunidad', backref='vendedor', lazy='dynamic')

    def set_password(self, password):
        """Encriptar contraseña"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Override get_id para Flask-Login"""
        return f'afiliado_{self.id}'

    # [PASO 2 - SANITIZACIÓN]
    @validates('nombre')
    def validate_nombre(self, key, value):
        """Sanitiza el nombre del afiliado (Anti-XSS)"""
        return sanitize_html(value)

    def total_comisiones_pendientes(self):
        """Calcular total de comisiones pendientes"""
        return db.session.query(db.func.sum(Comision.monto))\
            .filter(Comision.afiliado_id == self.id, Comision.estado == 'pendiente')\
            .scalar() or Decimal('0.00')

    def total_comisiones_generadas(self):
        """Calcular total de comisiones generadas"""
        return db.session.query(db.func.sum(Comision.monto))\
            .filter(Comision.afiliado_id == self.id, Comision.estado == 'generada')\
            .scalar() or Decimal('0.00')

    def total_comisiones_pagadas(self):
        """Calcular total de comisiones pagadas"""
        return db.session.query(db.func.sum(Comision.monto))\
            .filter(Comision.afiliado_id == self.id, Comision.estado == 'pagada')\
            .scalar() or Decimal('0.00')

    def total_ganado(self):
        """Calcular total ganado (generadas + pagadas)"""
        return self.total_comisiones_generadas() + self.total_comisiones_pagadas()

    def __repr__(self):
        return f'<Afiliado {self.codigo} - {self.nombre}>'


# Categorías disponibles para productos
CATEGORIAS_PRODUCTO = [
    ('telefonos', 'Teléfonos'),
    ('computadoras', 'Computadoras'),
    ('perfumes', 'Perfumes'),
    ('ropa', 'Ropa'),
    ('zapatos', 'Zapatos'),
    ('herramientas', 'Herramientas'),
    ('hogar', 'Hogar'),
    ('electronica', 'Electrónica'),
    ('accesorios', 'Accesorios'),
    ('otros', 'Otros')
]


# Modelo de Producto
class Producto(db.Model):
    __tablename__ = 'productos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    categoria = db.Column(db.String(50), default='otros', index=True)  # Categoría del producto
    precio_final = db.Column(db.Numeric(10, 2), nullable=False)
    precio_proveedor = db.Column(db.Numeric(10, 2), nullable=False)
    precio_oferta = db.Column(db.Numeric(10, 2), nullable=True)
    imagen = db.Column(db.String(300))  # Mantener por compatibilidad (imagen principal local)
    imagenes = db.Column(db.JSON, default=list)  # Lista de imágenes adicionales locales
    imagen_url = db.Column(db.String(500))  # URL externa de imagen principal
    imagenes_url = db.Column(db.JSON, default=list)  # Lista de URLs externas de imágenes
    #INICIA LOS CAMBIOS INDICADOS EN FASE 3
    # Columna stock: Mitiga el error crítico E41 (Inventarios Ciegos)
    stock = db.Column(db.Integer, default=0, nullable=False)
    # [FASE 1 - HERRAMIENTA INVENTARIO EN TIEMPO REAL] Campo en memoria para cotizaciones y bloqueos
    stock_reservado = db.Column(db.Integer, default=0, nullable=False)
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 3

    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # [PASO 2 - SANITIZACIÓN]
    @validates('nombre', 'descripcion')
    def validate_producto_text(self, key, value):
        """Sanitiza campos de texto del producto (Anti-XSS)"""
        return sanitize_html(value)

    #INICIA LOS CAMBIOS INDICADOS EN FASE 3
    # Métodos para la gestión de stock
    def reducir_stock(self, cantidad):
        """Reduce el stock disponible. Retorna True si fue exitoso."""
        if self.stock >= cantidad:
            self.stock -= cantidad
            return True
        return False

    def aumentar_stock(self, cantidad):
        """Aumenta el stock disponible."""
        self.stock += cantidad
        return True

    def esta_disponible(self, cantidad=1):
        """Verifica si hay stock real suficiente (descontando las reservas temporales) y el producto está activo."""
        stock_real = self.stock - self.stock_reservado
        return self.activo and stock_real >= cantidad
    #FIN DE LOS CAMBIOS INDICADOS EN FASE 3

    def calcular_margen(self):
        """Calcular margen del producto"""
        if self.precio_oferta:
            return self.precio_oferta - self.precio_proveedor
        return self.precio_final - self.precio_proveedor

    def precio_venta(self):
        """Obtener precio de venta (con oferta si existe)"""
        return self.precio_oferta if self.precio_oferta else self.precio_final

    def to_dict(self):
        """FASE 4: Centralizar la serialización del producto (DRY)"""
        todas_imagenes = self.obtener_todas_imagenes()
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'categoria': self.categoria or 'otros',
            'precio_final': float(self.precio_final),
            'precio_oferta': float(self.precio_oferta) if self.precio_oferta else None,
            'imagen': todas_imagenes[0] if todas_imagenes else None,
            'imagenes': todas_imagenes,
            'stock': self.stock
        }

    def calcular_comision_afiliado(self, porcentaje_comision):
        """Calcular comisión que ganaría un afiliado con cierto porcentaje"""
        margen = self.calcular_margen()
        return margen * (porcentaje_comision / Decimal('100'))

    def obtener_imagen_principal(self):
        """Obtener la imagen principal (prioriza URL externa sobre local)"""
        if self.imagen_url:
            return self.imagen_url
        elif self.imagen:
            return f'/static/uploads/{self.imagen}'
        return '/static/img/no-image.png'

    def obtener_todas_imagenes(self):
        """Obtener todas las imágenes del producto (URLs externas + locales)"""
        todas = []

        # Agregar imagen principal
        if self.imagen_url:
            todas.append(self.imagen_url)
        elif self.imagen:
            todas.append(f'/static/uploads/{self.imagen}')

        # Agregar imágenes adicionales de URLs externas
        if self.imagenes_url:
            todas.extend(self.imagenes_url)

        # Agregar imágenes adicionales locales
        if self.imagenes:
            for img in self.imagenes:
                todas.append(f'/static/uploads/{img}')

        return todas if todas else ['/static/img/no-image.png']

    def __repr__(self):
        return f'<Producto {self.nombre}>'


# Modelo de Pedido
class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    cliente_nombre = db.Column(db.String(100), nullable=False)
    # [MODIFICACIÓN SEGURIDAD - FASE 3]
    # Mapeo de columnas originales con lógica de cifrado transparente
    cliente_telefono_encrypted = db.Column('cliente_telefono', db.String(500), nullable=False)
    cliente_direccion_encrypted = db.Column('cliente_direccion', db.Text, nullable=False)

    @property
    def cliente_telefono(self):
        """Interceptor para descifrar el teléfono al vuelo"""
        return decrypt_data(self.cliente_telefono_encrypted)

    @cliente_telefono.setter
    def cliente_telefono(self, value):
        """Interceptor para cifrar el teléfono antes de persistir"""
        self.cliente_telefono_encrypted = encrypt_data(value)

    @property
    def cliente_direccion(self):
        """Interceptor para descifrar la dirección al vuelo"""
        return decrypt_data(self.cliente_direccion_encrypted)

    @cliente_direccion.setter
    def cliente_direccion(self, value):
        """Interceptor para cifrar la dirección antes de persistir"""
        self.cliente_direccion_encrypted = encrypt_data(value)
    productos_json = db.Column(db.JSON, nullable=False)  # [{id, nombre, cantidad, precio}]
    total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, pagado, cancelado
    afiliado_id = db.Column(db.Integer, db.ForeignKey('afiliados.id'), nullable=True)
    validado_por_vendedor = db.Column(db.Boolean, default=False)  # Si el vendedor validó el pago
    validado_en = db.Column(db.DateTime, nullable=True)  # Fecha de validación
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    pagado_en = db.Column(db.DateTime, nullable=True)
    metodo_pago = db.Column(db.String(30), nullable=True)
    pago_referencia = db.Column(db.String(100), nullable=True, unique=True)

    # [PASO 2 - SANITIZACIÓN]
    @validates('cliente_nombre', 'cliente_direccion')
    def validate_pedido_text(self, key, value):
        """Sanitiza datos del cliente (Anti-XSS)"""
        return sanitize_html(value)

    # [FASE 3 / E11 - ERRORES MEDIOS] Relación optimizada
    comisiones = db.relationship('Comision', backref='pedido', lazy='joined', cascade='all, delete-orphan')

    def marcar_como_pagado(self):
        """Marcar pedido como pagado (solo cambia estado, no genera comisión aún)"""
        if self.estado == 'pagado':
            return  # Ya está pagado

        self.estado = 'pagado'
        self.pagado_en = datetime.utcnow()
        db.session.commit()

    def marcar_como_cancelado(self):
        """Marcar pedido como cancelado"""
        if self.estado == 'cancelado':
            return  # Ya está cancelado
        
        if self.estado == 'pagado' and self.validado_por_vendedor:
            # Si ya está pagado y validado, no se puede cancelar fácilmente
            return False

        self.estado = 'cancelado'
        db.session.commit()
        return True

    def validar_para_admin(self):
        """Validar pedido para que el admin lo vea y se genere la comisión"""
        if not self.estado == 'pagado':
            return False  # Debe estar pagado primero

        if self.validado_por_vendedor:
            return True  # Ya está validado

        self.validado_por_vendedor = True
        self.validado_en = datetime.utcnow()

        # Si tiene afiliado asociado, calcular y crear comisión
        if self.afiliado_id:
            self._generar_comision()

        db.session.commit()
        return True

    def _generar_comision(self):
        """Generar comisión para el afiliado"""
        afiliado = Afiliado.query.get(self.afiliado_id)
        if not afiliado:
            return

        # Calcular margen total del pedido
        margen_total = Decimal('0.00')

        for item in self.productos_json:
            producto = Producto.query.get(item['id'])
            if producto:
                margen_unitario = producto.calcular_margen()
                margen_total += margen_unitario * Decimal(str(item['cantidad']))

        # Calcular comisión según porcentaje del afiliado
        monto_comision = margen_total * (afiliado.porcentaje_comision / Decimal('100'))

        # Crear registro de comisión
        comision = Comision(
            pedido_id=self.id,
            afiliado_id=self.afiliado_id,
            margen=margen_total,
            monto=monto_comision,
            estado='generada'
        )

        db.session.add(comision)

    def __repr__(self):
        return f'<Pedido #{self.id} - {self.cliente_nombre}>'


# Modelo de Comisión
class Comision(db.Model):
    __tablename__ = 'comisiones'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False)
    afiliado_id = db.Column(db.Integer, db.ForeignKey('afiliados.id'), nullable=False)
    margen = db.Column(db.Numeric(10, 2), nullable=False)
    monto = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, generada, pagada
    pagada_en = db.Column(db.DateTime, nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def marcar_como_pagada(self):
        """Marcar comisión como pagada"""
        self.estado = 'pagada'
        self.pagada_en = datetime.utcnow()
        db.session.commit()

    def __repr__(self):
        return f'<Comision #{self.id} - Pedido #{self.pedido_id} - ${self.monto}>'


# ==================== CRM & PIPELINE MODELS ====================

ETAPAS_OPORTUNIDAD = [
    ('prospecto', 'Prospecto (Lead)'),
    ('contactado', 'Contactado'),
    ('negociacion', 'En Negociación'),
    ('cerrado_ganado', 'Cerrado (Ganado)'),
    ('cerrado_perdido', 'Cerrado (Perdido)')
]

class Oportunidad(db.Model):
    """
    Representa una oportunidad de venta o prospecto en el pipeline CRM.
    Permite a la IA rastrear el progreso de una venta antes de que se convierta en pedido.
    """
    __tablename__ = 'oportunidades'

    id = db.Column(db.Integer, primary_key=True)
    cliente_nombre = db.Column(db.String(100), nullable=False)
    valor_estimado = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    etapa = db.Column(db.String(30), default='prospecto', index=True)
    probabilidad = db.Column(db.Integer, default=10)  # 0 a 100%
    notas = db.Column(db.Text)
    
    # Vinculación con el vendedor (afiliado)
    afiliado_id = db.Column(db.Integer, db.ForeignKey('afiliados.id'), nullable=True)
    
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # [PASO 2 - SANITIZACIÓN]
    @validates('cliente_nombre', 'notas')
    def validate_crm_text(self, key, value):
        """Sanitiza datos del CRM (Anti-XSS)"""
        return sanitize_html(value)

    def __repr__(self):
        return f'<Oportunidad {self.cliente_nombre} - {self.etapa}>'


# ==================== MÓDULO DE FACTURACIÓN ====================

class Factura(db.Model):
    """
    Modelo para gestionar la facturación legal de los pedidos.
    Permite el seguimiento de montos, impuestos y estado de cobro.
    """
    __tablename__ = 'facturas'

    id = db.Column(db.Integer, primary_key=True)
    numero_factura = db.Column(db.String(20), unique=True, nullable=False, index=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('pedidos.id'), nullable=False, unique=True)
    
    # Desglose Financiero
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    iva_porcentaje = db.Column(db.Numeric(5, 2), nullable=False)
    iva_monto = db.Column(db.Numeric(12, 2), nullable=False)
    total = db.Column(db.Numeric(12, 2), nullable=False)
    
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, pagada, anulada
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación uno a uno con Pedido
    pedido = db.relationship('Pedido', backref=db.backref('factura', uselist=False))

    @classmethod
    def generar_numero_correlativo(cls):
        """Genera el siguiente número de factura automático (ej: FAC-0001)"""
        ultima = cls.query.order_by(cls.id.desc()).first()
        if not ultima:
            return "FAC-0001"
        try:
            ultimo_num = int(ultima.numero_factura.split('-')[1])
            return f"FAC-{(ultimo_num + 1):04d}"
        except:
            return "FAC-0001"

    def __repr__(self):
        return f'<Factura {self.numero_factura} - Pedido #{self.pedido_id}>'


# User loader para Flask-Login
def setup_login_manager(login_manager):
    """Configurar login manager"""
    @login_manager.user_loader
    def load_user(user_id):
        """Cargar usuario para Flask-Login"""
        # Formato: "admin_1" o "afiliado_5"
        if user_id.startswith('admin_'):
            return Admin.query.get(int(user_id.split('_')[1]))
        elif user_id.startswith('afiliado_'):
            return Afiliado.query.get(int(user_id.split('_')[1]))
        return None


# ==================== CONFIGURACIÓN WHITE-LABEL ====================

class Configuracion(db.Model):
    """
    Modelo para almacenar la identidad visual y configuración dinámica del sitio.
    Permite transformar el sistema en White-Label (Marca Blanca).
    """
    __tablename__ = 'configuraciones'

    id = db.Column(db.Integer, primary_key=True)
    
    # Identidad
    nombre_tienda = db.Column(db.String(100), default='Mi Tienda Online')
    logo_path = db.Column(db.String(300), nullable=True)
    favicon_path = db.Column(db.String(300), nullable=True)
    
    # Estética (Colores Hexadecimales)
    color_primario = db.Column(db.String(7), default='#6366f1')
    color_secundario = db.Column(db.String(7), default='#22c55e')
    color_acento = db.Column(db.String(7), default='#06b6d4')
    
    # Contacto y Textos
    # [MODIFICACIÓN SEGURIDAD - FASE 3]
    # Blindaje del contacto de la tienda (White-Label Protegido)
    whatsapp_contacto_encrypted = db.Column('whatsapp_contacto', db.String(500), nullable=True)

    @property
    def whatsapp_contacto(self):
        """Descarga y descifra el contacto para mostrarlo en la web"""
        return decrypt_data(self.whatsapp_contacto_encrypted)

    @whatsapp_contacto.setter
    def whatsapp_contacto(self, value):
        """Cifra el contacto antes de guardarlo en la configuración"""
        self.whatsapp_contacto_encrypted = encrypt_data(value)
    mensaje_bienvenida = db.Column(db.String(255), default='¡Bienvenido a nuestra tienda!')
    mensaje_footer = db.Column(db.String(255), default='Tu tienda online de confianza')
    mensaje_copyright = db.Column(db.String(255), default='© 2026 Todos los derechos reservados.')
    
    # Metadatos SEO
    meta_descripcion = db.Column(db.Text, nullable=True)
    
    # Configuración de Facturación (Fase 1)
    iva_porcentaje = db.Column(db.Numeric(5, 2), default=15.00)
    
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # [PASO 2 - SANITIZACIÓN]
    @validates('nombre_tienda', 'mensaje_bienvenida', 'mensaje_footer', 'mensaje_copyright', 'meta_descripcion')
    def validate_config_text(self, key, value):
        """Sanitiza la configuración de marca blanca (Anti-XSS)"""
        return sanitize_html(value)

    def __repr__(self):
        return f'<Configuracion {self.nombre_tienda}>'


# ==================== MÓDULO DE CONTABILIDAD (HERRAMIENTA 5) ====================

class Transaccion(db.Model):
    """
    Libro contable digital para registrar todos los movimientos financieros.
    Soporta ingresos, gastos y categorización para reportes de balance.
    """
    __tablename__ = 'transacciones'

    id = db.Column(db.Integer, primary_key=True)
    
    # "ingreso" o "gasto"
    tipo = db.Column(db.String(10), nullable=False) 
    
    monto = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Categorías: ventas, marketing, operativo, salarios, otros
    categoria = db.Column(db.String(50), default='otros')
    
    # Fuente: caja, banco, paypal
    fuente = db.Column(db.String(50), default='caja')
    
    descripcion = db.Column(db.String(255), nullable=True)
    
    # Enlace opcional a pedidos o facturas
    referencia_id = db.Column(db.String(50), nullable=True)
    
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Transaccion {self.tipo} - {self.monto} ({self.categoria})>'

# ==================== MÓDULO DE RESERVAS DE INVENTARIO (HERRAMIENTA 8) ====================

class ReservaStock(db.Model):
    """
    Tabla para mantener la persistencia de las reservas de inventario.
    Soluciona el problema de los hilos en memoria perdiéndose si el servidor se reinicia.
    """
    __tablename__ = 'reservas_stock'

    id = db.Column(db.Integer, primary_key=True)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False)
    fecha_expiracion = db.Column(db.DateTime, nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación
    producto = db.relationship('Producto', backref=db.backref('reservas', lazy=True))

    def __repr__(self):
        return f'<ReservaStock Prod:{self.producto_id} - Cant:{self.cantidad}>'


# ==================== MÓDULO DE SOPORTE (TICKETS) ====================

class TicketSoporte(db.Model):
    """
    Tabla para gestionar tickets de soporte creados desde el chatbot o canales externos.
    Los datos de contacto (PII) se cifran automáticamente al guardar.
    """
    __tablename__ = 'tickets_soporte'

    id = db.Column(db.Integer, primary_key=True)

    # Asunto y descripción del problema (sanitizados anti-XSS)
    asunto = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)

    # Prioridad del ticket
    prioridad = db.Column(
        db.Enum('baja', 'media', 'alta', 'critica', name='prioridad_ticket'),
        nullable=False,
        default='media'
    )

    # Estado actual del ticket
    estado = db.Column(
        db.Enum('abierto', 'en_progreso', 'resuelto', 'cerrado', name='estado_ticket'),
        nullable=False,
        default='abierto'
    )

    # Canal de origen: chat, email, formulario
    canal = db.Column(db.String(50), nullable=False, default='chat')

    # Datos de contacto del cliente (PII — cifrados)
    _contacto_nombre = db.Column('contacto_nombre', db.String(300), nullable=True)
    _contacto_email  = db.Column('contacto_email',  db.String(400), nullable=True)

    # Indica si el ticket fue escalado al equipo humano
    escalado = db.Column(db.Boolean, nullable=False, default=False)

    # Timestamps
    creado_en     = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resuelto_en   = db.Column(db.DateTime, nullable=True)

    # Relación con comentarios
    comentarios = db.relationship('ComentarioTicket', backref='ticket', lazy=True, cascade='all, delete-orphan')

    # --- Propiedades de cifrado PII ---
    @property
    def contacto_nombre(self):
        return decrypt_data(self._contacto_nombre) if self._contacto_nombre else None

    @contacto_nombre.setter
    def contacto_nombre(self, value):
        self._contacto_nombre = encrypt_data(sanitize_html(value)) if value else None

    @property
    def contacto_email(self):
        return decrypt_data(self._contacto_email) if self._contacto_email else None

    @contacto_email.setter
    def contacto_email(self, value):
        self._contacto_email = encrypt_data(sanitize_html(value)) if value else None

    # --- Validaciones ---
    @validates('asunto')
    def validate_asunto(self, key, value):
        return sanitize_html(value) if value else value

    @validates('descripcion')
    def validate_descripcion(self, key, value):
        return sanitize_html(value) if value else value

    # --- Helpers ---
    @property
    def numero(self):
        """Retorna un código legible tipo TKT-0042."""
        return f"TKT-{str(self.id).zfill(4)}"

    def to_dict(self):
        return {
            'id': self.id,
            'numero': self.numero,
            'asunto': self.asunto,
            'descripcion': self.descripcion,
            'prioridad': self.prioridad,
            'estado': self.estado,
            'canal': self.canal,
            'escalado': self.escalado,
            'contacto_nombre': self.contacto_nombre,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
            'actualizado_en': self.actualizado_en.isoformat() if self.actualizado_en else None,
            'resuelto_en': self.resuelto_en.isoformat() if self.resuelto_en else None,
        }

    def __repr__(self):
        return f'<TicketSoporte {self.numero} [{self.prioridad}] - {self.estado}>'


class ComentarioTicket(db.Model):
    """
    Comentarios asociados a un ticket de soporte.
    Pueden ser generados por la IA, el admin o el propio usuario.
    """
    __tablename__ = 'comentarios_tickets'

    id = db.Column(db.Integer, primary_key=True)

    ticket_id = db.Column(db.Integer, db.ForeignKey('tickets_soporte.id'), nullable=False)

    # Quién escribió el comentario: 'ia', 'admin', 'usuario'
    autor = db.Column(db.String(20), nullable=False, default='ia')

    contenido = db.Column(db.Text, nullable=False)

    creado_en = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    @validates('contenido')
    def validate_contenido(self, key, value):
        return sanitize_html(value) if value else value

    def to_dict(self):
        return {
            'id': self.id,
            'autor': self.autor,
            'contenido': self.contenido,
            'creado_en': self.creado_en.isoformat() if self.creado_en else None,
        }

    def __repr__(self):
        return f'<ComentarioTicket Ticket:{self.ticket_id} por {self.autor}>'

# ==================== MÓDULO DE BASE DE CONOCIMIENTO (FAQ - HERRAMIENTA 10) ====================

class DocumentoConocimiento(db.Model):
    """
    Tabla para almacenar los manuales, políticas y preguntas frecuentes.
    Actúa como el "cerebro" interno para que la IA responda consultas de soporte.
    """
    __tablename__ = 'documentos_conocimiento'

    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(50), default='general')
    contenido_texto = db.Column(db.Text, nullable=False)
    
    # Aquí guardaremos el vector matemático de la IA.
    # Usamos JSON en lugar de instalar bases de datos gigantes, para que funcione en Render (Free Tier)
    vector_embedding = db.Column(db.JSON, nullable=True) 
    
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    actualizado_en = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<DocumentoConocimiento {self.titulo}>'

# ==================== MÓDULO DE ASISTENTE Y AGENDA (HERRAMIENTA 13) ====================

class Recordatorio(db.Model):
    """
    Tabla para gestionar recordatorios y tareas del administrador delegadas a la IA.
    """
    __tablename__ = 'recordatorios'

    id = db.Column(db.Integer, primary_key=True)
    texto_tarea = db.Column(db.String(500), nullable=False)
    fecha_hora_programada = db.Column(db.DateTime, nullable=False)
    completado = db.Column(db.Boolean, default=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    """__repr__ define cómo se mostrará este objeto cuando se imprima en consola,
    aparezca en logs o durante tareas de depuración (debugging).
    Esto facilita identificar rápidamente el contenido del registro
    en lugar de mostrar únicamente una dirección de memoria."""
    
    def __repr__(self):
        return f'<Recordatorio {self.id}: {self.texto_tarea[:20]}...>'