(function () {
    "use strict";

    // =========================================================
    // CONFIGURATION
    // =========================================================

    const API_URL = "http://127.0.0.1:8000/api/widget/chat/";

    // =========================================================
    // GET CURRENT WEBSITE
    // =========================================================

    const websiteUrl = window.location.origin;

    // =========================================================
    // CREATE CHAT BUTTON
    // =========================================================

    const chatButton = document.createElement("button");

    chatButton.innerHTML = "💬";

    chatButton.style.cssText = `
        position: fixed;
        right: 25px;
        bottom: 25px;
        width: 60px;
        height: 60px;
        border: none;
        border-radius: 50%;
        background: #111827;
        color: white;
        font-size: 26px;
        cursor: pointer;
        z-index: 999999;
        box-shadow: 0 8px 30px rgba(0,0,0,0.2);
    `;

    document.body.appendChild(chatButton);

    // =========================================================
    // CREATE CHAT WINDOW
    // =========================================================

    const chatWindow = document.createElement("div");

    chatWindow.style.cssText = `
        position: fixed;
        right: 25px;
        bottom: 95px;
        width: 360px;
        height: 450px;
        background: white;
        border-radius: 18px;
        box-shadow: 0 15px 50px rgba(0,0,0,0.2);
        z-index: 999998;
        display: none;
        overflow: hidden;
        font-family: Arial, sans-serif;
        border: 1px solid #e5e7eb;
    `;

    chatWindow.innerHTML = `
        <div style="
            height: 60px;
            background: #111827;
            color: white;
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 0 18px;
            font-weight: bold;
        ">
            <span>AI Assistant</span>

            <button id="widgetCloseBtn" style="
                background: transparent;
                border: none;
                color: white;
                font-size: 22px;
                cursor: pointer;
            ">
                ×
            </button>
        </div>

        <div id="widgetMessages" style="
            height: 380px;
            overflow-y: auto;
            padding: 15px;
            background: #f9fafb;
        ">
            <div style="
                background: white;
                padding: 10px 12px;
                border-radius: 12px;
                margin-bottom: 10px;
                border: 1px solid #e5e7eb;
            ">
                Hi! 👋 How can I help you?
            </div>
        </div>

        <div style="
            height: 60px;
            display: flex;
            border-top: 1px solid #e5e7eb;
            background: white;
        ">
            <input
                id="widgetInput"
                type="text"
                placeholder="Ask a question..."
                style="
                    flex: 1;
                    border: none;
                    outline: none;
                    padding: 0 14px;
                    font-size: 14px;
                "
            >

            <button id="widgetSendBtn" style="
                width: 70px;
                border: none;
                background: #111827;
                color: white;
                cursor: pointer;
                font-weight: bold;
            ">
                Send
            </button>
        </div>
    `;

    document.body.appendChild(chatWindow);

    // =========================================================
    // ELEMENTS
    // =========================================================

    const closeButton =
        document.getElementById("widgetCloseBtn");

    const messagesContainer =
        document.getElementById("widgetMessages");

    const input =
        document.getElementById("widgetInput");

    const sendButton =
        document.getElementById("widgetSendBtn");

    // =========================================================
    // OPEN / CLOSE
    // =========================================================

    chatButton.addEventListener("click", function () {

        chatWindow.style.display = "block";

        chatButton.style.display = "none";

        input.focus();
    });

    closeButton.addEventListener("click", function () {

        chatWindow.style.display = "none";

        chatButton.style.display = "block";
    });

    // =========================================================
    // ADD MESSAGE
    // =========================================================

    function addMessage(message, sender) {

        const messageElement =
            document.createElement("div");

        messageElement.innerText = message;

        messageElement.style.cssText = `
            padding: 10px 12px;
            border-radius: 12px;
            margin-bottom: 10px;
            max-width: 85%;
            word-wrap: break-word;
            ${
                sender === "user"
                    ? `
                        margin-left: auto;
                        background: #111827;
                        color: white;
                    `
                    : `
                        margin-right: auto;
                        background: white;
                        color: #111827;
                        border: 1px solid #e5e7eb;
                    `
            }
        `;

        messagesContainer.appendChild(messageElement);

        messagesContainer.scrollTop =
            messagesContainer.scrollHeight;
    }

    // =========================================================
    // SEND MESSAGE
    // =========================================================

    async function sendMessage() {

        const message =
            input.value.trim();

        if (!message) {
            return;
        }

        addMessage(message, "user");

        input.value = "";

        sendButton.disabled = true;

        sendButton.innerText = "...";

        addMessage("Thinking...", "assistant");

        try {

            const response = await fetch(API_URL, {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    message: message,

                    website_url: websiteUrl

                })

            });

            const data = await response.json();

            // Remove "Thinking..."
            const thinkingMessage =
                messagesContainer.lastElementChild;

            if (
                thinkingMessage &&
                thinkingMessage.innerText === "Thinking..."
            ) {
                thinkingMessage.remove();
            }

            if (!response.ok) {

                addMessage(
                    data.error ||
                    "Sorry, something went wrong.",
                    "assistant"
                );

                return;
            }

            addMessage(
                data.response ||
                "I couldn't generate a response.",
                "assistant"
            );

        } catch (error) {

            console.error(
                "Widget error:",
                error
            );

            const thinkingMessage =
                messagesContainer.lastElementChild;

            if (
                thinkingMessage &&
                thinkingMessage.innerText === "Thinking..."
            ) {
                thinkingMessage.remove();
            }

            addMessage(
                "Unable to connect to the AI assistant.",
                "assistant"
            );

        } finally {

            sendButton.disabled = false;

            sendButton.innerText = "Send";

            input.focus();
        }
    }

    // =========================================================
    // SEND BUTTON
    // =========================================================

    sendButton.addEventListener(
        "click",
        sendMessage
    );

    // =========================================================
    // ENTER KEY
    // =========================================================

    input.addEventListener(
        "keydown",
        function (event) {

            if (event.key === "Enter") {

                event.preventDefault();

                sendMessage();
            }

        }
    );

})();