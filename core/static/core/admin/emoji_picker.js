(function () {
    var EMOJIS = [
        "😀", "😃", "😄", "😁", "😊", "🙂", "😉", "😍", "🥳", "🎉",
        "🎊", "✅", "❌", "⚠️", "🔔", "📢", "📅", "🗓️", "⏰", "💼",
        "🏖️", "🤒", "📌", "📝", "👍", "👎", "❤️", "🙏", "🚀", "🌟",
        "⭐", "✨", "💪", "🤝", "👋", "😴", "🌴", "☀️", "🌧️", "❄️",
        "🎄", "🎁", "🥂", "🍀", "📍", "💬", "ℹ️", "✔️", "⛔", "🔥"
    ];

    function insertAtCursor(textarea, text) {
        var start = textarea.selectionStart;
        var end = textarea.selectionEnd;
        var value = textarea.value;
        textarea.value = value.slice(0, start) + text + value.slice(end);
        var newPos = start + text.length;
        textarea.selectionStart = textarea.selectionEnd = newPos;
        textarea.focus();
        textarea.dispatchEvent(new Event("input", { bubbles: true }));
    }

    function buildPicker(textarea) {
        var wrapper = document.createElement("div");
        wrapper.className = "emoji-picker-wrapper";

        var toggle = document.createElement("button");
        toggle.type = "button";
        toggle.className = "emoji-picker-toggle";
        toggle.innerHTML = "😀 Додати emoji";

        var panel = document.createElement("div");
        panel.className = "emoji-picker-panel";

        EMOJIS.forEach(function (emoji) {
            var btn = document.createElement("button");
            btn.type = "button";
            btn.className = "emoji-picker-btn";
            btn.textContent = emoji;
            btn.title = emoji;
            btn.addEventListener("click", function () {
                insertAtCursor(textarea, emoji);
            });
            panel.appendChild(btn);
        });

        toggle.addEventListener("click", function () {
            panel.classList.toggle("open");
        });

        wrapper.appendChild(toggle);
        wrapper.appendChild(panel);
        textarea.parentNode.insertBefore(wrapper, textarea);
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("textarea.emoji-textarea").forEach(buildPicker);
    });
})();
