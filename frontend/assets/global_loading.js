/**
 * Overlay global de carregamento — exibe card centralizado quando qualquer
 * componente Dash estiver em loading (data-dash-is-loading="true").
 */
(function () {
    const DELAY_SHOW_MS = 120;
    const DELAY_HIDE_MS = 80;

    let showTimer = null;
    let hideTimer = null;
    let observer = null;

    function getOverlay() {
        return document.getElementById("global-loading-overlay");
    }

    function isAnythingLoading() {
        return document.querySelector('[data-dash-is-loading="true"]') !== null;
    }

    function setVisible(visible) {
        const overlay = getOverlay();
        if (!overlay) {
            return;
        }
        overlay.classList.toggle("is-visible", visible);
        overlay.setAttribute("aria-hidden", visible ? "false" : "true");
    }

    function syncOverlay() {
        if (isAnythingLoading()) {
            clearTimeout(hideTimer);
            hideTimer = null;
            if (!showTimer) {
                showTimer = setTimeout(function () {
                    showTimer = null;
                    if (isAnythingLoading()) {
                        setVisible(true);
                    }
                }, DELAY_SHOW_MS);
            }
            return;
        }

        clearTimeout(showTimer);
        showTimer = null;
        if (!hideTimer) {
            hideTimer = setTimeout(function () {
                hideTimer = null;
                if (!isAnythingLoading()) {
                    setVisible(false);
                }
            }, DELAY_HIDE_MS);
        }
    }

    function attachObserver() {
        if (observer || !document.body) {
            return;
        }

        observer = new MutationObserver(syncOverlay);
        observer.observe(document.body, {
            subtree: true,
            attributes: true,
            childList: true,
            attributeFilter: ["data-dash-is-loading"],
        });
        syncOverlay();
    }

    function waitForOverlay() {
        if (getOverlay()) {
            attachObserver();
            return;
        }
        setTimeout(waitForOverlay, 50);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", waitForOverlay);
    } else {
        waitForOverlay();
    }
})();
