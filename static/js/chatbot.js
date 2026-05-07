
document.addEventListener('DOMContentLoaded', () => {
    const bubble = document.getElementById('chatbot-bubble');
    const window = document.getElementById('chatbot-window');
    const closeBtn = document.querySelector('.chatbot-close');
    const sendBtn = document.getElementById('chatbot-send');
    const input = document.getElementById('chatbot-input-field');
    const messagesContainer = document.getElementById('chatbot-messages');
    const modelSelect = document.getElementById('chatbot-model');
    const typingIndicator = document.getElementById('chatbot-typing');

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
                    model: modelSelect.value
                })
            });

            const data = await response.json();

            typingIndicator.style.display = 'none';

            if (data.error) {
                addMessage("Error: " + data.error, 'ai');
            } else {
                addMessage(data.response, 'ai', data.reasoning);
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

    function addMessage(text, sender, reasoning = null) {
        const div = document.createElement('div');
        div.classList.add('message', sender);

        if (reasoning) {
            const reasoningDiv = document.createElement('div');
            reasoningDiv.classList.add('reasoning');
            reasoningDiv.innerText = "Pensamiento: " + reasoning;
            div.appendChild(reasoningDiv);
        }

        const textSpan = document.createElement('span');
        textSpan.innerText = text;
        div.appendChild(textSpan);

        messagesContainer.appendChild(div);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
});
