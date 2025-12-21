document.addEventListener("DOMContentLoaded", () => {
    const toggleButtons = document.querySelectorAll("[data-toggle-target]");

    toggleButtons.forEach((button) => {
        const targetSelector = button.getAttribute("data-toggle-target");
        if (!targetSelector) {
            return;
        }

        const target = document.querySelector(targetSelector);
        if (!target) {
            return;
        }

        const labelOpen = button.getAttribute("data-label-open") || "開く";
        const labelClose = button.getAttribute("data-label-close") || "閉じる";

        const updateState = () => {
            const isHidden = target.classList.contains("d-none");
            button.textContent = isHidden ? labelOpen : labelClose;
            button.setAttribute("aria-expanded", String(!isHidden));
        };

        updateState();

        button.addEventListener("click", () => {
            target.classList.toggle("d-none");
            updateState();
        });
    });

    const rejectModals = document.querySelectorAll(".reject-modal");
    rejectModals.forEach((modal) => {
        modal.addEventListener("shown.bs.modal", () => {
            const input = modal.querySelector("textarea, input, select");
            if (input) {
                input.focus();
                if (typeof input.select === "function") {
                    input.select();
                }
            }
        });

        modal.addEventListener("hidden.bs.modal", () => {
            const form = modal.querySelector("form");
            if (form) {
                form.reset();
            }
        });
    });
});
