import { useEffect, useRef, useState, useCallback } from "react";

const GREEN      = "#00D166";
const GREEN_DIM  = "#003D1F";

const TICKERS = [
  "KXFED +2.3%", "NASDAQ-HIGH ▲", "AI-PROD-MAR", "OIL-70-Q2 ▼",
  "KXKHAMENEI ▲", "NVDA-250 +4.1%", "BTC-100K ▲", "KXFEDCHAIRNOM",
  "SP500-HIGH ▲", "GOLD-3000 +0.8%", "CONF: 0.94", "SIGNAL: +1",
  "KXELECTION ▲", "RATE-CUT-MAR ▼", "CONF: 0.88", "SIGNAL: −1",
  "KXSUPREME ▲",  "EUR-USD 1.09 ▼", "CONF: 0.91", "KALSHI API ✓",
];

const BOOT_LINES = [
  "> INITIALIZING KAT...",
  "> CONNECTING TO KALSHI API...",
  "> LOADING FINBERT MODEL...",
  "> SCANNING 30+ RSS FEEDS...",
  "> EMBEDDING MARKET INDEX...",
  "> SYSTEM READY.",
];

// ─── Perspective helpers ────────────────────────────────────────────
const FOV = 420;

function project(x, y, z, cx, cy) {
  if (z <= 0) return null;
  const s = FOV / z;
  return { x: cx + x * s, y: cy + y * s, s };
}

// ─── Trend line class ───────────────────────────────────────────────
class TrendLine {
  constructor() { this.reset(Math.random() * 2200); }

  reset(z = 2200) {
    this.z     = z;
    this.ox    = (Math.random() - 0.5) * 2400;
    this.oy    = (Math.random() - 0.5) * 1400;
    this.n     = 50 + Math.floor(Math.random() * 50);
    this.speed = 9 + Math.random() * 14;
    this.color = Math.random() > 0.15 ? GREEN : "#00FF80";
    // Generate random-walk price path
    this.pts = [];
    let v = 0;
    const drift = (Math.random() - 0.48) * 0.4;
    for (let i = 0; i < this.n; i++) {
      v += (Math.random() - 0.5) * 7 + drift;
      this.pts.push(v);
    }
  }

  draw(ctx, cx, cy, glitching) {
    this.z -= this.speed;
    if (this.z <= 30) { this.reset(); return; }

    const brightness = Math.min(1, (2200 - this.z) / 1800);
    ctx.globalAlpha = (0.08 + brightness * 0.92) * (glitching ? 0.3 + Math.random() * 0.7 : 1);
    ctx.lineWidth   = Math.max(0.4, brightness * 2.8);
    ctx.strokeStyle = this.color;
    ctx.beginPath();
    let started = false;

    for (let i = 0; i < this.pts.length; i++) {
      const p = project(
        this.ox + (i - this.pts.length / 2) * 16,
        this.oy + this.pts[i] * 1.8,
        this.z,
        cx, cy
      );
      if (!p) continue;
      if (!started) { ctx.moveTo(p.x, p.y); started = true; }
      else ctx.lineTo(p.x, p.y);
    }
    ctx.stroke();
    ctx.globalAlpha = 1;
  }
}

// ─── Floating ticker label class ────────────────────────────────────
class TickerLabel {
  constructor() { this.reset(Math.random() * 2200); }

  reset(z = 2200) {
    this.z     = z;
    this.ox    = (Math.random() - 0.5) * 2600;
    this.oy    = (Math.random() - 0.5) * 1600;
    this.text  = TICKERS[Math.floor(Math.random() * TICKERS.length)];
    this.speed = 7 + Math.random() * 11;
    this.pos   = this.text.includes("▲") || this.text.includes("+");
  }

  draw(ctx, cx, cy, glitching) {
    this.z -= this.speed;
    if (this.z <= 30) { this.reset(); return; }

    const brightness = Math.min(1, (2200 - this.z) / 1800);
    const p = project(this.ox, this.oy, this.z, cx, cy);
    if (!p) return;

    const size = Math.max(8, p.s * 13);
    ctx.font        = `700 ${size}px 'JetBrains Mono', monospace`;
    ctx.fillStyle   = this.pos ? GREEN : "#FF4560";
    ctx.globalAlpha = brightness * 0.55 * (glitching ? Math.random() : 1);
    ctx.fillText(this.text, p.x, p.y);
    ctx.globalAlpha = 1;
  }
}

// ─── Component ──────────────────────────────────────────────────────
export default function Opener({ onComplete }) {
  const canvasRef   = useRef(null);
  const phaseRef    = useRef("flying"); // flying | glitching | done
  const [phase, setPhase] = useState("flying");
  const [bootText, setBootText] = useState("");
  const [caretOn, setCaretOn]   = useState(true);

  // Caret blink
  useEffect(() => {
    const id = setInterval(() => setCaretOn(c => !c), 530);
    return () => clearInterval(id);
  }, []);

  // Boot message typewriter
  useEffect(() => {
    let lineIdx = 0, charIdx = 0, active = true;
    let timeout;

    const type = () => {
      if (!active || lineIdx >= BOOT_LINES.length) return;
      const line = BOOT_LINES[lineIdx];
      if (charIdx <= line.length) {
        setBootText(line.slice(0, charIdx));
        charIdx++;
        timeout = setTimeout(type, charIdx === 1 ? 200 : 38);
      } else {
        lineIdx++; charIdx = 0;
        timeout = setTimeout(type, 320);
      }
    };
    timeout = setTimeout(type, 500);
    return () => { active = false; clearTimeout(timeout); };
  }, []);

  // Canvas render loop
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const resize = () => {
      canvas.width  = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    resize();
    window.addEventListener("resize", resize);

    const lines  = Array.from({ length: 40 }, () => new TrendLine());
    const labels = Array.from({ length: 22 }, () => new TickerLabel());

    const startMs   = Date.now();
    let glitchStart = null;
    let raf;

    const tick = () => {
      raf = requestAnimationFrame(tick);
      const W  = canvas.width, H = canvas.height;
      const cx = W / 2,        cy = H / 2;
      const elapsed = (Date.now() - startMs) / 1000;
      const glitching = phaseRef.current === "glitching";

      // ── Clear with trail ──────────────────────────────────────────
      ctx.fillStyle = glitching
        ? `rgba(0,0,0,${0.12 + Math.random() * 0.15})`
        : "rgba(0,0,0,0.16)";
      ctx.fillRect(0, 0, W, H);

      // ── Perspective grid ─────────────────────────────────────────
      const gridZ = [400, 700, 1100, 1600, 2100];
      gridZ.forEach(gz => {
        const a = Math.max(0, 0.06 - gz / 40000);
        ctx.globalAlpha = a;
        ctx.strokeStyle = GREEN_DIM;
        ctx.lineWidth   = 0.4;
        for (let gy = -500; gy <= 500; gy += 100) {
          const p0 = project(-1400, gy, gz, cx, cy);
          const p1 = project( 1400, gy, gz, cx, cy);
          if (!p0 || !p1) continue;
          ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(p1.x, p1.y); ctx.stroke();
        }
        ctx.globalAlpha = 1;
      });
      // Vanishing-point verticals
      ctx.globalAlpha = 0.04;
      ctx.strokeStyle = GREEN_DIM;
      ctx.lineWidth   = 0.4;
      for (let vx = -1400; vx <= 1400; vx += 180) {
        ctx.beginPath(); ctx.moveTo(cx + vx, 0); ctx.lineTo(cx, cy); ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // ── Trend lines + labels ──────────────────────────────────────
      lines.forEach(l  => l.draw(ctx, cx, cy, glitching));
      labels.forEach(l => l.draw(ctx, cx, cy, glitching));

      // ── Scanlines ────────────────────────────────────────────────
      ctx.fillStyle = "rgba(0,0,0,0.025)";
      for (let y = 0; y < H; y += 4) ctx.fillRect(0, y, W, 2);

      // ── Glitch effects ────────────────────────────────────────────
      if (glitching) {
        if (!glitchStart) glitchStart = Date.now();
        const gElapsed   = (Date.now() - glitchStart) / 1000;
        const intensity  = Math.min(1, gElapsed / 1.1);

        // RGB pixel shift
        try {
          const id  = ctx.getImageData(0, 0, W, H);
          const out = ctx.createImageData(W, H);
          const sh  = Math.floor(intensity * 28);
          for (let i = 0; i < id.data.length; i += 4) {
            const px = (i / 4) % W;
            const py = Math.floor(i / 4 / W);
            const ri = (py * W + Math.min(W - 1, px + sh)) * 4;
            const bi = (py * W + Math.max(0,     px - sh)) * 4;
            out.data[i]   = id.data[ri]   || 0;
            out.data[i+1] = id.data[i+1]  || 0;
            out.data[i+2] = id.data[bi+2] || 0;
            out.data[i+3] = id.data[i+3]  || 255;
          }
          ctx.putImageData(out, 0, 0);
        } catch (_) {}

        // Horizontal tears
        const numTears = Math.floor(intensity * 14);
        for (let t = 0; t < numTears; t++) {
          const ty = Math.random() * H;
          const th = Math.random() * 10 + 2;
          const tx = (Math.random() - 0.5) * intensity * 70;
          try {
            const strip = ctx.getImageData(0, ty, W, th);
            ctx.putImageData(strip, tx, ty);
          } catch (_) {}
        }

        // Noise blocks
        const numBlocks = Math.floor(intensity * 8);
        for (let b = 0; b < numBlocks; b++) {
          ctx.fillStyle = `rgba(0,${Math.floor(Math.random()*255)},${Math.floor(Math.random()*80)},${Math.random()*0.35})`;
          ctx.fillRect(Math.random()*W, Math.random()*H, Math.random()*140+20, Math.random()*14+4);
        }

        // Black fade-out
        if (gElapsed > 1.1) {
          const fa = Math.min(1, (gElapsed - 1.1) / 0.45);
          ctx.fillStyle = `rgba(0,0,0,${fa})`;
          ctx.fillRect(0, 0, W, H);
          if (fa >= 0.99 && phaseRef.current !== "done") {
            phaseRef.current = "done";
            setPhase("done");
          }
        }
      }

      // ── Fade-in at start ─────────────────────────────────────────
      if (elapsed < 0.7) {
        ctx.fillStyle = `rgba(0,0,0,${1 - elapsed / 0.7})`;
        ctx.fillRect(0, 0, W, H);
      }
    };

    tick();

    // Trigger glitch after 3.8 s
    const glitchTimer = setTimeout(() => {
      phaseRef.current = "glitching";
      setPhase("glitching");
    }, 3800);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(glitchTimer);
      window.removeEventListener("resize", resize);
    };
  }, []);

  // Fire onComplete once done
  useEffect(() => {
    if (phase === "done") {
      const t = setTimeout(onComplete, 80);
      return () => clearTimeout(t);
    }
  }, [phase, onComplete]);

  const glitching = phase === "glitching";

  return (
    <div style={{ position:"fixed", inset:0, zIndex:1000, background:"#000", overflow:"hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&display=swap');
        @keyframes blink  { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes gText  {
          0%,100% { transform:translateX(0);    color:rgba(0,209,102,0.8); }
          25%     { transform:translateX(-5px); color:#FF4560; clip-path:inset(20% 0 60% 0); }
          50%     { transform:translateX( 5px); color:#00FFFF; clip-path:inset(60% 0 20% 0); }
          75%     { transform:translateX(-2px); color:rgba(0,209,102,0.8); clip-path:none; }
        }
        @keyframes hudPulse { 0%,100%{opacity:0.5} 50%{opacity:1} }
        @keyframes cornerIn {
          from { opacity:0; transform:scale(1.3); }
          to   { opacity:1; transform:scale(1); }
        }
      `}</style>

      <canvas ref={canvasRef} style={{ position:"absolute", inset:0, display:"block" }} />

      {/* Vignette */}
      <div style={{ position:"absolute", inset:0, background:"radial-gradient(ellipse at center, transparent 25%, rgba(0,0,0,0.72) 100%)", pointerEvents:"none" }} />

      {/* HUD */}
      <div style={{ position:"absolute", inset:0, fontFamily:"'JetBrains Mono',monospace", pointerEvents:"none" }}>

        {/* Corner brackets */}
        {[
          { top:28, left:28,  borderTop:"1px solid", borderLeft:"1px solid" },
          { top:28, right:28, borderTop:"1px solid", borderRight:"1px solid" },
          { bottom:28, left:28,  borderBottom:"1px solid", borderLeft:"1px solid" },
          { bottom:28, right:28, borderBottom:"1px solid", borderRight:"1px solid" },
        ].map((s, i) => (
          <div key={i} style={{ position:"absolute", ...s, borderColor:"rgba(0,209,102,0.35)", width:44, height:44, animation:`cornerIn 0.6s ${i * 0.1}s both` }} />
        ))}

        {/* Top bar */}
        <div style={{ position:"absolute", top:34, left:"50%", transform:"translateX(-50%)", display:"flex", alignItems:"center", gap:10, color:"rgba(0,209,102,0.6)", fontSize:11, letterSpacing:2.5, whiteSpace:"nowrap", animation:glitching?"gText 0.12s infinite":"hudPulse 2s infinite" }}>
          <div style={{ width:6, height:6, borderRadius:"50%", background:GREEN, animation:"blink 1s infinite" }} />
          KAT — KALSHI ALGORITHMIC TRADING
          <div style={{ width:6, height:6, borderRadius:"50%", background:GREEN, animation:"blink 1s 0.5s infinite" }} />
        </div>

        {/* Bottom-left: boot text */}
        <div style={{ position:"absolute", bottom:44, left:52, color:"rgba(0,209,102,0.85)", fontSize:12, letterSpacing:1, animation:glitching?"gText 0.13s infinite":"none" }}>
          {bootText}<span style={{ animation:"blink 0.65s infinite", visibility:caretOn?"visible":"hidden" }}>_</span>
        </div>

        {/* Bottom-right: telemetry */}
        <div style={{ position:"absolute", bottom:44, right:52, color:"rgba(0,209,102,0.3)", fontSize:10, letterSpacing:1, textAlign:"right", lineHeight:1.8 }}>
          <div style={{ animation:glitching?"gText 0.1s infinite":"none" }}>DEPTH: {glitching ? "⚠ ERR" : "∞"}</div>
          <div>MARKETS: 2,847</div>
          <div>LATENCY: 9ms</div>
        </div>

        {/* Center crosshair */}
        <div style={{ position:"absolute", top:"50%", left:"50%", transform:"translate(-50%,-50%)", opacity:glitching?0:0.18, transition:"opacity 0.2s" }}>
          <div style={{ position:"relative", width:48, height:48 }}>
            <div style={{ position:"absolute", top:"50%", left:0, right:0, height:1, background:GREEN }} />
            <div style={{ position:"absolute", left:"50%", top:0, bottom:0, width:1, background:GREEN }} />
            <div style={{ position:"absolute", inset:0, border:"1px solid rgba(0,209,102,0.6)", borderRadius:"50%", animation:"hudPulse 1.5s infinite" }} />
          </div>
        </div>

        {/* Skip hint */}
        <div
          onClick={onComplete}
          style={{ position:"absolute", top:34, right:80, color:"rgba(0,209,102,0.25)", fontSize:10, letterSpacing:2, cursor:"pointer", pointerEvents:"all", textTransform:"uppercase" }}
        >
          SKIP →
        </div>

      </div>
    </div>
  );
}