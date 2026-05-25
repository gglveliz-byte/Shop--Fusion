
document.addEventListener('DOMContentLoaded', () => {
    const bubble = document.getElementById('chatbot-bubble');
    const window = document.getElementById('chatbot-window');
    const closeBtn = document.querySelector('.chatbot-close');
    const sendBtn = document.getElementById('chatbot-send');
    const input = document.getElementById('chatbot-input-field');
    const messagesContainer = document.getElementById('chatbot-messages');
    const modelSelect = document.getElementById('chatbot-model');
    const typingIndicator = document.getElementById('chatbot-typing');

    // Memoria del chat (últimos 10 mensajes)
    let chatHistory = [];

    // Toggle window (Solo si existe la burbuja)
    if (bubble) {
        bubble.addEventListener('click', () => {
            window.style.display = window.style.display === 'flex' ? 'none' : 'flex';
            if (window.style.display === 'flex') {
                input.focus();
            }
        });
    }

    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            window.style.display = 'none';
        });
    }

    // Botón para borrar historial (Inyectado dinámicamente o buscado en el DOM)
    const setupClearButton = () => {
        const header = document.querySelector('.chatbot-header');
        if (!header) return;

        const clearBtn = document.createElement('span');
        clearBtn.innerHTML = ' 🗑️ ';
        clearBtn.title = 'Borrar historial';
        clearBtn.style.cursor = 'pointer';
        clearBtn.style.marginLeft = '10px';
        clearBtn.onclick = () => {
            chatHistory = [];
            messagesContainer.innerHTML = '<div class="message ai">Historial borrado. ¿En qué puedo ayudarte ahora?</div>';
            typingIndicator.style.display = 'none';
            messagesContainer.appendChild(typingIndicator);
        };
        header.insertBefore(clearBtn, closeBtn);
    };
    setupClearButton();

    // Send message
    const sendMessage = async (hiddenText = null) => {
        const text = hiddenText !== null ? hiddenText : input.value.trim();
        if (!text) return;

        // Add user message to UI
        if (!text.startsWith('[SISTEMA_CONFIRMA]')) {
            addMessage(text, 'user');
        } else {
            addMessage("✔️ Acción aprobada por el usuario.", 'user');
        }
        
        if (hiddenText === null) {
            input.value = '';
        }

        // Show typing
        typingIndicator.style.display = 'block';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').content;

            const response = await fetch('/ai/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({
                    message: text,
                    model: modelSelect.value,
                    history: chatHistory // Enviar historial
                })
            });

            const data = await response.json();

            typingIndicator.style.display = 'none';

            if (data.error) {
                addMessage("Error: " + data.error, 'ai');
            } else if (data.status === "requires_confirmation") {
                // Generar UI de confirmación dinámica y premium
                let confMsg = `
                    <div style="background: rgba(255, 255, 255, 0.05); border-left: 4px solid #f59e0b; padding: 12px; border-radius: 8px; margin-top: 8px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);">
                        <div style="font-weight: 600; color: #f59e0b; margin-bottom: 6px; display: flex; align-items: center; gap: 6px;">
                            <svg width="16" height="16" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
                            Autorización Requerida
                        </div>
                        <div style="font-size: 0.9em; margin-bottom: 12px; color: #4b5563;">
                            El sistema intentó ejecutar una operación crítica: <strong style="color: #111827; background: #f3f4f6; padding: 2px 6px; border-radius: 4px;">${data.pending_action.func_name}</strong>. Por tu seguridad, necesitamos tu confirmación.
                        </div>
                        <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                            <button id="btn-approve-action" style="flex: 1; background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; border: none; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 0.9em; transition: all 0.2s ease; box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);">
                                ✓ Aprobar
                            </button>
                            <button id="btn-reject-action" style="flex: 1; background: #fff; color: #ef4444; border: 1px solid #ef4444; padding: 8px 14px; border-radius: 6px; cursor: pointer; font-weight: 500; font-size: 0.9em; transition: all 0.2s ease;">
                                ✕ Rechazar
                            </button>
                        </div>
                    </div>
                `;
                addMessage(confMsg, 'ai');
                
                setTimeout(() => {
                    const btnApprove = document.getElementById('btn-approve-action');
                    const btnReject = document.getElementById('btn-reject-action');

                    if (btnApprove) {
                        btnApprove.onclick = function() {
                            // Deshabilitar ambos botones para evitar doble clic
                            btnApprove.disabled = true;
                            btnApprove.innerHTML = '&#9203; Procesando...';
                            btnApprove.style.opacity = '0.7';
                            if (btnReject) btnReject.disabled = true;

                            // Preservar el contexto de lo que el asistente intentó hacer
                            chatHistory.push({
                                "role": "assistant",
                                "content": data.response || ""
                            });

                            // Enviar token como hiddenText (no se pinta en el chat)
                            let confirmPayload = `[SISTEMA_CONFIRMA] ${data.pending_action.token}`;
                            sendMessage(confirmPayload);
                        };
                        btnApprove.onmouseover = () => btnApprove.style.transform = 'translateY(-1px)';
                        btnApprove.onmouseout = () => btnApprove.style.transform = 'translateY(0)';
                    }

                    if (btnReject) {
                        btnReject.onclick = function() {
                            btnReject.disabled = true;
                            if (btnApprove) btnApprove.disabled = true;
                            sendMessage('He rechazado la acción. Cancela la operación y dime en qué más puedo ayudarte.');
                        };
                        btnReject.onmouseover = () => { btnReject.style.background = '#fef2f2'; btnReject.style.transform = 'translateY(-1px)'; };
                        btnReject.onmouseout = () => { btnReject.style.background = '#fff'; btnReject.style.transform = 'translateY(0)'; };
                    }
                }, 100);
            } else {
                addMessage(data.response, 'ai', data.reasoning, data.tool_calls);
                
                // Interceptar acciones de carrito ejecutadas por la IA
                if (data.status === "tool_executed") {
                    const results = data.db_results || (data.db_result ? [data.db_result] : []);
                    results.forEach(res => {
                        if (res.success) {
                            const action = res.action;
                            if (action === "addProductToCart" || action === "updateCartItem") {
                                ejecutarUpdateCartDesdeIA(res);
                            } else if (action === "checkoutCart") {
                                ejecutarCheckoutDesdeIA();
                            }
                        }
                    });
                }

                // Guardar en el historial
                chatHistory.push({"role": "user", "content": text});
                if (data.response) {
                    chatHistory.push({"role": "assistant", "content": data.response});
                } else if (data.tool_calls) {
                    chatHistory.push({"role": "assistant", "content": "Acción de herramienta detectada."});
                }

                // Limitar a los últimos 10 mensajes (5 pares de pregunta/respuesta)
                if (chatHistory.length > 10) {
                    chatHistory = chatHistory.slice(-10);
                }
            }
        } catch (error) {
            typingIndicator.style.display = 'none';
            addMessage("Error de conexión con el servidor.", 'ai');
            console.error(error);
        }
    };

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') sendMessage();
    });

    function addMessage(text, sender, reasoning = null, tool_calls = null) {
        const div = document.createElement('div');
        div.classList.add('message', sender);

        // 1. Mostrar razonamiento si existe (Deep Thinking)
        if (reasoning) {
            const reasoningDiv = document.createElement('div');
            reasoningDiv.classList.add('reasoning');
            reasoningDiv.innerText = "Pensamiento: " + reasoning;
            div.appendChild(reasoningDiv);
        }

        // 2. Mostrar texto final
        if (text) {
            const textSpan = document.createElement('span');
            textSpan.innerHTML = text.replace(/\n/g, '<br>');
            div.appendChild(textSpan);
        }

        // 3. [NUEVO] Mostrar Caja de Herramientas (Action Card)
        if (tool_calls) {
            tool_calls.forEach(tool => {
                const actionDiv = document.createElement('div');
                actionDiv.classList.add('action-box');
                
                let toolName = tool.function.name;
                let args = JSON.parse(tool.function.arguments);

                if (toolName === 'createInvoice') {
                    actionDiv.innerHTML = `
                        <div style="background: #eef2ff; border-left: 4px solid #4f46e5; padding: 10px; margin-top: 10px; border-radius: 4px;">
                            <strong style="color: #4f46e5;">🔧 Borrador de Factura</strong><br>
                            <small>Pedido: #${args.pedido_id}</small><br>
                            <button class="confirm-btn" onclick="confirmarFactura(${args.pedido_id}, this)" 
                                    style="background: #4f46e5; color: white; border: none; padding: 5px 10px; border-radius: 4px; margin-top: 5px; cursor: pointer;">
                                Confirmar y Emitir
                            </button>
                        </div>
                    `;
                } else {
                    actionDiv.innerHTML = `
                        <div style="background: #f3f4f6; border-left: 4px solid #9ca3af; padding: 8px; margin-top: 10px; border-radius: 4px; font-size: 0.85em;">
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

    // Función global para manejar la confirmación desde el botón de la UI
    window.confirmarFactura = async (pedidoId, btn) => {
        btn.disabled = true;
        btn.innerText = "Emitiendo...";
        try {
            const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
            const res = await fetch(`/facturacion/generar/${pedidoId}`, { 
                method: 'POST',
                headers: { 'X-CSRFToken': csrfToken }
            });
            const data = await res.json();
            if (data.success) {
                btn.style.background = "#059669";
                btn.innerText = "✓ Factura Emitida";
                addMessage(`Factura generada: <strong>${data.numero}</strong><br><a href="/facturacion/ver_documento/${data.factura_id}" target="_blank" style="color: #4f46e5; text-decoration: underline;">📄 Ver Documento de Factura</a>`, 'ai');
            } else {
                alert("Error: " + data.error);
                btn.disabled = false;
                btn.innerText = "Reintentar";
            }
        } catch (e) {
            console.error(e);
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
            toast.style.background = actionType === 'remove' ? '#dc2626' : '#059669';
            toast.style.color = 'white';
            toast.style.padding = '12px 24px';
            toast.style.borderRadius = '8px';
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
});
