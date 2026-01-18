# FIX PARA IMPORTS CIRCULARES

El error que estás viendo es por imports circulares. Ya arreglé `routes/tienda.py` y `routes/auth.py`.

Para arreglar `routes/admin.py` y `routes/afiliado.py`, necesitas agregar los imports dentro de cada función.

## Solución Rápida:

Agrega estas líneas al inicio de CADA función en `routes/admin.py` que use modelos:

```python
from models import Admin, Producto, Pedido, Afiliado, Comision
from app import db
```

Y en `routes/afiliado.py` al inicio de CADA función:

```python
from models import Afiliado, Producto, Comision, Pedido
from app import db
```

## O usa este archivo corregido:

Voy a crear los archivos corregidos completos...
