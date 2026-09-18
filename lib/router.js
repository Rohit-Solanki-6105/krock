/**
 * Krock Ultra-Fast Top Progress Loader
 * Displays a sleek top progress bar during page navigation
 */
(function () {
    if (typeof window === "undefined" || window.__KROCK_PROGRESS_ACTIVE__) return;
    window.__KROCK_PROGRESS_ACTIVE__ = true;

    function createProgressBar() {
        if (document.getElementById("krock-top-loader")) return;
        const bar = document.createElement("div");
        bar.id = "krock-top-loader";
        bar.style.cssText = "position:fixed;top:0;left:0;height:3px;background:#2563eb;width:0%;transition:width 0.3s ease;z-index:99999;box-shadow:0 0 10px #2563eb;";
        document.body.appendChild(bar);
    }

    function startProgress() {
        createProgressBar();
        const bar = document.getElementById("krock-top-loader");
        if (bar) {
            bar.style.width = "30%";
            setTimeout(() => { if (bar) bar.style.width = "70%"; }, 200);
        }
    }

    function finishProgress() {
        const bar = document.getElementById("krock-top-loader");
        if (bar) {
            bar.style.width = "100%";
            setTimeout(() => {
                if (bar && bar.parentNode) bar.parentNode.removeChild(bar);
            }, 300);
        }
    }

    document.addEventListener("click", (e) => {
        const anchor = e.target.closest("a");
        if (!anchor) return;
        const href = anchor.getAttribute("href");
        if (!href || href.startsWith("#") || href.startsWith("http://") || href.startsWith("https://") || href.startsWith("//") || anchor.getAttribute("target") === "_blank") {
            return;
        }
        startProgress();
    });

    window.addEventListener("pageshow", () => {
        finishProgress();
    });
})();
