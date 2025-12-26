document.addEventListener('DOMContentLoaded', () => {
    const chatToggle = document.getElementById("chat-toggle");
    const chatBox = document.getElementById("chat-box");
    const closeChat = document.getElementById("close-chat");
    const sendBtn = document.getElementById("send-btn");
    const input = document.getElementById("user-input");
    const messages = document.getElementById("chat-messages");

    const API_URL = "http://127.0.0.1:8000";
    let isChatOpen = false;

    if (!chatToggle || !chatBox || !closeChat || !sendBtn || !input || !messages) {
        console.warn('❌ Chatbot elements missing in DOM');
        return;
    }

    // ---------------------------
    // Open / Close Chat
    // ---------------------------
    function openChatBox() {
        if (isChatOpen) return;
        chatBox.classList.remove('hidden');
        isChatOpen = true;
        input.focus();
    }

    function closeChatBox() {
        if (!isChatOpen) return;
        chatBox.classList.add('hidden');
        isChatOpen = false;
    }

    chatToggle.addEventListener('click', (e) => {
        e.stopPropagation();
        isChatOpen ? closeChatBox() : openChatBox();
    });

    closeChat.addEventListener('click', closeChatBox);

    document.addEventListener('click', (e) => {
        if (isChatOpen && !chatBox.contains(e.target) && !chatToggle.contains(e.target)) {
            closeChatBox();
        }
    });

    // ---------------------------
    // UI Helpers
    // ---------------------------
    function escapeHtml(unsafe) {
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function addMessage(text, sender) {
        const div = document.createElement('div');
        div.className = `message ${sender}`;

        const time = new Date();
        const hh = String(time.getHours()).padStart(2, '0');
        const mm = String(time.getMinutes()).padStart(2, '0');

        div.innerHTML = `
            <div class="message-text">${escapeHtml(text)}</div>
            <div class="message-time">${hh}:${mm}</div>
        `;

        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function addPhone(phone) {
        const div = document.createElement('div');
        div.className = 'phone-card';

        div.innerHTML = `
            <strong>${escapeHtml(phone.name)}</strong><br>
            السعر: ${escapeHtml(String(phone.price))}$<br>
            نسبة التطابق: ${escapeHtml(String(phone.match_percentage))}%<br>
        `;

        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function showTyping() {
        let t = document.getElementById('typing-indicator');
        if (!t) {
            t = document.createElement('div');
            t.id = 'typing-indicator';
            t.className = 'message bot';
            t.innerHTML = `<div class="message-text">🤖 يكتب...</div>`;
            messages.appendChild(t);
        }
        messages.scrollTop = messages.scrollHeight;
    }

    function hideTyping() {
        const t = document.getElementById('typing-indicator');
        if (t) t.remove();
    }

    // ---------------------------
    // Send Message
    // ---------------------------
    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        addMessage(text, 'user');
        input.value = '';
        input.disabled = true;
        sendBtn.disabled = true;

        showTyping();

        try {
            const res = await fetch(`${API_URL}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            if (!res.ok) throw new Error(`HTTP ${res.status}`);

            const data = await res.json();
            hideTyping();

            // ✅ الرد النصي من Ollama
            if (data.reply) {
                addMessage(data.reply, 'bot');
            }

            // ✅ (اختياري) توصيات مستقبلية
            if (data.recommendations && Array.isArray(data.recommendations)) {
                data.recommendations.forEach(addPhone);
            }

        } catch (err) {
            hideTyping();
            addMessage('❌ حدث خطأ، تأكد أن السيرفر يعمل', 'bot');
            console.error('Chat error:', err);
        } finally {
            input.disabled = false;
            sendBtn.disabled = false;
            input.focus();
        }
    }

    // ---------------------------
    // Events
    // ---------------------------
    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    input.addEventListener('input', () => {
        input.style.height = 'auto';
        input.style.height = input.scrollHeight + 'px';
    });
});
