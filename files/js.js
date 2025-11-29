document.addEventListener("DOMContentLoaded", function () {

    const menu = document.getElementById("menu");
    const main = document.getElementById("mainContent");
    const button = document.getElementById("menuToggle");
    const floatingShow = document.getElementById("menuShowFloating");

    if (!menu || !main || !button) return;

    let visible = true;

    // Hide/show logic for the sidebar toggle inside the menu
    button.addEventListener("click", function () {
        visible = !visible;

        if (visible) {
            // Show menu
            menu.classList.remove("menu-hidden");
            menu.classList.add("menu-visible");
            button.textContent = "⮜ Hide menu";

            // Restore margin on desktop
            if (window.innerWidth > 768) {
                main.style.marginLeft = "260px";
            }

            // Hide floating show button
            if (floatingShow) floatingShow.style.display = "none";

        } else {
            // Hide menu
            menu.classList.remove("menu-visible");
            menu.classList.add("menu-hidden");
            button.textContent = "⮞ Show menu";

            // Allow full-screen content
            main.style.marginLeft = "0";

            // Show floating button
            if (floatingShow) floatingShow.style.display = "block";
        }
    });

    // === FLOATING ☰ BUTTON BEHAVIOR ===
    if (floatingShow) {
        floatingShow.addEventListener("click", function () {
            visible = true;

            // Show menu
            menu.classList.add("menu-visible");
            menu.classList.remove("menu-hidden");

            // Desktop margin restore
            if (window.innerWidth > 768) {
                main.style.marginLeft = "260px";
            }

            // Hide floating button
            floatingShow.style.display = "none";

            // Update main button label
            button.textContent = "⮜ Hide menu";
        });
    }

    // Handle resizing between desktop/mobile
    window.addEventListener("resize", function () {
        if (visible) {
            if (window.innerWidth > 768) {
                main.style.marginLeft = "260px";
            } else {
                main.style.marginLeft = "0";
            }
        }
    });

});
