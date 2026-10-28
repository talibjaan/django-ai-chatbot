document.addEventListener("DOMContentLoaded", () => {

    // =========================================================
    // ELEMENTS
    // =========================================================

    const chatOpenBtn =
        document.getElementById("chatOpenBtn");

    const heroChatBtn =
        document.getElementById("heroChatBtn");

    const chatWindow =
        document.getElementById("chatWindow");

    const closeChatBtn =
        document.getElementById("closeChatBtn");

    const clearChatBtn =
        document.getElementById("clearChatBtn");

    const refreshChatBtn =
        document.getElementById("refreshChatBtn");

    const chatMessages =
        document.getElementById("chatMessages");

    const welcomeMessage =
        document.getElementById("welcomeMessage");

    const messageInput =
        document.getElementById("messageInput");

    const sendBtn =
        document.getElementById("sendBtn");

    const typingIndicator =
        document.getElementById("typingIndicator");

    const quickQuestions =
        document.querySelectorAll(".quick-question");


    // =========================================================
    // SIDEBAR ELEMENTS
    // =========================================================

    const historyBtn =
        document.getElementById("historyBtn");

    const chatSidebar =
        document.getElementById("chatSidebar");

    const closeSidebarBtn =
        document.getElementById("closeSidebarBtn");

    const newChatBtn =
        document.getElementById("newChatBtn");

    const chatHistory =
        document.getElementById("chatHistory");


    // =========================================================
    // REQUIRED ELEMENT CHECK
    // =========================================================

    if (!chatWindow) {
        console.error("chatWindow not found.");
        return;
    }

    if (!messageInput) {
        console.error("messageInput not found.");
        return;
    }

    if (!sendBtn) {
        console.error("sendBtn not found.");
        return;
    }

    if (!chatMessages) {
        console.error("chatMessages not found.");
        return;
    }


    // =========================================================
    // CHAT MEMORY
    // =========================================================

    let messages = [];

    try {

        messages = JSON.parse(
            localStorage.getItem("aiMessages") || "[]"
        );

        if (!Array.isArray(messages)) {
            messages = [];
        }

    } catch (error) {

        console.error(
            "Could not load saved messages:",
            error
        );

        messages = [];
    }


    // =========================================================
    // DATABASE CONVERSATION HISTORY
    // =========================================================

    let conversations = [];


    // =========================================================
    // CURRENT DATABASE CONVERSATION
    // =========================================================

    let currentConversationId =
        localStorage.getItem("currentConversationId") || null;


    // =========================================================
    // STATE
    // =========================================================

    let isSending = false;
    let isTyping = false;


    // =========================================================
    // SAVE MESSAGES
    // =========================================================

    function saveMessages() {

        try {

            localStorage.setItem(
                "aiMessages",
                JSON.stringify(messages)
            );

        } catch (error) {

            console.error(
                "Could not save messages:",
                error
            );

        }

    }


    // =========================================================
    // SAVE CURRENT CONVERSATION ID
    // =========================================================

    function saveCurrentConversationId() {

        if (currentConversationId) {

            localStorage.setItem(
                "currentConversationId",
                currentConversationId
            );

        } else {

            localStorage.removeItem(
                "currentConversationId"
            );

        }

    }


    // =========================================================
    // GET CSRF TOKEN
    // =========================================================

    function getCSRFToken() {

        const csrfInput =
            document.querySelector(
                "[name=csrfmiddlewaretoken]"
            );

        if (
            csrfInput &&
            csrfInput.value
        ) {

            return csrfInput.value;

        }

        return getCookie("csrftoken");

    }


    // =========================================================
    // GET COOKIE
    // =========================================================

    function getCookie(name) {

        const cookies =
            document.cookie.split(";");

        for (let cookie of cookies) {

            cookie = cookie.trim();

            if (
                cookie.startsWith(
                    name + "="
                )
            ) {

                return decodeURIComponent(
                    cookie.substring(
                        name.length + 1
                    )
                );

            }

        }

        return "";

    }


    // =========================================================
    // OPEN CHAT
    // =========================================================

    function openChat() {

        chatWindow.classList.add("open");

        chatWindow.setAttribute(
            "aria-hidden",
            "false"
        );

        if (chatOpenBtn) {

            chatOpenBtn.classList.add(
                "hidden"
            );

        }

        setTimeout(() => {

            messageInput.focus();

            scrollToBottom();

        }, 250);

    }


    // =========================================================
    // CLOSE CHAT
    // =========================================================

    function closeChat() {

        chatWindow.classList.remove("open");

        chatWindow.setAttribute(
            "aria-hidden",
            "true"
        );

        closeSidebar();

        if (chatOpenBtn) {

            chatOpenBtn.classList.remove(
                "hidden"
            );

        }

    }


    // =========================================================
    // OPEN CHAT BUTTON
    // =========================================================

    if (chatOpenBtn) {

        chatOpenBtn.addEventListener(
            "click",
            openChat
        );

    }


    // =========================================================
    // HERO CHAT BUTTON
    // =========================================================

    if (heroChatBtn) {

        heroChatBtn.addEventListener(
            "click",
            openChat
        );

    }


    // =========================================================
    // CLOSE CHAT BUTTON
    // =========================================================

    if (closeChatBtn) {

        closeChatBtn.addEventListener(
            "click",
            closeChat
        );

    }


    // =========================================================
    // SIDEBAR
    // =========================================================

    function openSidebar() {

        if (!chatSidebar) {
            return;
        }

        chatSidebar.classList.add("open");

    }


    function closeSidebar() {

        if (!chatSidebar) {
            return;
        }

        chatSidebar.classList.remove("open");

    }


    // =========================================================
    // HISTORY BUTTON
    // =========================================================

    if (historyBtn) {

        historyBtn.addEventListener(
            "click",
            async () => {

                await loadConversationsFromDatabase();

                openSidebar();

            }
        );

    }


    // =========================================================
    // CLOSE SIDEBAR
    // =========================================================

    if (closeSidebarBtn) {

        closeSidebarBtn.addEventListener(
            "click",
            closeSidebar
        );

    }


    // =========================================================
    // LOAD USER CONVERSATIONS FROM DATABASE
    // =========================================================

    async function loadConversationsFromDatabase() {

        try {

            const response =
                await fetch(
                    "/conversations/",
                    {
                        method: "GET",
                        credentials: "same-origin"
                    }
                );

            if (!response.ok) {

                throw new Error(
                    `Failed to load conversations: ${response.status}`
                );

            }

            const data =
                await response.json();

            conversations =
                Array.isArray(
                    data.conversations
                )
                    ? data.conversations
                    : [];

            renderChatHistory();

            console.log(
                "Database conversations loaded:",
                conversations
            );

        } catch (error) {

            console.error(
                "Could not load conversations:",
                error
            );

        }

    }


    // =========================================================
    // LOAD SINGLE CONVERSATION FROM DATABASE
    // =========================================================

    async function loadConversationFromDatabase(id) {

        try {

            const response =
                await fetch(
                    `/conversations/${id}/`,
                    {
                        method: "GET",
                        credentials: "same-origin"
                    }
                );

            if (!response.ok) {

                if (response.status === 404) {

                    console.error(
                        "Conversation not found."
                    );

                }

                throw new Error(
                    `Failed to load conversation: ${response.status}`
                );

            }

            const data =
                await response.json();

            if (!data.conversation) {

                throw new Error(
                    "Conversation data not received."
                );

            }


            // -------------------------------------------------
            // SET DATABASE CONVERSATION ID
            // -------------------------------------------------

            currentConversationId =
                data.conversation.id;

            saveCurrentConversationId();


            // -------------------------------------------------
            // UPDATE CONVERSATION IN MEMORY
            // -------------------------------------------------

            const existingIndex =
                conversations.findIndex(
                    conversation =>
                        Number(conversation.id) ===
                        Number(data.conversation.id)
                );


            if (existingIndex !== -1) {

                conversations[existingIndex] = {

                    ...conversations[existingIndex],

                    title:
                        data.conversation.title,

                    updated_at:
                        data.conversation.updated_at

                };

            } else {

                conversations.push({

                    id:
                        data.conversation.id,

                    title:
                        data.conversation.title,

                    created_at:
                        data.conversation.created_at,

                    updated_at:
                        data.conversation.updated_at

                });

            }


            // -------------------------------------------------
            // LOAD MESSAGES
            // -------------------------------------------------

            messages =
                Array.isArray(data.messages)
                    ? data.messages.map(
                        message => ({
                            role: message.role,
                            content: message.content
                        })
                    )
                    : [];


            saveMessages();


            // -------------------------------------------------
            // DISPLAY
            // -------------------------------------------------

            displayLoadedConversation();


            // -------------------------------------------------
            // UPDATE SIDEBAR
            // -------------------------------------------------

            renderChatHistory();


            // -------------------------------------------------
            // CLOSE SIDEBAR
            // -------------------------------------------------

            closeSidebar();


            // -------------------------------------------------
            // SCROLL
            // -------------------------------------------------

            scrollToBottom();


        } catch (error) {

            console.error(
                "Could not load conversation:",
                error
            );

        }

    }


    // =========================================================
    // DISPLAY LOADED DATABASE CONVERSATION
    // =========================================================

    function displayLoadedConversation() {

        chatMessages
            .querySelectorAll(".message")
            .forEach((message) => {

                message.remove();

            });


        hideTyping();


        if (!messages.length) {

            if (welcomeMessage) {

                welcomeMessage.style.display =
                    "flex";

            }

            return;

        }


        if (welcomeMessage) {

            welcomeMessage.style.display =
                "none";

        }


        messages.forEach(
            (message) => {

                addMessage(
                    message.role,
                    message.content
                );

            }
        );


        scrollToBottom();

    }


    // =========================================================
    // RENDER DATABASE CHAT HISTORY
    // =========================================================

    function renderChatHistory() {

        if (!chatHistory) {
            return;
        }


        chatHistory.innerHTML = "";


        if (conversations.length === 0) {

            const empty =
                document.createElement("div");


            empty.className =
                "history-empty";


            empty.innerHTML = `
                <div class="history-empty-icon">✦</div>
                <p>No conversations yet</p>
                <span>Start chatting to create your first conversation.</span>
            `;


            chatHistory.appendChild(
                empty
            );


            return;

        }


        // -----------------------------------------------------
        // SORT NEWEST FIRST
        // -----------------------------------------------------

        const sortedConversations =
            [...conversations].sort(
                (a, b) => {

                    const dateA =
                        new Date(
                            a.updated_at ||
                            a.updatedAt ||
                            0
                        ).getTime();

                    const dateB =
                        new Date(
                            b.updated_at ||
                            b.updatedAt ||
                            0
                        ).getTime();

                    return dateB - dateA;

                }
            );


        // -----------------------------------------------------
        // CREATE ITEMS
        // -----------------------------------------------------

        sortedConversations.forEach(
            (conversation) => {

                const item =
                    document.createElement("div");


                item.className =
                    "history-item";


                // -------------------------------------------------
                // ACTIVE CONVERSATION
                // -------------------------------------------------

                if (
                    Number(conversation.id) ===
                    Number(currentConversationId)
                ) {

                    item.classList.add(
                        "active"
                    );

                }


                // -------------------------------------------------
                // CLICK CONVERSATION
                // -------------------------------------------------

                item.addEventListener(
                    "click",
                    () => {

                        loadConversationFromDatabase(
                            conversation.id
                        );

                    }
                );


                // -------------------------------------------------
                // ICON
                // -------------------------------------------------

                const icon =
                    document.createElement("div");


                icon.className =
                    "history-item-icon";


                icon.textContent =
                    "✦";


                // -------------------------------------------------
                // CONTENT
                // -------------------------------------------------

                const content =
                    document.createElement("div");


                content.className =
                    "history-item-content";


                // -------------------------------------------------
                // TITLE
                // -------------------------------------------------

                const title =
                    document.createElement("div");


                title.className =
                    "history-item-title";


                title.textContent =
                    conversation.title ||
                    "New Conversation";


                // -------------------------------------------------
                // DATE
                // -------------------------------------------------

                const date =
                    document.createElement("div");


                date.className =
                    "history-item-date";


                date.textContent =
                    formatDatabaseDate(
                        conversation.updated_at
                    );


                content.appendChild(
                    title
                );


                content.appendChild(
                    date
                );


                // -------------------------------------------------
                // DELETE BUTTON
                // -------------------------------------------------

                const deleteBtn =
                    document.createElement("button");


                deleteBtn.className =
                    "delete-conversation-btn";


                deleteBtn.type =
                    "button";


                deleteBtn.textContent =
                    "🗑️";


                deleteBtn.title =
                    "Delete conversation";


                // -------------------------------------------------
                // DELETE CLICK
                // -------------------------------------------------

                deleteBtn.addEventListener(
                    "click",
                    async (event) => {

                        // Prevent conversation from opening
                        event.stopPropagation();

                        await deleteConversation(
                            conversation.id
                        );

                    }
                );


                // -------------------------------------------------
                // APPEND
                // -------------------------------------------------

                item.appendChild(
                    icon
                );


                item.appendChild(
                    content
                );


                item.appendChild(
                    deleteBtn
                );


                chatHistory.appendChild(
                    item
                );

            }
        );

    }


    // =========================================================
    // DELETE DATABASE CONVERSATION
    // =========================================================

    async function deleteConversation(
        conversationId
    ) {

        if (!conversationId) {
            return;
        }


        const confirmed =
            confirm(
                "Are you sure you want to delete this conversation?"
            );


        if (!confirmed) {
            return;
        }


        try {

            const csrfToken =
                getCSRFToken();


            if (!csrfToken) {

                throw new Error(
                    "CSRF token not found."
                );

            }


            const response =
                await fetch(
                    `/conversations/${conversationId}/delete/`,
                    {
                        method: "DELETE",

                        headers: {
                            "X-CSRFToken":
                                csrfToken
                        },

                        credentials:
                            "same-origin"
                    }
                );


            const data =
                await response.json();


            if (!response.ok) {

                throw new Error(
                    data.error ||
                    "Could not delete conversation."
                );

            }


            // -------------------------------------------------
            // REMOVE FROM LOCAL CONVERSATION LIST
            // -------------------------------------------------

            conversations =
                conversations.filter(
                    conversation =>
                        Number(conversation.id) !==
                        Number(conversationId)
                );


            // -------------------------------------------------
            // IF CURRENT CONVERSATION WAS DELETED
            // -------------------------------------------------

            if (
                Number(currentConversationId) ===
                Number(conversationId)
            ) {

                startNewChat();

            }


            // -------------------------------------------------
            // UPDATE SIDEBAR
            // -------------------------------------------------

            renderChatHistory();


            console.log(
                "Conversation deleted successfully."
            );


        } catch (error) {

            console.error(
                "DELETE CONVERSATION ERROR:",
                error
            );


            alert(
                error.message ||
                "Could not delete conversation."
            );

        }

    }


    // =========================================================
    // FORMAT DATABASE DATE
    // =========================================================

    function formatDatabaseDate(dateString) {

        if (!dateString) {
            return "";
        }


        const date =
            new Date(
                dateString
            );


        if (isNaN(date.getTime())) {
            return "";
        }


        const now =
            new Date();


        const difference =
            now - date;


        const oneMinute =
            60 * 1000;


        const oneHour =
            60 * oneMinute;


        const oneDay =
            24 * oneHour;


        if (difference < oneMinute) {

            return "Just now";

        }


        if (difference < oneHour) {

            const minutes =
                Math.floor(
                    difference /
                    oneMinute
                );


            return (
                minutes +
                (
                    minutes === 1
                        ? " minute ago"
                        : " minutes ago"
                )
            );

        }


        if (difference < oneDay) {

            const hours =
                Math.floor(
                    difference /
                    oneHour
                );


            return (
                hours +
                (
                    hours === 1
                        ? " hour ago"
                        : " hours ago"
                )
            );

        }


        return date.toLocaleDateString(
            undefined,
            {
                month: "short",
                day: "numeric"
            }
        );

    }


    // =========================================================
    // NEW CHAT
    // =========================================================

    function startNewChat() {

        currentConversationId =
            null;


        saveCurrentConversationId();


        messages = [];


        saveMessages();


        chatMessages
            .querySelectorAll(".message")
            .forEach((message) => {

                message.remove();

            });


        if (welcomeMessage) {

            welcomeMessage.style.display =
                "flex";

        }


        messageInput.value = "";


        messageInput.style.height =
            "auto";


        hideTyping();


        closeSidebar();


        setTimeout(() => {

            messageInput.focus();

        }, 150);


        renderChatHistory();

    }


    // =========================================================
    // NEW CHAT BUTTON
    // =========================================================

    if (newChatBtn) {

        newChatBtn.addEventListener(
            "click",
            startNewChat
        );

    }


    // =========================================================
    // SEND MESSAGE
    // =========================================================

    async function sendMessage(
        customMessage = null
    ) {

        // -----------------------------------------------------
        // PREVENT MULTIPLE REQUESTS
        // -----------------------------------------------------

        if (isSending) {
            return;
        }


        // -----------------------------------------------------
        // GET USER MESSAGE
        // -----------------------------------------------------

        const userMessage =
            customMessage ||
            messageInput.value.trim();


        // -----------------------------------------------------
        // EMPTY MESSAGE
        // -----------------------------------------------------

        if (!userMessage) {
            return;
        }


        // =====================================================
        // WEBSITE URL DETECTION
        // =====================================================

        const websiteUrlPattern =
            /(https?:\/\/[^\s]+|www\.[^\s]+)/i;


        const isWebsiteRequest =
            websiteUrlPattern.test(
                userMessage
            );


        // -----------------------------------------------------
        // HIDE WELCOME
        // -----------------------------------------------------

        if (welcomeMessage) {

            welcomeMessage.style.display =
                "none";

        }


        // -----------------------------------------------------
        // CLEAR INPUT
        // -----------------------------------------------------

        messageInput.value = "";


        messageInput.style.height =
            "auto";


        // -----------------------------------------------------
        // ADD USER MESSAGE TO SCREEN
        // -----------------------------------------------------

        addMessage(
            "user",
            userMessage
        );


        // -----------------------------------------------------
        // ADD USER MESSAGE TO MEMORY
        // -----------------------------------------------------

        messages.push({

            role: "user",

            content: userMessage

        });


        saveMessages();


        // =====================================================
        // WEBSITE ANALYZING / NORMAL TYPING
        // =====================================================

        if (isWebsiteRequest) {

            showWebsiteAnalyzing();

        } else {

            showTyping();

        }


        isSending = true;

        sendBtn.disabled = true;


        try {

            // -------------------------------------------------
            // CSRF
            // -------------------------------------------------

            const csrfToken =
                getCSRFToken();


            if (!csrfToken) {

                throw new Error(
                    "CSRF token not found."
                );

            }


            // -------------------------------------------------
            // SEND TO DJANGO
            // -------------------------------------------------

            const response =
                await fetch(
                    "/chat/",
                    {

                        method: "POST",

                        headers: {

                            "Content-Type":
                                "application/json",

                            "X-CSRFToken":
                                csrfToken

                        },

                        credentials:
                            "same-origin",

                        body:
                            JSON.stringify({

                                messages:
                                    messages,

                                conversation_id:
                                    currentConversationId

                            })

                    }
                );


            // -------------------------------------------------
            // RESPONSE ERROR
            // -------------------------------------------------

            if (!response.ok) {

                let errorMessage =
                    `Server error: ${response.status}`;


                try {

                    const errorData =
                        await response.json();


                    console.error(
                        "Server error:",
                        errorData
                    );


                    if (
                        errorData.error
                    ) {

                        errorMessage =
                            errorData.error;

                    }


                    if (
                        errorData.details
                    ) {

                        console.error(
                            "Details:",
                            errorData.details
                        );

                    }

                } catch (error) {

                    console.error(
                        "Could not read error:",
                        error
                    );

                }


                throw new Error(
                    errorMessage
                );

            }


            // -------------------------------------------------
            // JSON
            // -------------------------------------------------

            const data =
                await response.json();


            console.log(
                "AI response:",
                data
            );


            // -------------------------------------------------
            // GET REAL DATABASE CONVERSATION ID
            // -------------------------------------------------

            if (
                data.conversation_id
            ) {

                currentConversationId =
                    data.conversation_id;


                saveCurrentConversationId();

            }


            // -------------------------------------------------
            // GET AI RESPONSE
            // -------------------------------------------------

            const aiResponse =
                data.response ||
                data.reply ||
                data.message;


            if (!aiResponse) {

                throw new Error(
                    "No AI response received."
                );

            }


            // -------------------------------------------------
            // HIDE TYPING / WEBSITE STATUS
            // -------------------------------------------------

            hideTyping();

            hideWebsiteAnalyzing();


            // -------------------------------------------------
            // AI TYPING
            // -------------------------------------------------

            await typeAssistantMessage(
                aiResponse
            );


            // -------------------------------------------------
            // SAVE AI MESSAGE LOCALLY
            // -------------------------------------------------

            messages.push({

                role: "assistant",

                content: aiResponse

            });


            saveMessages();


            // -------------------------------------------------
            // REFRESH DATABASE HISTORY
            // -------------------------------------------------

            await loadConversationsFromDatabase();


        } catch (error) {

            console.error(
                "CHAT ERROR:",
                error
            );


            hideTyping();

            hideWebsiteAnalyzing();


            addMessage(
                "assistant",
                error.message ||
                "Sorry, I couldn't process your message right now. 😕"
            );


        } finally {

            isSending = false;

            sendBtn.disabled = false;

            messageInput.focus();

        }

    }


    // =========================================================
    // WEBSITE ANALYZING INDICATOR
    // =========================================================

    function showWebsiteAnalyzing() {

        if (!typingIndicator) {
            return;
        }


        typingIndicator.style.display =
            "flex";


        const textElement =
            typingIndicator.querySelector(
                ".typing-text"
            );


        if (textElement) {

            textElement.textContent =
                "Analyzing website...";

        }


        scrollToBottom();

    }


    // =========================================================
    // HIDE WEBSITE ANALYZING
    // =========================================================

    function hideWebsiteAnalyzing() {

        if (!typingIndicator) {
            return;
        }


        typingIndicator.style.display =
            "none";


        const textElement =
            typingIndicator.querySelector(
                ".typing-text"
            );


        if (textElement) {

            textElement.textContent =
                "AI is typing...";

        }

    }


    // =========================================================
    // ADD MESSAGE
    // =========================================================

    function addMessage(
        role,
        text
    ) {

        if (!chatMessages) {
            return;
        }


        const messageWrapper =
            document.createElement("div");


        messageWrapper.classList.add(
            "message"
        );


        if (role === "user") {

            messageWrapper.classList.add(
                "user-message"
            );

        } else {

            messageWrapper.classList.add(
                "assistant-message"
            );

        }


        // -----------------------------------------------------
        // AVATAR
        // -----------------------------------------------------

        const avatar =
            document.createElement("div");


        avatar.classList.add(
            "message-avatar"
        );


        if (role === "user") {

            avatar.classList.add(
                "user-message-avatar"
            );


            avatar.textContent =
                "U";

        } else {

            avatar.classList.add(
                "ai-message-avatar"
            );


            avatar.textContent =
                "✦";

        }


        // -----------------------------------------------------
        // BUBBLE
        // -----------------------------------------------------

        const bubble =
            document.createElement("div");


        bubble.classList.add(
            "message-bubble"
        );


        // -----------------------------------------------------
        // TEXT
        // -----------------------------------------------------

        const messageText =
            document.createElement("div");


        messageText.classList.add(
            "message-text"
        );


        // -----------------------------------------------------
        // MARKDOWN
        // -----------------------------------------------------

        if (
            role === "assistant" &&
            typeof marked !== "undefined"
        ) {

            messageText.innerHTML =
                marked.parse(text);


            highlightCode(
                messageText
            );


            addCopyButtons(
                messageText
            );

        } else {

            messageText.textContent =
                text;

        }


        // -----------------------------------------------------
        // BUILD
        // -----------------------------------------------------

        bubble.appendChild(
            messageText
        );


        messageWrapper.appendChild(
            avatar
        );


        messageWrapper.appendChild(
            bubble
        );


        chatMessages.appendChild(
            messageWrapper
        );


        scrollToBottom();

    }


    // =========================================================
    // AI TYPING MESSAGE
    // =========================================================

    function typeAssistantMessage(text) {

        return new Promise((resolve) => {

            if (!chatMessages) {

                resolve();

                return;

            }


            isTyping = true;


            const messageWrapper =
                document.createElement("div");


            messageWrapper.classList.add(
                "message",
                "assistant-message"
            );


            // -------------------------------------------------
            // AVATAR
            // -------------------------------------------------

            const avatar =
                document.createElement("div");


            avatar.classList.add(
                "message-avatar",
                "ai-message-avatar"
            );


            avatar.textContent =
                "✦";


            // -------------------------------------------------
            // BUBBLE
            // -------------------------------------------------

            const bubble =
                document.createElement("div");


            bubble.classList.add(
                "message-bubble"
            );


            // -------------------------------------------------
            // TEXT
            // -------------------------------------------------

            const messageText =
                document.createElement("div");


            messageText.classList.add(
                "message-text"
            );


            bubble.appendChild(
                messageText
            );


            messageWrapper.appendChild(
                avatar
            );


            messageWrapper.appendChild(
                bubble
            );


            chatMessages.appendChild(
                messageWrapper
            );


            // -------------------------------------------------
            // TYPE
            // -------------------------------------------------

            let index = 0;


            const typingSpeed = 18;


            function typeNextCharacter() {

                if (
                    index >=
                    text.length
                ) {

                    // -----------------------------------------
                    // FINAL MARKDOWN
                    // -----------------------------------------

                    if (
                        typeof marked !==
                        "undefined"
                    ) {

                        messageText.innerHTML =
                            marked.parse(text);

                    } else {

                        messageText.textContent =
                            text;

                    }


                    highlightCode(
                        messageText
                    );


                    addCopyButtons(
                        messageText
                    );


                    isTyping = false;


                    scrollToBottom();


                    resolve();


                    return;

                }


                messageText.textContent +=
                    text.charAt(index);


                index++;


                scrollToBottom();


                setTimeout(
                    typeNextCharacter,
                    typingSpeed
                );

            }


            typeNextCharacter();

        });

    }


    // =========================================================
    // PRISM
    // =========================================================

    function highlightCode(container) {

        if (
            typeof Prism ===
            "undefined"
        ) {

            return;

        }


        container
            .querySelectorAll("pre code")
            .forEach((block) => {

                Prism.highlightElement(
                    block
                );

            });

    }


    // =========================================================
    // LOAD CURRENT CHAT FROM LOCAL MEMORY
    // =========================================================

    function loadMessages() {

        if (
            !messages ||
            messages.length === 0
        ) {

            if (welcomeMessage) {

                welcomeMessage.style.display =
                    "flex";

            }

            return;

        }


        if (welcomeMessage) {

            welcomeMessage.style.display =
                "none";

        }


        chatMessages
            .querySelectorAll(".message")
            .forEach((message) => {

                message.remove();

            });


        messages.forEach(
            (message) => {

                addMessage(
                    message.role,
                    message.content
                );

            }
        );


        scrollToBottom();

    }


    // =========================================================
    // TYPING INDICATOR
    // =========================================================

    function showTyping() {

        if (!typingIndicator) {
            return;
        }


        typingIndicator.style.display =
            "flex";


        const textElement =
            typingIndicator.querySelector(
                ".typing-text"
            );


        if (textElement) {

            textElement.textContent =
                "AI is typing...";

        }


        scrollToBottom();

    }


    function hideTyping() {

        if (!typingIndicator) {
            return;
        }


        typingIndicator.style.display =
            "none";

    }


    // =========================================================
    // SCROLL
    // =========================================================

    function scrollToBottom() {

        setTimeout(() => {

            if (chatMessages) {

                chatMessages.scrollTop =
                    chatMessages.scrollHeight;

            }

        }, 30);

    }


    // =========================================================
    // SEND BUTTON
    // =========================================================

    sendBtn.addEventListener(
        "click",
        () => {

            sendMessage();

        }
    );


    // =========================================================
    // ENTER TO SEND
    // =========================================================

    messageInput.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Enter" &&
                !event.shiftKey
            ) {

                event.preventDefault();

                sendMessage();

            }

        }
    );


    // =========================================================
    // AUTO RESIZE
    // =========================================================

    messageInput.addEventListener(
        "input",
        () => {

            messageInput.style.height =
                "auto";


            const newHeight =
                Math.min(
                    messageInput.scrollHeight,
                    120
                );


            messageInput.style.height =
                newHeight + "px";

        }
    );


    // =========================================================
    // QUICK QUESTIONS
    // =========================================================

    quickQuestions.forEach(
        (button) => {

            button.addEventListener(
                "click",
                () => {

                    const message =
                        button.dataset.message;


                    if (!message) {
                        return;
                    }


                    if (
                        !chatWindow.classList.contains(
                            "open"
                        )
                    ) {

                        openChat();

                    }


                    sendMessage(
                        message
                    );

                }
            );

        }
    );


    // =========================================================
    // CLEAR CHAT
    // =========================================================

    if (clearChatBtn) {

        clearChatBtn.addEventListener(
            "click",
            clearChat
        );

    }


    // =========================================================
    // REFRESH / NEW CHAT
    // =========================================================

    if (refreshChatBtn) {

        refreshChatBtn.addEventListener(
            "click",
            startNewChat
        );

    }


    // =========================================================
    // CLEAR CURRENT CHAT
    // =========================================================

    function clearChat() {

        messages = [];


        saveMessages();


        chatMessages
            .querySelectorAll(".message")
            .forEach((message) => {

                message.remove();

            });


        if (welcomeMessage) {

            welcomeMessage.style.display =
                "flex";

        }


        messageInput.value = "";


        messageInput.style.height =
            "auto";


        hideTyping();

        hideWebsiteAnalyzing();


        messageInput.focus();

    }


    // =========================================================
    // ESC TO CLOSE
    // =========================================================

    document.addEventListener(
        "keydown",
        (event) => {

            if (
                event.key === "Escape"
            ) {

                if (
                    chatSidebar &&
                    chatSidebar.classList.contains(
                        "open"
                    )
                ) {

                    closeSidebar();

                    return;

                }


                if (
                    chatWindow.classList.contains(
                        "open"
                    )
                ) {

                    closeChat();

                }

            }

        }
    );


    // =========================================================
    // COPY CODE BUTTON
    // =========================================================

    function addCopyButtons(container) {

        const codeBlocks =
            container.querySelectorAll(
                "pre"
            );


        codeBlocks.forEach(
            (pre) => {

                if (
                    pre.querySelector(
                        ".copy-code-btn"
                    )
                ) {

                    return;

                }


                const button =
                    document.createElement(
                        "button"
                    );


                button.className =
                    "copy-code-btn";


                button.textContent =
                    "Copy";


                button.type =
                    "button";


                button.addEventListener(
                    "click",
                    async () => {

                        const code =
                            pre.querySelector(
                                "code"
                            );


                        if (!code) {
                            return;
                        }


                        try {

                            await navigator
                                .clipboard
                                .writeText(
                                    code.innerText
                                );


                            button.textContent =
                                "Copied ✓";


                            setTimeout(
                                () => {

                                    button.textContent =
                                        "Copy";

                                },
                                2000
                            );


                        } catch (error) {

                            console.error(
                                "Copy failed:",
                                error
                            );


                            button.textContent =
                                "Failed";


                            setTimeout(
                                () => {

                                    button.textContent =
                                        "Copy";

                                },
                                2000
                            );

                        }

                    }
                );


                pre.appendChild(
                    button
                );

            }
        );

    }


    // =========================================================
    // INITIAL STATE
    // =========================================================

    chatWindow.setAttribute(
        "aria-hidden",
        "true"
    );


    hideTyping();


    // =========================================================
    // LOAD CURRENT LOCAL MESSAGES
    // =========================================================

    loadMessages();


    // =========================================================
    // LOAD DATABASE CHAT HISTORY
    // =========================================================

    loadConversationsFromDatabase();


    // =========================================================
    // READY
    // =========================================================

    console.log(
        "AI Assistant JavaScript + Database Chat History + Delete Conversation loaded successfully."
    );

});