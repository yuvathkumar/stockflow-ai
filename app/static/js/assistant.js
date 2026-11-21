(function () {
    const toggle = document.getElementById("flo-toggle");
    const panel = document.getElementById("flo-panel");
    if (!toggle || !panel) return;

    const closeButton = document.getElementById("flo-close");
    const form = document.getElementById("flo-form");
    const input = document.getElementById("flo-input");
    const messages = document.getElementById("flo-messages");
    const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
    const MAX_ROWS_SHOWN = 10;

    function openPanel() {
        panel.hidden = false;
        toggle.setAttribute("aria-expanded", "true");
        input.focus();
    }

    function closePanel() {
        panel.hidden = true;
        toggle.setAttribute("aria-expanded", "false");
        toggle.focus();
    }

    toggle.addEventListener("click", () => (panel.hidden ? openPanel() : closePanel()));
    closeButton.addEventListener("click", closePanel);
    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && !panel.hidden) closePanel();
    });

    function addMessage(classes, text) {
        const bubble = document.createElement("div");
        bubble.className = "flo-msg " + classes;
        if (text) {
            const line = document.createElement("div");
            line.textContent = text;
            bubble.appendChild(line);
        }
        messages.appendChild(bubble);
        messages.scrollTop = messages.scrollHeight;
        return bubble;
    }

    function buildTable(columns, rows) {
        const wrap = document.createElement("div");
        wrap.className = "flo-table-wrap";
        const table = document.createElement("table");
        table.className = "table table-sm mb-0";

        const headerRow = table.createTHead().insertRow();
        columns.forEach((column) => {
            const th = document.createElement("th");
            th.textContent = column;
            headerRow.appendChild(th);
        });

        const body = table.createTBody();
        rows.slice(0, MAX_ROWS_SHOWN).forEach((row) => {
            const tr = body.insertRow();
            row.forEach((value) => {
                tr.insertCell().textContent = value === null ? "–" : value;
            });
        });

        wrap.appendChild(table);
        return wrap;
    }

    function showTyping() {
        const bubble = addMessage("bot");
        bubble.innerHTML = '<div class="flo-typing"><span></span><span></span><span></span></div>';
        return bubble;
    }

    async function ask(question) {
        addMessage("user", question);
        input.value = "";
        input.disabled = true;
        const typing = showTyping();

        try {
            const response = await fetch("/api/ask", {
                method: "POST",
                headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken },
                body: JSON.stringify({ question }),
            });
            const data = await response.json();
            typing.remove();

            if (!response.ok) {
                addMessage("bot error", data.error || "Something went wrong.");
                return;
            }

            const count = data.rows.length;
            const reply = addMessage(
                "bot",
                count
                    ? `Here's what I found (${count} row${count === 1 ? "" : "s"}):`
                    : "I ran the query, but it returned no rows."
            );
            if (count) reply.appendChild(buildTable(data.columns, data.rows));
            if (count > MAX_ROWS_SHOWN) {
                const note = document.createElement("div");
                note.className = "small text-muted mt-1";
                note.textContent = `Showing the first ${MAX_ROWS_SHOWN} of ${count} rows.`;
                reply.appendChild(note);
            }

            const details = document.createElement("details");
            const summary = document.createElement("summary");
            summary.textContent = "Show SQL";
            const pre = document.createElement("pre");
            pre.textContent = data.sql;
            details.append(summary, pre);
            reply.appendChild(details);
        } catch (error) {
            typing.remove();
            addMessage("bot error", "I couldn't reach the server. Please try again.");
        } finally {
            input.disabled = false;
            input.focus();
            messages.scrollTop = messages.scrollHeight;
        }
    }

    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const question = input.value.trim();
        if (question) ask(question);
    });

    messages.addEventListener("click", (event) => {
        const chip = event.target.closest(".flo-chip");
        if (chip) ask(chip.dataset.question);
    });
})();