(function () {
    var root = document.getElementById("mineroChatbot");
    if (!root) {
        return;
    }

    var toggleBtn = root.querySelector("[data-chatbot-toggle]");
    var closeBtn = root.querySelector("[data-chatbot-close]");
    var body = root.querySelector("[data-chatbot-body]");
    var form = root.querySelector("[data-chatbot-form]");
    var input = root.querySelector("[data-chatbot-input]");
    var chipsWrap = root.querySelector("[data-chatbot-chips]");
    var sendBtn = root.querySelector(".minero-chatbot-send");
    var BOT_REPLY_DELAY_MS = 2200;
    var isSending = false;

    function getCookie(name) {
        var value = "; " + document.cookie;
        var parts = value.split("; " + name + "=");
        if (parts.length === 2) {
            return parts.pop().split(";").shift();
        }
        return "";
    }

    function appendMessage(text, role) {
        var msg = document.createElement("div");
        msg.className = "minero-msg " + role;
        msg.textContent = text;
        body.appendChild(msg);
        body.scrollTop = body.scrollHeight;
        return msg;
    }

    function appendTypingIndicator() {
        var msg = document.createElement("div");
        msg.className = "minero-msg bot typing";
        msg.setAttribute("aria-label", "Chat Bot Minero esta escribiendo");
        msg.innerHTML =
            "<span>Respondiendo</span>" +
            '<span class="minero-typing-dots" aria-hidden="true">' +
            "<span></span><span></span><span></span>" +
            "</span>";
        body.appendChild(msg);
        body.scrollTop = body.scrollHeight;
        return msg;
    }

    function removeMessage(node) {
        if (node && node.parentNode) {
            node.parentNode.removeChild(node);
        }
    }

    function wait(ms) {
        return new Promise(function (resolve) {
            setTimeout(resolve, ms);
        });
    }

    async function waitMinDelay(startTime) {
        var elapsed = Date.now() - startTime;
        var remaining = BOT_REPLY_DELAY_MS - elapsed;
        if (remaining > 0) {
            await wait(remaining);
        }
    }

    function setBusyState(busy) {
        isSending = busy;
        input.disabled = busy;
        if (sendBtn) {
            sendBtn.disabled = busy;
        }
    }

    function toggleChat(forceOpen) {
        var open = typeof forceOpen === "boolean" ? forceOpen : !root.classList.contains("open");
        root.classList.toggle("open", open);
        if (open) {
            setTimeout(function () {
                input.focus();
            }, 100);
        }
    }

    function renderChips(sugerencias) {
        if (!chipsWrap) {
            return;
        }
        chipsWrap.innerHTML = "";
        (sugerencias || []).slice(0, 4).forEach(function (sug) {
            var chip = document.createElement("button");
            chip.type = "button";
            chip.className = "minero-chatbot-chip";
            chip.textContent = sug;
            chip.addEventListener("click", function () {
                input.value = sug;
                form.dispatchEvent(new Event("submit", { cancelable: true }));
            });
            chipsWrap.appendChild(chip);
        });
    }

    async function sendMessage(message) {
        if (isSending) {
            return;
        }

        setBusyState(true);
        appendMessage(message, "user");
        var typingMsg = appendTypingIndicator();
        var startTime = Date.now();
        var response;
        var data;
        var requestFailed = false;
        var parseFailed = false;

        try {
            response = await fetch("/chatbot/responder/", {
                method: "POST",
                credentials: "same-origin",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({ mensaje: message }),
            });

            try {
                data = await response.json();
            } catch (err) {
                parseFailed = true;
                data = null;
            }
        } catch (err) {
            requestFailed = true;
        }

        await waitMinDelay(startTime);
        removeMessage(typingMsg);

        if (requestFailed) {
            appendMessage("Estoy fuera de linea por un momento. Intenta de nuevo.", "bot");
            setBusyState(false);
            input.focus();
            return;
        }

        if (parseFailed) {
            appendMessage("No pude validar la sesion del chat. Recarga la pagina e intenta nuevamente.", "bot");
            setBusyState(false);
            input.focus();
            return;
        }

        if (!response.ok || !data.ok) {
            appendMessage("No pude procesar el mensaje. Intenta nuevamente.", "bot");
            setBusyState(false);
            input.focus();
            return;
        }

        appendMessage(data.respuesta, "bot");
        renderChips(data.sugerencias || []);
        setBusyState(false);
        input.focus();
    }

    toggleBtn.addEventListener("click", function () {
        toggleChat();
    });

    closeBtn.addEventListener("click", function () {
        toggleChat(false);
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        if (isSending) {
            return;
        }
        var value = (input.value || "").trim();
        if (!value) {
            return;
        }
        input.value = "";
        sendMessage(value);
    });

    if (chipsWrap) {
        chipsWrap.addEventListener("click", function (event) {
            if (isSending) {
                return;
            }
            var target = event.target;
            if (!target.classList.contains("minero-chatbot-chip")) {
                return;
            }
            input.value = target.textContent || "";
            form.dispatchEvent(new Event("submit", { cancelable: true }));
        });
    }
})();
