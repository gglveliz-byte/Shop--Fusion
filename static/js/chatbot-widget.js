(function () {
    // Configuración Base Automática: Se detecta desde donde se carga el script
    const scriptTag = document.currentScript;
    const scriptUrl = new URL(scriptTag.src);
    const BASE_URL = scriptUrl.origin;
    const urlParams = new URLSearchParams(scriptUrl.search);

    // LÓGICA INTELIGENTE DE POSICIONAMIENTO
    let position = urlParams.get('pos') || 'left';

    // Función para detectar si una esquina está ocupada
    const isCornerOccupied = (side) => {
        const x = side === 'left' ? 30 : window.innerWidth - 30;
        const y = window.innerHeight - 30;
        const element = document.elementFromPoint(x, y);
        // Si hay algo que no sea el cuerpo o la raíz, está ocupado
        return element && !['HTML', 'BODY'].includes(element.tagName);
    };

    // Si la posición elegida está ocupada, intentar la otra
    if (isCornerOccupied(position)) {
        position = position === 'left' ? 'right' : 'left';
    }

    // DETECCIÓN DE TEMA (MODO OSCURO/CLARO)
    const isDarkTheme = window.getComputedStyle(document.body).backgroundColor.match(/\d+/g)?.reduce((a, b) => +a + +b) < 380;

    // 1. Cargar CSS del Chatbot
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = BASE_URL + '/static/css/chatbot.css';
    document.head.appendChild(link);

    // Inyectar estilos de posición dinámicos
    const posStyle = document.createElement('style');
    posStyle.innerHTML = `
        #chatbot-bubble { 
            ${position}: 20px !important; 
            box-shadow: 0 4px 15px ${isDarkTheme ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.3)'} !important;
        }
        #chatbot-window { ${position}: 20px !important; }
        @media (max-width: 600px) {
            #chatbot-window { width: 90%; left: 5% !important; right: 5% !important; bottom: 80px; height: 70vh; }
        }
    `;
    document.head.appendChild(posStyle);

    // 2. Inyectar HTML del Chatbot (Con etiquetas de iconos y puros IDs)
    const template = document.createElement('template');
    template.innerHTML = `
        <div id="chatbot-bubble">
            <span class="material-symbols-outlined">forum</span>
        </div>
        <div id="chatbot-window">
            <div class="chatbot-header">
                <h3><span class="material-symbols-outlined">forum</span> Asistente AI Qwen</h3>
                <span class="chatbot-close"><span class="material-symbols-outlined">close</span></span>
            </div>
            <div class="chatbot-model-select">
                <select id="chatbot-model">
                    <option value="qwen-plus">Qwen Plus (Lógica y Ventas)</option>
                    <option value="qwen-vl-max">Qwen VL Max (Visión y OCR)</option>
                </select>
            </div>
            <div id="chatbot-messages" class="chatbot-messages">
                <div class="message ai">¡Hola! Soy un asistente externo. ¿En qué puedo ayudarte?</div>
                <div id="chatbot-typing" class="typing" style="display:none;">Escribiendo...</div>
            </div>
            <div class="chatbot-input">
                <input type="text" id="chatbot-input-field" placeholder="Escribe un mensaje...">
                <button id="chatbot-send"><span class="material-symbols-outlined">send</span></button>
            </div>
        </div>
    `;
    document.body.appendChild(template.content);

    // 3. Lógica del Chatbot
    setTimeout(() => {
        const bubble = document.getElementById('chatbot-bubble');
        const windowChat = document.getElementById('chatbot-window');
        const closeBtn = document.querySelector('.chatbot-close');
        const sendBtn = document.getElementById('chatbot-send');
        const input = document.getElementById('chatbot-input-field');
        const messagesContainer = document.getElementById('chatbot-messages');
        const modelSelect = document.getElementById('chatbot-model');
        const typingIndicator = document.getElementById('chatbot-typing');

        // Memoria del chat (últimos 10 mensajes)
        let chatHistory = [];

        bubble.addEventListener('click', () => {
            windowChat.style.display = windowChat.style.display === 'flex' ? 'none' : 'flex';
            if (windowChat.style.display === 'flex') input.focus();
        });

        closeBtn.addEventListener('click', () => {
            windowChat.style.display = 'none';
        });

        // Botón para borrar historial (Adaptado con icono limpio)
        const setupClearButton = () => {
            const header = document.querySelector('.chatbot-header');
            const closeBtn = document.querySelector('.chatbot-close');

            const actionsDiv = document.createElement('div');
            actionsDiv.style.display = 'flex';
            actionsDiv.style.alignItems = 'center';
            actionsDiv.style.gap = '15px';
            
            const clearBtn = document.createElement('span');
            clearBtn.innerHTML = '<span class="material-symbols-outlined" style="font-size:1.3rem; cursor:pointer; display:flex; align-items:center;">delete</span>';
            clearBtn.title = 'Borrar historial';
            clearBtn.onclick = () => {
                chatHistory = [];
                messagesContainer.innerHTML = '<div class="message ai">Historial borrado. ¿En qué puedo ayudarte?</div>';
                typingIndicator.style.display = 'none';
                messagesContainer.appendChild(typingIndicator);
            };
            header.appendChild(actionsDiv);
            header.appendChild(clearBtn);
            header.appendChild(closeBtn);
        };
        setupClearButton();

        const sendMessage = async () => {
            const text = input.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            input.value = '';
            typingIndicator.style.display = 'block';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            const csrfTokenElement = document.querySelector('meta[name="csrf-token"]') || document.querySelector('input[name="csrf_token"]');
            const csrfToken = csrfTokenElement ? csrfTokenElement.content || csrfTokenElement.value : '';

            try {
                const response = await fetch(BASE_URL + '/ai/stream-chat', {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({
                        message: text,
                        model: modelSelect.value,
                        history: chatHistory
                    })
                });

                typingIndicator.style.display = 'none';

                if (!response.ok) {
                    addMessage("Error: La solicitud fue rechazada por el servidor.", 'ai');
                    return;
                }

                // Crear la burbuja de la IA vacía donde se irá inyectando el texto (Streaming)
                const messageDiv = document.createElement('div');
                messageDiv.classList.add('message', 'ai');
                
                const reasoningDiv = document.createElement('div');
                reasoningDiv.classList.add('reasoning');
                reasoningDiv.style.display = 'none'; // Oculto hasta que haya razonamiento
                
                const contentSpan = document.createElement('span');
                
                messageDiv.appendChild(reasoningDiv);
                messageDiv.appendChild(contentSpan);
                messagesContainer.appendChild(messageDiv);

                const reader = response.body.getReader();
                const decoder = new TextDecoder("utf-8");
                let buffer = "";

                let fullContent = "";
                let fullReasoning = "";

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    
                    // Procesar los fragmentos SSE dividiendo por el doble salto de línea
                    let lines = buffer.split('\n\n');
                    buffer = lines.pop(); // Guardar el fragmento incompleto para la siguiente iteración

                    for (let line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const dataStr = line.substring(6); // Quitar el prefijo 'data: '
                                const data = JSON.parse(dataStr);
                                
                                if (data.type === 'error') {
                                    contentSpan.innerHTML += `<br><span style="color:red">Error: ${data.content}</span>`;
                                } else if (data.type === 'reasoning') {
                                    reasoningDiv.style.display = 'block';
                                    fullReasoning += data.content;
                                    reasoningDiv.innerText = "Pensamiento: " + fullReasoning;
                                } else if (data.type === 'content') {
                                    fullContent += data.content;
                                    contentSpan.innerHTML = fullContent.replace(/\n/g, '<br>');
                                } else if (data.type === 'final') {
                                    // Al finalizar el stream, actualizamos el historial para recordar la conversación
                                    chatHistory.push({ "role": "user", "content": text });
                                    if (fullContent) {
                                        chatHistory.push({ "role": "assistant", "content": fullContent });
                                    } else if (data.result && data.result.tool_calls) {
                                        chatHistory.push({ "role": "assistant", "content": "Acción de herramienta ejecutada." });
                                    }
                                    
                                    if (chatHistory.length > 10) chatHistory = chatHistory.slice(-10);

                                    // Fase 3/4: Renderizar tarjetas de herramientas si las hay en el resultado final
                                    if (data.result && data.result.tool_calls) {
                                        data.result.tool_calls.forEach(tool => {
                                            const actionDiv = document.createElement('div');
                                            actionDiv.classList.add('action-box');
                                            let toolName = tool.function.name;
                                            actionDiv.innerHTML = `
                                                <div style="background: #f3f4f6; border-left: 3px solid #9ca3af; padding: 5px; margin-top: 8px; border-radius: 4px; font-size: 0.8em; color: #333;">
                                                    <strong>🔧 Acción solicitada: ${toolName}</strong><br>
                                                    <small>(Ejecución pendiente - Fase Reactiva)</small>
                                                </div>
                                            `;
                                            messageDiv.appendChild(actionDiv);
                                        });
                                    }
                                }
                                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                            } catch (e) {
                                console.error("Error parseando fragmento SSE:", e, line);
                            }
                        }
                    }
                }
            } catch (error) {
                console.error("Error SSE/Fetch (Equivalente a onerror):", error);
                typingIndicator.style.display = 'none';
                
                // Manejo de reconexión/error equivalente al evento onerror
                const errorMsg = document.createElement('div');
                errorMsg.style.color = '#ef4444';
                errorMsg.style.fontSize = '0.9em';
                errorMsg.style.marginTop = '10px';
                errorMsg.innerHTML = "❌ <strong>Conexión perdida.</strong> Hubo un micro-corte con el servidor. Puedes volver a enviar tu mensaje para reconectar.";
                
                // Si el mensaje se cortó a la mitad, le pegamos la advertencia, si no, creamos un mensaje nuevo.
                if (typeof messageDiv !== 'undefined' && messageDiv && messagesContainer.contains(messageDiv)) {
                    messageDiv.appendChild(errorMsg);
                } else {
                    addMessage("Error de red. No se pudo establecer comunicación con Qwen.", 'ai');
                }
            }
        };

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        function addMessage(text, sender, reasoning = null, tool_calls = null) {
            const div = document.createElement('div');
            div.classList.add('message', sender);

            if (reasoning) {
                const reasoningDiv = document.createElement('div');
                reasoningDiv.classList.add('reasoning');
                reasoningDiv.innerText = "Pensamiento: " + reasoning;
                div.appendChild(reasoningDiv);
            }

            if (text) {
                const textSpan = document.createElement('span');
                textSpan.innerHTML = text.replace(/\n/g, '<br>');
                div.appendChild(textSpan);
            }

            // Soporte para Ficha de Acción de Facturación en el Widget
            if (tool_calls) {
                tool_calls.forEach(tool => {
                    const actionDiv = document.createElement('div');
                    actionDiv.classList.add('action-box');

                    let toolName = tool.function.name;
                    let args = JSON.parse(tool.function.arguments);

                    if (toolName === 'createInvoice') {
                        actionDiv.innerHTML = `
                            <div style="background: #eef2ff; border-left: 3px solid #4f46e5; padding: 8px; margin-top: 8px; border-radius: 4px; font-size: 0.9em; color: #333;">
                                <strong style="color: #4f46e5;">🔧 Factura Disponible</strong><br>
                                <small>Pedido: #${args.pedido_id}</small><br>
                                <button class="confirm-btn" onclick="confirmarFacturaWidget(${args.pedido_id}, this)" 
                                        style="background: #4f46e5; color: white; border: none; padding: 4px 8px; border-radius: 4px; margin-top: 5px; cursor: pointer; width: 100%;">
                                    Emitir Factura
                                </button>
                            </div>
                        `;
                    } else {
                        actionDiv.innerHTML = `
                            <div style="background: #f3f4f6; border-left: 3px solid #9ca3af; padding: 5px; margin-top: 8px; border-radius: 4px; font-size: 0.8em; color: #333;">
                                <strong>🔧 Acción: ${toolName}</strong>
                            </div>
                        `;
                    }
                    div.appendChild(actionDiv);
                });
            }

            messagesContainer.appendChild(div);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        // Función global para el widget
        window.confirmarFacturaWidget = async (pedidoId, btn) => {
            btn.disabled = true;
            btn.innerText = "Emitiendo...";
            try {
                const res = await fetch(`/facturacion/generar/${pedidoId}`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    btn.style.background = "#059669";
                    btn.innerText = "✓ Emitida";
                    addMessage(`Factura generada: <strong>${data.numero}</strong><br><a href="/facturacion/ver_documento/${data.factura_id}" target="_blank" style="color: #4f46e5; text-decoration: underline;">📄 Ver Factura</a>`, 'ai');
                } else {
                    alert("Error: " + data.error);
                    btn.disabled = false;
                    btn.innerText = "Reintentar";
                }
            } catch (e) {
                alert("Error de conexión");
            }
        };

        // Funciones de integración con Carrito e IA
        function ejecutarUpdateCartDesdeIA(product) {
            let currentCart = [];
            try {
                currentCart = JSON.parse(localStorage.getItem('carrito')) || [];
                if (!Array.isArray(currentCart)) currentCart = [];
            } catch(e) {
                currentCart = [];
            }

            const itemExistente = currentCart.find(item => item.id === product.id);
            const qty = parseInt(product.cantidad);
            const actionType = product.action_type || 'add';

            if (actionType === 'remove') {
                if (itemExistente) {
                    currentCart = currentCart.filter(item => item.id !== product.id);
                }
            } else if (actionType === 'set') {
                if (qty <= 0) {
                    currentCart = currentCart.filter(item => item.id !== product.id);
                } else {
                    if (itemExistente) {
                        itemExistente.cantidad = qty;
                    } else {
                        currentCart.push({
                            id: product.id,
                            nombre: product.nombre,
                            precio: parseFloat(product.precio),
                            imagen: product.imagen,
                            cantidad: qty
                        });
                    }
                }
            } else { // 'add' (por defecto)
                const addQty = qty || 1;
                if (itemExistente) {
                    itemExistente.cantidad += addQty;
                } else {
                    currentCart.push({
                        id: product.id,
                        nombre: product.nombre,
                        precio: parseFloat(product.precio),
                        imagen: product.imagen,
                        cantidad: addQty
                    });
                }
            }

            localStorage.setItem('carrito', JSON.stringify(currentCart));

            if (typeof carrito !== 'undefined') {
                carrito = currentCart;
                if (typeof actualizarCarrito === 'function') actualizarCarrito();
                if (typeof sincronizarCarritoConServidor === 'function') sincronizarCarritoConServidor();
            } else {
                const csrfTokenElement = document.querySelector('meta[name="csrf-token"]') || document.querySelector('input[name="csrf_token"]');
                const csrfToken = csrfTokenElement ? csrfTokenElement.content || csrfTokenElement.value : '';
                fetch('/api/actualizar-carrito-session', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken
                    },
                    body: JSON.stringify({ carrito: currentCart })
                }).catch(err => console.error("Error al sincronizar carrito desde IA:", err));
            }

            let toastMsg = "";
            if (actionType === 'remove') {
                toastMsg = `❌ Eliminado: ${product.nombre}`;
            } else if (actionType === 'set') {
                toastMsg = `✏️ Ajustado: ${product.nombre} a ${qty}x`;
            } else {
                toastMsg = `🛒 Agregado: ${qty}x ${product.nombre}`;
            }

            if (typeof mostrarNotificacion === 'function') {
                mostrarNotificacion(toastMsg);
            } else {
                const toast = document.createElement('div');
                toast.style.position = 'fixed';
                toast.style.bottom = '80px';
                toast.style.right = '20px';
                toast.style.background = actionType === 'remove' ? '#dc2626' : 'var(--primary-color, #059669)';
                toast.style.color = 'white';
                toast.style.padding = '12px 24px';
                toast.style.borderRadius = '4px'; /* Consistencia industrial recta */
                toast.style.zIndex = '10000';
                toast.style.boxShadow = '0 10px 25px rgba(0,0,0,0.15)';
                toast.style.fontFamily = 'sans-serif';
                toast.innerHTML = toastMsg;
                document.body.appendChild(toast);
                setTimeout(() => {
                    toast.style.transition = 'opacity 0.5s';
                    toast.style.opacity = '0';
                    setTimeout(() => toast.remove(), 500);
                }, 2500);
            }
        }

        function ejecutarCheckoutDesdeIA() {
            if (typeof mostrarCheckout === 'function') {
                if (typeof actualizarCarrito === 'function') actualizarCarrito();
                const panel = document.getElementById('carrito-panel');
                if (panel && panel.classList.contains('active')) {
                    if (typeof toggleCarrito === 'function') toggleCarrito();
                }
                mostrarCheckout();
            } else {
                window.location.href = '/?checkout=true';
            }
        }
    }, 100);
})();