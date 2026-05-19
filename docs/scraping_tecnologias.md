# Justificación Técnica: Elección de Librería para Web Scraping

En el diseño del módulo 7 de la IA (Herramienta de Web Scraping), se evaluaron tres de las tecnologías más populares en el mercado: **Beautiful Soup 4**, **Puppeteer / Selenium**, y **Scrapy**. 

Dado que el ecosistema del proyecto *Shop Fusion* está alojado en infraestructuras de capa gratuita (Free Tier en plataformas como Render), la elección tecnológica debe equilibrar el rendimiento, el consumo de memoria y la facilidad de integración.

A continuación, se detalla el análisis comparativo:

## 1. Puppeteer / Selenium (Scraping Dinámico)
Estas herramientas controlan un navegador web real (Chromium, Firefox) en segundo plano (Headless).
* **Ventajas:** Pueden ejecutar JavaScript, hacer clic en botones, y leer páginas que cargan contenido dinámicamente (como las hechas en React o Angular).
* **Desventajas:** 
  * **Consumo Extremo de RAM:** Iniciar una instancia de navegador consume cientos de megabytes de memoria RAM. Los servidores Free Tier de Render suelen tener un límite estricto de 512 MB. Usar Puppeteer haría que el servidor colapsara (`Out of Memory`).
  * **Lentitud:** Tarda varios segundos en levantar el navegador por cada petición, lo que causaría demoras severas en las respuestas del Chatbot.

## 2. Scrapy (Framework de Scraping Masivo)
Es un framework completo de Python para extraer datos a gran escala.
* **Ventajas:** Extremadamente potente y rápido para "arañar" (crawl) miles de páginas web en paralelo de forma automatizada.
* **Desventajas:**
  * **Exceso de Arquitectura (Overkill):** Es una herramienta demasiado grande y compleja para nuestro caso de uso. Nosotros solo necesitamos que la IA extraiga texto de **una (1) página web específica bajo demanda**, no rastrear sitios completos.

## 3. Requests + Beautiful Soup 4 (Nuestra Elección)
Combina la librería estándar HTTP de Python (`requests`) con un analizador de código HTML súper ligero (`beautifulsoup4`).
* **Ventajas:**
  * **Ultra Ligero:** No requiere ejecutar un navegador. Simplemente descarga el archivo HTML plano y lo lee, consumiendo casi **0% de memoria RAM**. Ideal para servidores Free Tier.
  * **Máxima Velocidad:** Las peticiones toman milisegundos, permitiendo que la IA responda al instante en el chat.
  * **Limpieza Sencilla:** Beautiful Soup permite extraer fácilmente párrafos limpios (`<p>`) e ignorar publicidad, menús o scripts, lo cual es vital para ahorrar tokens y no confundir a la IA de Qwen.
* **Desventajas:** No puede ejecutar JavaScript. Si una página requiere hacer scroll o presionar un botón para ver los datos, BS4 no podrá leerlo. Sin embargo, para el 90% de casos de uso empresariales (documentación técnica, páginas de "Acerca de", o foros de texto estático), es más que suficiente.

---

### Conclusión
La combinación de **Requests + BeautifulSoup** es la decisión arquitectónica más prudente, responsable y segura para el contexto actual del proyecto, garantizando que la funcionalidad de IA opere velozmente sin riesgo de tumbar el servidor por falta de memoria.
