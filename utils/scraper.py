import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from config import Config

def is_url_allowed(url):
    """
    Verifica si el dominio de la URL pertenece a la Lista Blanca configurada en config.py
    """
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # Revisamos si el dominio exacto o un subdominio está en la lista blanca
        return any(domain == d.lower() or domain.endswith('.' + d.lower()) for d in Config.SCRAPING_WHITELIST)
    except Exception:
        return False

def scrape_webpage(url, selector=None):
    """
    Simula ser un navegador para entrar a una página, descargar el HTML y limpiarlo.
    Si se proporciona un selector, extrae solo esa porción.
    """
    # Paso 2.1: Validación de Seguridad (Protección contra SSRF)
    # Verifica que la URL pertenezca a la Lista Blanca antes de intentar descargarla.
    if not is_url_allowed(url):
        return {"success": False, "error": "URL no permitida por políticas de seguridad (Fuera de la Lista Blanca)."}

    # Paso 2.2: Simulación de Navegador y Descarga
    # Usamos Headers para evitar que las tiendas bloqueen la solicitud creyendo que es un bot malicioso
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    
    try:
        # Descargamos la página (con un timeout de 10 segundos para no congelar el servidor)
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Lanza error si es 404 o 500
        
        # Paso 2.3: Limpieza Quirúrgica y Filtrado con Selectores (BeautifulSoup)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Borramos elementos innecesarios (scripts invisibles, estilos CSS, barras de navegación)
        for tag in soup(['script', 'style', 'noscript', 'header', 'footer', 'nav', 'svg', 'button']):
            tag.decompose()
            
        # Si el usuario quiere buscar algo específico (ej: .price, h1, #description)
        if selector:
            elementos = soup.select(selector)
            if not elementos:
                return {"success": False, "error": f"No se encontraron elementos con el selector '{selector}' en la página."}
            
            # Unimos el texto de todos los elementos encontrados
            texto_limpio = " ".join([el.get_text(separator=' ', strip=True) for el in elementos if el.get_text(strip=True)])
        else:
            # Si no hay selector, extraemos todo el texto legible de la página principal
            texto_limpio = soup.get_text(separator=' ', strip=True)
            
            # Limitamos el tamaño del texto para no exceder los límites de tokens de Qwen
            # 10000 caracteres son aprox 2500-3000 tokens, lo cual es muy seguro
            if len(texto_limpio) > 10000:
                texto_limpio = texto_limpio[:10000] + "\n... [El resto del contenido ha sido truncado por ser muy largo]"
                
        return {"success": True, "data": texto_limpio}
        
    except requests.exceptions.Timeout:
        return {"success": False, "error": "La página tardó demasiado en responder."}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Error de conexión con la página: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": f"Error interno al procesar el HTML: {str(e)}"}
