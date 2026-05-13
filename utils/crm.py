from models import db, Oportunidad, ETAPAS_OPORTUNIDAD
from decimal import Decimal
from datetime import datetime

def upsert_opportunity(data):
    """
    Paso 2.1: Crea o actualiza una oportunidad en el CRM.
    data: {cliente_nombre, valor_estimado, etapa, probabilidad, notas, afiliado_id}
    """
    try:
        # Si viene un ID, intentamos actualizar
        opportunity_id = data.get('id')
        if opportunity_id:
            op = Oportunidad.query.get(opportunity_id)
            if not op:
                return {"success": False, "error": "Oportunidad no encontrada"}
        else:
            # Crear nueva
            op = Oportunidad()
            db.session.add(op)

        # Asignar campos (manteniendo los actuales si no vienen en la data)
        op.cliente_nombre = data.get('cliente_nombre', op.cliente_nombre)
        
        if 'valor_estimado' in data:
            op.valor_estimado = Decimal(str(data.get('valor_estimado')))
        
        op.etapa = data.get('etapa', op.etapa or 'prospecto')
        
        if 'probabilidad' in data:
            op.probabilidad = int(data.get('probabilidad'))
        
        op.notas = data.get('notas', op.notas)
        op.afiliado_id = data.get('afiliado_id', op.afiliado_id)

        db.session.commit()
        return {
            "success": True, 
            "id": op.id, 
            "mensaje": f"Oportunidad de '{op.cliente_nombre}' gestionada correctamente."
        }
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}

def update_opportunity_stage(opportunity_id, new_stage):
    """
    Paso 2.2: Cambia la etapa de un negocio y ajusta la probabilidad automáticamente.
    """
    try:
        op = Oportunidad.query.get(opportunity_id)
        if not op:
            return {"success": False, "error": "Negocio no encontrado"}
        
        # Validar que la etapa sea una de las oficiales definidas en models.py
        etapas_validas = [e[0] for e in ETAPAS_OPORTUNIDAD]
        if new_stage not in etapas_validas:
            return {"success": False, "error": f"Etapa '{new_stage}' no es válida."}

        op.etapa = new_stage
        
        # Lógica de probabilidad automática basada en la etapa
        probabilidades_sugeridas = {
            'prospecto': 10,
            'contactado': 25,
            'negociacion': 50,
            'cerrado_ganado': 100,
            'cerrado_perdido': 0
        }
        op.probabilidad = probabilidades_sugeridas.get(new_stage, op.probabilidad)

        db.session.commit()
        return {"success": True, "mensaje": f"Negocio movido a la etapa: {new_stage}"}
    except Exception as e:
        db.session.rollback()
        return {"success": False, "error": str(e)}

def get_pipeline_summary(afiliado_id=None):
    """
    Paso 2.3: Desarrollo de cálculos de Forecast (Proyección de ingresos).
    Extrae estadísticas para que la IA genere el reporte estratégico.
    """
    query = Oportunidad.query
    if afiliado_id:
        query = query.filter_by(afiliado_id=afiliado_id)
    
    deals = query.all()
    
    summary = {
        "total_deals": len(deals),
        "valor_nominal_total": float(sum(d.valor_estimado for d in deals)),
        "etapas_conteo": {},
        "forecast_ingresos": 0.0 # Cálculo: Valor * (Probabilidad/100)
    }

    for d in deals:
        # Contar por etapa
        summary["etapas_conteo"][d.etapa] = summary["etapas_conteo"].get(d.etapa, 0) + 1
        
        # Calcular Forecast (Ingreso ponderado)
        summary["forecast_ingresos"] += float(d.valor_estimado) * (d.probabilidad / 100.0)

    return summary
