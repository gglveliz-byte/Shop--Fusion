from datetime import datetime
from decimal import Decimal
from models import db, Transaccion

def register_transaction(tipo, monto, categoria='otros', fuente='caja', descripcion=None, referencia_id=None):
    """
    Registra un movimiento en el libro contable.
    tipo: 'ingreso' o 'gasto'
    monto: valor numérico
    """
    try:
        nueva_t = Transaccion(
            tipo=tipo.lower(),
            monto=Decimal(str(monto)),
            categoria=categoria.lower(),
            fuente=fuente.lower(),
            descripcion=descripcion,
            referencia_id=referencia_id
        )
        db.session.add(nueva_t)
        db.session.commit()
        return {"success": True, "id": nueva_t.id, "mensaje": f"Transacción de {tipo} registrada."}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}

def get_account_balance():
    """
    Calcula el balance actual (Ingresos - Gastos).
    """
    transacciones = Transaccion.query.all()
    total_ingresos = sum(float(t.monto) for t in transacciones if t.tipo == 'ingreso')
    total_gastos = sum(float(t.monto) for t in transacciones if t.tipo == 'gasto')
    
    return {
        "ingresos": total_ingresos,
        "gastos": total_gastos,
        "balance": total_ingresos - total_gastos,
        "conteo": len(transacciones)
    }

def generate_monthly_report():
    """
    Genera un desglose de gastos e ingresos por categoría.
    """
    transacciones = Transaccion.query.all()
    reporte = {
        "categorias_gastos": {},
        "categorias_ingresos": {},
        "fuentes": {}
    }
    
    for t in transacciones:
        cat = t.categoria
        fuente = t.fuente
        monto = float(t.monto)
        
        if t.tipo == 'gasto':
            reporte["categorias_gastos"][cat] = reporte["categorias_gastos"].get(cat, 0) + monto
        else:
            reporte["categorias_ingresos"][cat] = reporte["categorias_ingresos"].get(cat, 0) + monto
            
        reporte["fuentes"][fuente] = reporte["fuentes"].get(fuente, 0) + (monto if t.tipo == 'ingreso' else -monto)
        
    return reporte
