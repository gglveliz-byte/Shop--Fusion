from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from decimal import Decimal

# Crear instancia de SQLAlchemy
db = SQLAlchemy()

# Modelo de Administrador
class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

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


# Modelo de Afiliado
class Afiliado(UserMixin, db.Model):
    __tablename__ = 'afiliados'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    codigo = db.Column(db.String(20), unique=True, nullable=False, index=True)
    porcentaje_comision = db.Column(db.Numeric(5, 2), nullable=False, default=80.00)  # Default 80%
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    pedidos = db.relationship('Pedido', backref='afiliado', lazy='dynamic')
    comisiones = db.relationship('Comision', backref='afiliado', lazy='dynamic')

    def set_password(self, password):
        """Encriptar contraseña"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verificar contraseña"""
        return check_password_hash(self.password_hash, password)

    def get_id(self):
        """Override get_id para Flask-Login"""
        return f'afiliado_{self.id}'

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


# Modelo de Producto
class Producto(db.Model):
    __tablename__ = 'productos'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(200), nullable=False)
    descripcion = db.Column(db.Text)
    precio_final = db.Column(db.Numeric(10, 2), nullable=False)
    precio_proveedor = db.Column(db.Numeric(10, 2), nullable=False)
    precio_oferta = db.Column(db.Numeric(10, 2), nullable=True)
    imagen = db.Column(db.String(300))  # Mantener por compatibilidad (imagen principal)
    imagenes = db.Column(db.JSON, default=list)  # Lista de URLs de imágenes
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    def calcular_margen(self):
        """Calcular margen del producto"""
        if self.precio_oferta:
            return self.precio_oferta - self.precio_proveedor
        return self.precio_final - self.precio_proveedor

    def precio_venta(self):
        """Obtener precio de venta (con oferta si existe)"""
        return self.precio_oferta if self.precio_oferta else self.precio_final

    def calcular_comision_afiliado(self, porcentaje_comision):
        """Calcular comisión que ganaría un afiliado con cierto porcentaje"""
        margen = self.calcular_margen()
        return margen * (porcentaje_comision / Decimal('100'))

    def __repr__(self):
        return f'<Producto {self.nombre}>'


# Modelo de Pedido
class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    cliente_nombre = db.Column(db.String(100), nullable=False)
    cliente_telefono = db.Column(db.String(20), nullable=False)
    cliente_direccion = db.Column(db.Text, nullable=False)
    productos_json = db.Column(db.JSON, nullable=False)  # [{id, nombre, cantidad, precio}]
    total = db.Column(db.Numeric(10, 2), nullable=False)
    estado = db.Column(db.String(20), default='pendiente')  # pendiente, pagado
    afiliado_id = db.Column(db.Integer, db.ForeignKey('afiliados.id'), nullable=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)
    pagado_en = db.Column(db.DateTime, nullable=True)

    # Relaciones
    comisiones = db.relationship('Comision', backref='pedido', lazy='dynamic', cascade='all, delete-orphan')

    def marcar_como_pagado(self):
        """Marcar pedido como pagado y generar comisiones"""
        if self.estado == 'pagado':
            return  # Ya está pagado

        self.estado = 'pagado'
        self.pagado_en = datetime.utcnow()

        # Si tiene afiliado asociado, calcular y crear comisión
        if self.afiliado_id:
            self._generar_comision()

        db.session.commit()

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
