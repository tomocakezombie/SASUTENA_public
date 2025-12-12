let originalBodyOverflow = "";
let originalBodyMargin = "";
let splashTimeoutId = null;
let animationFrameId = null;
let animationActive = false;
let splashDismissed = false;
let resizeHandler = null;

// ① パーティクルロゴが完成したらメイン表示
window.showMainContent = function(options = {}) {
    const container = document.getElementById("logo-container");
    const main = document.getElementById("main-content");
    const { immediate = false } = options;

    if (!container || splashDismissed) {
        return;
    }

    splashDismissed = true;
    animationActive = false;

    if (animationFrameId !== null) {
        cancelAnimationFrame(animationFrameId);
        animationFrameId = null;
    }

    if (splashTimeoutId !== null) {
        clearTimeout(splashTimeoutId);
        splashTimeoutId = null;
    }

    const fadeDuration = immediate ? 0 : 1200;
    container.style.transition = immediate ? "none" : "opacity 1.2s ease-out";
    container.style.opacity = 0;

    setTimeout(() => {
        container.style.display = "none";
        if (main) {
            main.style.display = "block";
        }
        document.body.style.overflow = originalBodyOverflow;
        document.body.style.margin = originalBodyMargin;
        if (resizeHandler) {
            window.removeEventListener("resize", resizeHandler);
            resizeHandler = null;
        }
    }, fadeDuration);
};

// 画面が開いたときに再生されるロゴアニメーション
// 粒子が集まってロゴを形成する
window.addEventListener("load", () => {
    const container = document.getElementById("logo-container");
    const canvas = document.getElementById("particleCanvas");
    const ctx = canvas.getContext("2d");

    if (!container) {
        return;
    }

    // スクロールバーを抑止して全画面中央に配置
    originalBodyOverflow = document.body.style.overflow;
    originalBodyMargin = document.body.style.margin;
    document.body.style.overflow = "hidden";
    document.body.style.margin = "0";

    container.style.position = "fixed";
    container.style.inset = "0";
    container.style.width = "100vw";
    container.style.height = "100vh";
    container.style.display = "flex";
    container.style.alignItems = "center";
    container.style.justifyContent = "center";

    canvas.style.display = "block";
    canvas.style.width = "100%";
    canvas.style.height = "100%";

    // Canvas サイズセット（常に画面にフィット）
    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    resizeHandler = resize;
    window.addEventListener("resize", resizeHandler);

    container.addEventListener("click", () => window.showMainContent({ immediate: true }));

    // ロゴ画像読み込み
    const logo = new Image();
    logo.src = "/static/images/SASUTENA_logo.png";

    logo.onload = () => {
        if (splashDismissed) {
            return;
        }

        const w = canvas.width;
        const h = canvas.height;

        // オフスクリーンCanvasでロゴを描画してピクセル取得
        const temp = document.createElement("canvas");
        temp.width = w;
        temp.height = h;
        const tctx = temp.getContext("2d");

        // ロゴの描画サイズをウィンドウに合わせて算出（どちらか小さい側に対して8割程度）
        const maxLogoWidth = w * 0.8;
        const maxLogoHeight = h * 0.8;
        const scale = Math.max(Math.min(maxLogoWidth / logo.width, maxLogoHeight / logo.height), 0.1);
        const logoW = logo.width * scale;
        const logoH = logo.height * scale;

        tctx.drawImage(logo, (w - logoW) / 2, (h - logoH) / 2, logoW, logoH);

        const imgData = tctx.getImageData(0, 0, w, h);
        const candidates = [];

        // 粒子生成候補
        const step = 2;
        for (let y = 0; y < h; y += step) {
            for (let x = 0; x < w; x += step) {
                const i = (y * w + x) * 4;
                if (imgData.data[i + 3] > 128) {
                    candidates.push({ x, y });
                }
            }
        }

        const TARGET_PARTICLES = 300000;
        const particles = [];
        // Fisher-Yates シャッフルでランダム抽出
        for (let i = candidates.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            const tmp = candidates[i];
            candidates[i] = candidates[j];
            candidates[j] = tmp;
        }

        const limit = Math.min(TARGET_PARTICLES, candidates.length);
        for (let idx = 0; idx < limit; idx++) {
            const { x, y } = candidates[idx];
            particles.push({
                x: Math.random() * w,
                y: Math.random() * h,
                tx: x,
                ty: y,
                vx: 0,
                vy: 0
            });
        }

        // アニメーション
        function animate() {
            if (!animationActive) {
                return;
            }

            ctx.clearRect(0, 0, w, h);

            particles.forEach(p => {
                p.vx += (p.tx - p.x) * 0.02;
                p.vy += (p.ty - p.y) * 0.02;
                p.vx *= 0.90;
                p.vy *= 0.90;
                p.x += p.vx;
                p.y += p.vy;

                ctx.fillStyle = "rgba(104, 241, 143, 0.8)";
                ctx.fillRect(p.x, p.y, 2, 2);
            });

            animationFrameId = requestAnimationFrame(animate);
        }

        animationActive = true;
        animationFrameId = requestAnimationFrame(animate);

        // 3秒後にメインへ切り替え（showMainContentを呼ぶ）
        splashTimeoutId = setTimeout(() => {
            window.showMainContent();
        }, 3000);
    };
});
