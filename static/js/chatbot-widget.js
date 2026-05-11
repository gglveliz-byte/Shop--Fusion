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
            border: 2px solid ${isDarkTheme ? 'rgba(255,255,255,0.5)' : 'rgba(0,0,0,0.1)'};
            box-shadow: 0 4px 15px ${isDarkTheme ? 'rgba(255,255,255,0.2)' : 'rgba(0,0,0,0.3)'} !important;
        }
        #chatbot-window { ${position}: 20px !important; }
        @media (max-width: 600px) {
            #chatbot-window { width: 90%; left: 5% !important; right: 5% !important; bottom: 80px; height: 70vh; }
        }
    `;
    document.head.appendChild(posStyle);

    // 2. Inyectar HTML del Chatbot
    const chatbotHtml = `
        <div id="chatbot-bubble">🤖</div>
        <div id="chatbot-window">
            <div class="chatbot-header">
                <h3>Asistente AI Qwen</h3>
                <span class="chatbot-close">&times;</span>
            </div>
            <div class="chatbot-model-select">
                <select id="chatbot-model">
                    <option value="qwen-plus">Qwen Plus (Lógica y Ventas)</option>
                    <option value="qwen-vl-max">Qwen VL Max (Visión y OCR)</option>
                </select>
            </div>
            <div id="chatbot-messages" class="chatbot-messages">
                <div class="message ai">¡Hola! Soy un asistente externo. ¿En qué puedo ayudarte?</div>
                <div id="chatbot-typing" class="typing" style="display:none; font-size:0.8rem; color:#888;">Escribiendo...</div>
            </div>
            <div class="chatbot-input">
                <input type="text" id="chatbot-input-field" placeholder="Escribe un mensaje...">
                <button id="chatbot-send">➤</button>
            </div>
        </div>
    `;

    const div = document.createElement('div');
    div.innerHTML = chatbotHtml;
    document.body.appendChild(div);

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

        // Botón para borrar historial
        const setupClearButton = () => {
            const header = document.querySelector('.chatbot-header');
            const clearBtn = document.createElement('span');
            clearBtn.innerHTML = ' 🗑️ ';
            clearBtn.title = 'Borrar historial';
            clearBtn.style.cursor = 'pointer';
            clearBtn.style.marginLeft = '10px';
            clearBtn.onclick = () => {
                chatHistory = [];
                messagesContainer.innerHTML = '<div class="message ai">Historial borrado. ¿En qué puedo ayudarte?</div>';
                typingIndicator.style.display = 'none';
                messagesContainer.appendChild(typingIndicator);
            };
            header.insertBefore(clearBtn, closeBtn);
        };
        setupClearButton();

        const sendMessage = async () => {
            const text = input.value.trim();
            if (!text) return;

            addMessage(text, 'user');
            input.value = '';
            typingIndicator.style.display = 'block';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            try {
                const response = await fetch(BASE_URL + '/ai/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
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

                    // Limitar a los últimos 10 mensajes
                    if (chatHistory.length > 10) {
                        chatHistory = chatHistory.slice(-10);
                    }
                }
            } catch (error) {
                typingIndicator.style.display = 'none';
                addMessage("Error de conexión con el servidor de IA.", 'ai');
            }
        };

        sendBtn.addEventListener('click', sendMessage);
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') sendMessage();
        });

        function addMessage(text, sender, reasoning = null) {
            const msgDiv = document.createElement('div');
            msgDiv.classList.add('message', sender);
            
            // 1. Mostrar razonamiento si existe (Deep Thinking)
            if (reasoning) {
                const rDiv = document.createElement('div');
                rDiv.classList.add('reasoning');
                rDiv.innerText = "Pensamiento: " + reasoning;
                msgDiv.appendChild(rDiv);
            }

            // 2. Mostrar texto final
            if (text) {
                const tSpan = document.createElement('span');
                // Soporte básico para saltos de línea
                tSpan.innerHTML = text.replace(/\n/g, '<br>');
                msgDiv.appendChild(tSpan);
            }

            messagesContainer.appendChild(msgDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }, 100);
})();
