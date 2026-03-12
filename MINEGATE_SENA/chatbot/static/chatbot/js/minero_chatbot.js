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
        appendMessage(message, "user");

        try {
            var response = await fetch("/chatbot/responder/", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                    "X-CSRFToken": getCookie("csrftoken"),
                },
                body: JSON.stringify({ mensaje: message }),
            });

            var data = await response.json();
            if (!response.ok || !data.ok) {
                appendMessage("No pude procesar el mensaje. Intenta nuevamente.", "bot");
                return;
            }

            appendMessage(data.respuesta, "bot");
            renderChips(data.sugerencias || []);
        } catch (err) {
            appendMessage("Estoy fuera de linea por un momento. Intenta de nuevo.", "bot");
        }
    }

    toggleBtn.addEventListener("click", function () {
        toggleChat();
    });

    closeBtn.addEventListener("click", function () {
        toggleChat(false);
    });

    form.addEventListener("submit", function (event) {
        event.preventDefault();
        var value = (input.value || "").trim();
        if (!value) {
            return;
        }
        input.value = "";
        sendMessage(value);
    });

    chipsWrap.addEventListener("click", function (event) {
        var target = event.target;
        if (!target.classList.contains("minero-chatbot-chip")) {
            return;
        }
        input.value = target.textContent || "";
        form.dispatchEvent(new Event("submit", { cancelable: true }));
    });
})();
