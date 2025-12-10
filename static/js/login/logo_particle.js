// ① パーティクルロゴが完成したらメイン表示
window.showMainContent = function() {
    const container = document.getElementById("logo-container");
    const header = document.getElementById("header-wrapper");
    const main = document.getElementById("main-content");

    container.style.transition = "opacity 1.2s ease-out";
    container.style.opacity = 0;

    setTimeout(() => {
        container.style.display = "none";
        // header.style.display = "block";
        main.style.display = "block";
    }, 1200);
};

// 画面が開いたときに再生されるロゴアニメーション
// 粒子が集まってロゴを形成する
window.addEventListener("load", () => {
    const canvas = document.getElementById("particleCanvas");
    const ctx = canvas.getContext("2d");

    // Canvas サイズセット（常に画面にフィット）
    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    resize();
    window.addEventListener("resize", resize);

    // ロゴ画像読み込み
    const logo = new Image();
    logo.src = "/static/images/SASUTENA_logo.png";

    logo.onload = () => {
        const w = canvas.width;
        const h = canvas.height;

        // オフスクリーンCanvasでロゴを描画してピクセル取得
        const temp = document.createElement("canvas");
        temp.width = w;
        temp.height = h;
        const tctx = temp.getContext("2d");

        // ロゴを中央に縮小して描画
        const logoW = w * 0.4;
        const ratio = logoW / logo.width;
        const logoH = logo.height * ratio;

        tctx.drawImage(logo, (w - logoW) / 2, (h - logoH) / 2, logoW, logoH);

        const imgData = tctx.getImageData(0, 0, w, h);
        const particles = [];

        // 粒子生成
        const step = 3; // 粒子密度（小さいほど密度↑）
        for (let y = 0; y < h; y += step) {
            for (let x = 0; x < w; x += step) {
                const i = (y * w + x) * 4;
                if (imgData.data[i + 3] > 128) {
                    particles.push({
                        x: Math.random() * w,
                        y: Math.random() * h,
                        tx: x,
                        ty: y,
                        vx: 0,
                        vy: 0
                    });
                }
            }
        }

        // アニメーション
        function animate() {
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

            requestAnimationFrame(animate);
        }

        animate();

        // 3秒後にメインへ切り替え（showMainContentを呼ぶ）
        setTimeout(() => {
            window.showMainContent();
        }, 3000);
    };
});
