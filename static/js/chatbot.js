
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
    const sendMessage = async () => {
        const text = input.value.trim();
        if (!text) return;

        // Add user message to UI
        addMessage(text, 'user');
        input.value = '';

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
            } else {
                addMessage(data.response, 'ai', data.reasoning, data.tool_calls);
                
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
});
