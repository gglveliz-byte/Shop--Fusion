from models import db, Oportunidad, ETAPAS_OPORTUNIDAD, Pedido
from decimal import Decimal
from datetime import datetime

def create_deal(data):
    """
    Paso 2.1: Crea o actualiza una oportunidad en el CRM.
    data: {cliente_nombre, valor_estimado, etapa, probabilidad, notas, afiliado_id}
    """
    try:
        opportunity_id = data.get('id')
        if opportunity_id:
            op = Oportunidad.query.get(opportunity_id)
            if not op:
                return {"success": False, "error": "Oportunidad no encontrada"}
        else:
            op = Oportunidad()
            db.session.add(op)

        op.cliente_nombre = data.get('cliente_nombre', op.cliente_nombre)
        
        if 'valor_estimado' in data:
            op.valor_estimado = Decimal(str(data.get('valor_estimado')))
        
        op.etapa = data.get('etapa', op.etapa or 'prospecto')
        
        if 'probabilidad' in data:
            op.probabilidad = int(data.get('probabilidad'))

        op.notas = data.get('notas', op.notas)
        op.afiliado_id = data.get('afiliado_id', op.afiliado_id)

        db.session.commit()
        return {"success": True, "id": op.id, "mensaje": f"Negocio de '{op.cliente_nombre}' gestionado."}
        
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}

def update_deal_stage(opportunity_id, new_stage):
    """
    Paso 2.2: Cambia la etapa de un negocio y ajusta la probabilidad automáticamente.
    """
    try:
        op = Oportunidad.query.get(opportunity_id)
        if not op: return {"success": False, "error": "Negocio no encontrado"}
        
        etapas_validas = [e[0] for e in ETAPAS_OPORTUNIDAD]
        if new_stage not in etapas_validas:
            return {"success": False, "error": f"Etapa '{new_stage}' no válida."}

        op.etapa = new_stage
        probabilidades = {'prospecto': 10, 'contactado': 25, 'negociacion': 50, 'cerrado_ganado': 100, 'cerrado_perdido': 0}
        op.probabilidad = probabilidades.get(new_stage, op.probabilidad)

        db.session.commit()
        return {"success": True, "mensaje": f"Etapa actualizada a {new_stage}"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}

def forecast_revenue():
    """
    Paso 2.3: Desarrollo de cálculos de Forecast (Proyección de ingresos).
    Extrae estadísticas para que la IA genere el reporte estratégico.
    """
    deals = Oportunidad.query.all()
    summary = {
        "total_deals": len(deals),
        "valor_nominal_total": float(sum(d.valor_estimado for d in deals)),
        "forecast_ingresos": sum(float(d.valor_estimado) * (d.probabilidad / 100.0) for d in deals),
        "etapas": {},
        "lista_negocios": [{"id": d.id, "cliente": d.cliente_nombre, "valor": float(d.valor_estimado), "etapa": d.etapa} for d in deals]
    }
    for d in deals:
        summary["etapas"][d.etapa] = summary["etapas"].get(d.etapa, 0) + 1
    return summary

def generate_executive_summary():
    """
    Backlog: Generar resúmenes ejecutivos automáticos usando Qwen-Max.
    Cruza Ventas Reales vs Proyecciones CRM.
    """
    pedidos_pagados = Pedido.query.filter_by(estado='pagado').all()
    ventas_reales = float(sum(p.total for p in pedidos_pagados))
    conteo_ventas = len(pedidos_pagados)
    crm = forecast_revenue()

    return {
        "ventas_reales": {"monto": ventas_reales, "cantidad": conteo_ventas},
        "crm_pipeline": {
            "total_negocios": crm['total_deals'],
            "forecast": crm['forecast_ingresos'],
            "valor_potencial": crm['valor_nominal_total']
        },
        "analisis": {
            "brecha": crm['valor_nominal_total'] - ventas_reales,
            "eficiencia": (conteo_ventas / crm['total_deals'] * 100) if crm['total_deals'] > 0 else 0
        }
    }
