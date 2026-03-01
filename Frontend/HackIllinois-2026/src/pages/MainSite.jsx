import { useState, useEffect, useRef } from "react";
import * as THREE from "three";

const GREEN = "#00D166";

const PIPELINE_STEPS = [
  {
    id: "01",
    title: "RSS News Ingestion",
    subtitle: "30+ Sources",
    desc: "Polls WSJ, Bloomberg, CNBC, BBC, NYT and 25+ feeds every 10 seconds. Deduplicates via seen_links.txt and returns structured DataFrames ready for inference.",
    tag: "rss.py",
  },
  {
    id: "02",
    title: "FinBERT Sentiment",
    subtitle: "GPU Inference",
    desc: "A Modal A10G GPU runs ProsusAI/FinBERT. Entire batches score in a single GPU call, returning a label, confidence score, and directional signal.",
    tag: "modaltest.py",
  },
  {
    id: "03",
    title: "Market Matching",
    subtitle: "Semantic Search",
    desc: "SentenceTransformer embeds all open Kalshi markets. Cosine similarity instantly finds the best matching contract for each headline.",
    tag: "news_runner.py",
  },
  {
    id: "04",
    title: "Order Execution",
    subtitle: "RSA-PSS Auth",
    desc: "Cryptographically signed requests hit Kalshi's trade API. Limit orders are placed only when confidence clears 0.70 — protecting against low-signal noise.",
    tag: "kalshi_order_executor.py",
  },
];

const TECH = [
  { name: "FinBERT", desc: "Financial NLP" },
  { name: "Modal", desc: "GPU Cloud" },
  { name: "Kalshi API", desc: "Prediction Markets" },
  { name: "SentenceTransformers", desc: "Semantic Matching" },
  { name: "GDELT GKG", desc: "Global News Feed" },
  { name: "RSA-PSS", desc: "Auth Signing" },
];

const FAKE_TRADES = [
  { time: "14:32:07", headline: "Fed raises rates 50bps", ticker: "KXFED-25-0525", conf: 0.94, signal: -1 },
  { time: "14:31:44", headline: "Apple beats earnings expectations", ticker: "NASDAQ-HIGH-MAR", conf: 0.88, signal: 1 },
  { time: "14:30:21", headline: "Nvidia AI chip demand raised guidance", ticker: "NVDA-250-JUN", conf: 0.91, signal: 1 },
  { time: "14:29:55", headline: "Oil tumbles on weak China demand", ticker: "OIL-70-Q2", conf: 0.82, signal: -1 },
  { time: "14:28:13", headline: "OpenAI releases GPT-5 flagship model", ticker: "AI-PROD-MAR", conf: 0.87, signal: 1 },
];

function ThreeScene({ canvasRef }) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const W = canvas.offsetWidth, H = canvas.offsetHeight;
    const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(W, H, false);
    renderer.setClearColor(0x000000, 0);
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, W / H, 0.1, 1000);
    camera.position.z = 5;
    const count = 1400;
    const pos = new Float32Array(count * 3), col = new Float32Array(count * 3);
    for (let i = 0; i < count; i++) {
      pos[i*3]=(Math.random()-.5)*22; pos[i*3+1]=(Math.random()-.5)*22; pos[i*3+2]=(Math.random()-.5)*22;
      const g = Math.random() > 0.55;
      col[i*3]=g?0:0.12; col[i*3+1]=g?.82:.12; col[i*3+2]=g?.4:.12;
    }
    const geo = new THREE.BufferGeometry();
    geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    geo.setAttribute("color", new THREE.BufferAttribute(col, 3));
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ size:.045, vertexColors:true, transparent:true, opacity:.85 }));
    scene.add(pts);
    const shapes = [];
    for (let i = 0; i < 5; i++) {
      const m = new THREE.Mesh(
        new THREE.IcosahedronGeometry(.4+Math.random()*.65, 1),
        new THREE.MeshBasicMaterial({ color: i<3?0x00d166:0x003322, wireframe:true, transparent:true, opacity:.13+Math.random()*.18 })
      );
      m.position.set((Math.random()-.5)*9,(Math.random()-.5)*7,(Math.random()-.5)*5);
      m.userData = { rx:(Math.random()-.5)*.012, ry:(Math.random()-.5)*.012, fs:Math.random()*.0018+.0008, fo:Math.random()*Math.PI*2 };
      scene.add(m); shapes.push(m);
    }
    const t1 = new THREE.Mesh(new THREE.TorusGeometry(2,.014,8,120), new THREE.MeshBasicMaterial({ color:0x00d166, transparent:true, opacity:.22 }));
    t1.rotation.x = Math.PI/3; scene.add(t1);
    const t2 = new THREE.Mesh(new THREE.TorusGeometry(2.7,.009,8,120), new THREE.MeshBasicMaterial({ color:0x00d166, transparent:true, opacity:.1 }));
    t2.rotation.x=Math.PI/5; t2.rotation.z=Math.PI/4; scene.add(t2);
    let raf, t=0;
    const tick = () => {
      raf=requestAnimationFrame(tick); t+=.005;
      pts.rotation.y+=.0007; pts.rotation.x+=.00025;
      t1.rotation.z+=.003; t2.rotation.y+=.002;
      shapes.forEach(s => { s.rotation.x+=s.userData.rx; s.rotation.y+=s.userData.ry; s.position.y+=Math.sin(t+s.userData.fo)*s.userData.fs; });
      renderer.render(scene, camera);
    };
    tick();
    const onResize = () => { const w=canvas.offsetWidth,h=canvas.offsetHeight; camera.aspect=w/h; camera.updateProjectionMatrix(); renderer.setSize(w,h,false); };
    window.addEventListener("resize", onResize);
    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); renderer.dispose(); };
  }, []);
  return null;
}

function LiveFeed() {
  const [trades, setTrades] = useState(FAKE_TRADES);
  const [idx, setIdx] = useState(0);
  useEffect(() => {
    const id = setInterval(() => {
      const now = new Date();
      const ts = `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}:${String(now.getSeconds()).padStart(2,"0")}`;
      setTrades(prev => [{ ...FAKE_TRADES[idx % FAKE_TRADES.length], time: ts }, ...prev].slice(0, 8));
      setIdx(i => i + 1);
    }, 2800);
    return () => clearInterval(id);
  }, [idx]);
  return (
    <div style={{ fontFamily:"'JetBrains Mono',monospace", fontSize:12 }}>
      {trades.map((t, i) => (
        <div key={i} style={{ display:"grid", gridTemplateColumns:"72px 64px 160px 1fr 44px", gap:8, padding:"8px 0", borderBottom:"1px solid rgba(0,209,102,0.07)", opacity:Math.max(0.3,1-i*0.09), animation:i===0?"fadeIn 0.35s ease":undefined, alignItems:"center" }}>
          <span style={{ color:"#555" }}>{t.time}</span>
          <span style={{ color:t.signal===1?GREEN:"#FF4560", fontWeight:700 }}>{t.signal===1?"▲ YES":"▼  NO"}</span>
          <span style={{ color:GREEN, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{t.ticker}</span>
          <span style={{ color:"#888", overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{t.headline}</span>
          <span style={{ color:"#666", textAlign:"right" }}>{(t.conf*100).toFixed(0)}%</span>
        </div>
      ))}
    </div>
  );
}

export default function MainSite() {
  const canvasRef = useRef(null);
  const [scrolled, setScrolled] = useState(false);
  const [activeStep, setActiveStep] = useState(null);
  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 40);
    window.addEventListener("scroll", fn);
    return () => window.removeEventListener("scroll", fn);
  }, []);

  return (
    <>
      <style>{`
        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
        html, body, #root { width: 100%; min-height: 100vh; background: #000; color: #fff; }
        body { overflow-x: hidden; }
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=JetBrains+Mono:wght@400;700&display=swap');
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: #000; }
        ::-webkit-scrollbar-thumb { background: #00D166; }
        @keyframes fadeIn { from { opacity:0; transform:translateY(-6px); } to { opacity:1; transform:translateY(0); } }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:0.25; } }
        @keyframes floatY { 0%,100% { transform:translateY(0); } 50% { transform:translateY(-10px); } }
        .nav-link { color:#999; text-decoration:none; font-size:12px; font-weight:600; letter-spacing:1.5px; text-transform:uppercase; transition:color 0.2s; }
        .nav-link:hover { color:#00D166; }
        .step-card { transition:transform 0.25s, border-color 0.25s, background 0.25s !important; cursor:pointer; }
        .step-card:hover { transform:translateY(-3px) !important; border-color:#00D166 !important; }
        .chip:hover { border-color:#00D166 !important; color:#00D166 !important; background:rgba(0,209,102,0.07) !important; }
        .chip { transition:all 0.2s; }
        .btn-primary { transition:all 0.22s; background:#00D166; color:#000; border:none; border-radius:3px; padding:13px 30px; font-size:13px; font-weight:800; cursor:pointer; letter-spacing:1px; text-transform:uppercase; font-family:'Syne',sans-serif; }
        .btn-primary:hover { background:#00A34F; transform:translateY(-2px); box-shadow:0 8px 28px rgba(0,209,102,0.35); }
        .btn-ghost { transition:all 0.22s; background:transparent; color:#888; border:1px solid #333; border-radius:3px; padding:13px 30px; font-size:13px; font-weight:600; cursor:pointer; letter-spacing:1px; text-transform:uppercase; font-family:'Syne',sans-serif; }
        .btn-ghost:hover { color:#00D166; border-color:rgba(0,209,102,0.4); background:rgba(0,209,102,0.05); }
        .file-row { display:flex; gap:16px; align-items:center; padding:9px 16px; background:#080808; border:1px solid #161616; border-radius:2px; font-family:'JetBrains Mono',monospace; font-size:12px; }
      `}</style>

      <div style={{ fontFamily:"'Syne',sans-serif", background:"#000", color:"#fff", width:"100%", minHeight:"100vh" }}>

        {/* NAV */}
        <nav style={{ position:"fixed", top:0, left:0, right:0, zIndex:100, display:"flex", alignItems:"center", justifyContent:"space-between", padding:"0 clamp(24px,5vw,64px)", height:64, background:scrolled?"rgba(0,0,0,0.88)":"transparent", borderBottom:scrolled?"1px solid rgba(0,209,102,0.12)":"none", backdropFilter:scrolled?"blur(14px)":"none", transition:"all 0.3s ease" }}>
          <div style={{ display:"flex", alignItems:"center", gap:10 }}>
            <div style={{ width:26, height:26, background:GREEN, clipPath:"polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)", flexShrink:0 }} />
            <span style={{ fontWeight:800, fontSize:16, letterSpacing:"-0.5px" }}>K<span style={{ color:GREEN }}>A</span>T</span>
          </div>
          <div style={{ display:"flex", gap:28 }}>
            {[["Pipeline","#pipeline"],["Innovation","#innovation"],["Live Feed","#live-feed"],["About","#about"]].map(([l,h]) => (
              <a key={l} href={h} className="nav-link">{l}</a>
            ))}
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:7, background:"rgba(0,209,102,0.07)", border:"1px solid rgba(0,209,102,0.22)", borderRadius:20, padding:"5px 14px", fontFamily:"JetBrains Mono", fontSize:11, color:GREEN }}>
            <div style={{ width:6, height:6, borderRadius:"50%", background:GREEN, animation:"pulse 1.5s infinite" }} />
            DEMO
          </div>
        </nav>

        {/* HERO */}
        <section style={{ position:"relative", width:"100%", height:"100vh", display:"flex", alignItems:"center", justifyContent:"center", overflow:"hidden" }}>
          <canvas ref={canvasRef} style={{ position:"absolute", inset:0, width:"100%", height:"100%", display:"block" }} />
          <ThreeScene canvasRef={canvasRef} />
          <div style={{ position:"absolute", inset:0, background:"repeating-linear-gradient(0deg,transparent,transparent 2px,rgba(0,0,0,0.025) 2px,rgba(0,0,0,0.025) 4px)", pointerEvents:"none", zIndex:1 }} />
          <div style={{ position:"absolute", top:"50%", left:"50%", transform:"translate(-50%,-50%)", width:"min(700px,90vw)", height:"min(700px,90vw)", background:"radial-gradient(circle,rgba(0,209,102,0.07) 0%,transparent 68%)", pointerEvents:"none", zIndex:1 }} />

          <div style={{ position:"relative", zIndex:2, textAlign:"center", width:"100%", maxWidth:960, padding:"0 clamp(24px,5vw,64px)", display:"flex", flexDirection:"column", alignItems:"center" }}>

            <h1 style={{ fontSize:"clamp(56px,10vw,118px)", fontWeight:800, lineHeight:0.88, letterSpacing:"-4px", marginBottom:28 }}>
              <span style={{ display:"block" }}>NEWS TO</span>
              <span style={{ display:"block", color:GREEN }}>TRADES IN</span>
              <span style={{ display:"block" }}>MILLISECONDS</span>
            </h1>

            <p style={{ fontFamily:"JetBrains Mono", fontSize:12, color:"#666", letterSpacing:3, textTransform:"uppercase" }}>
              Kalshi Algorithmic Trading
            </p>

            <p style={{ fontSize:"clamp(15px,2vw,18px)", color:"#aaa", maxWidth:540, lineHeight:1.75, margin:"24px auto 44px" }}>
              Autonomous prediction market trading. FinBERT reads breaking headlines, semantic search finds the right Kalshi contract, RSA-signed orders execute — all in under 10 seconds.
            </p>

            <div style={{ display:"flex", gap:14, justifyContent:"center", flexWrap:"wrap" }}>
              <button className="btn-primary" onClick={() => document.getElementById("pipeline").scrollIntoView({ behavior:"smooth" })}>See the Pipeline</button>
              <button className="btn-ghost" onClick={() => document.getElementById("live-feed").scrollIntoView({ behavior:"smooth" })}>Live Feed →</button>
            </div>

            <div style={{ display:"flex", gap:"clamp(24px,5vw,56px)", justifyContent:"center", marginTop:64, flexWrap:"wrap" }}>
              {[["30+","News Sources"],["10s","Poll Interval"],["0.70","Conf. Threshold"],["A10G","GPU Inference"]].map(([v,l]) => (
                <div key={l} style={{ textAlign:"center" }}>
                  <div style={{ fontSize:"clamp(24px,4vw,36px)", fontWeight:800, color:GREEN, letterSpacing:"-1.5px" }}>{v}</div>
                  <div style={{ fontSize:10, color:"#666", letterSpacing:2.5, textTransform:"uppercase", marginTop:4 }}>{l}</div>
                </div>
              ))}
            </div>
          </div>

          <div style={{ position:"absolute", bottom:32, left:"50%", transform:"translateX(-50%)", display:"flex", flexDirection:"column", alignItems:"center", gap:8, animation:"floatY 2.2s ease-in-out infinite" }}>
            <span style={{ fontSize:9, color:"#333", letterSpacing:3, textTransform:"uppercase" }}>Scroll</span>
            <div style={{ width:1, height:36, background:`linear-gradient(to bottom, ${GREEN}, transparent)` }} />
          </div>
        </section>

        {/* PIPELINE */}
        <section id="pipeline" style={{ padding:"clamp(64px,10vw,120px) clamp(24px,5vw,64px)" }}>
          <div style={{ maxWidth:1200, margin:"0 auto" }}>
            <div style={{ marginBottom:56 }}>
              <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:GREEN, letterSpacing:3, marginBottom:14, textTransform:"uppercase" }}>// Architecture</div>
              <h2 style={{ fontSize:"clamp(32px,5vw,64px)", fontWeight:800, letterSpacing:"-2px", lineHeight:1 }}>The Full Pipeline</h2>
              <p style={{ color:"#999", marginTop:16, maxWidth:520, fontSize:16, lineHeight:1.75 }}>
                Four stages, one goal: turn breaking news into a prediction market position before the crowd reacts.
              </p>
            </div>

            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit, minmax(240px, 1fr))", gap:2 }}>
              {PIPELINE_STEPS.map((step, i) => (
                <div key={step.id} className="step-card" onClick={() => setActiveStep(activeStep===i?null:i)}
                  style={{ background:activeStep===i?"rgba(0,209,102,0.05)":"#080808", border:`1px solid ${activeStep===i?GREEN:"#1a1a1a"}`, padding:"30px 26px", position:"relative", overflow:"hidden" }}>
                  <div style={{ position:"absolute", top:10, right:14, fontSize:74, fontWeight:800, color:"rgba(0,209,102,0.04)", lineHeight:1, fontFamily:"JetBrains Mono", pointerEvents:"none", userSelect:"none" }}>{step.id}</div>
                  <div style={{ fontFamily:"JetBrains Mono", fontSize:9, color:GREEN, letterSpacing:2.5, marginBottom:14, textTransform:"uppercase" }}>Step {step.id}</div>
                  <h3 style={{ fontSize:20, fontWeight:800, marginBottom:6, letterSpacing:"-0.5px", color:"#fff" }}>{step.title}</h3>
                  <div style={{ fontSize:11, color:GREEN, fontFamily:"JetBrains Mono", marginBottom:16, opacity:.7 }}>{step.subtitle}</div>
                  <p style={{ color:"#888", fontSize:14, lineHeight:1.8 }}>{step.desc}</p>
                  <div style={{ marginTop:24, display:"inline-block", background:"rgba(0,209,102,0.06)", border:"1px solid rgba(0,209,102,0.18)", borderRadius:2, padding:"3px 10px", fontFamily:"JetBrains Mono", fontSize:10, color:"#666" }}>{step.tag}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* INNOVATION */}
        <section id="innovation" style={{ padding:"clamp(64px,10vw,120px) clamp(24px,5vw,64px)", background:"#040404", width:"100%" }}>
          <div style={{ maxWidth:1200, margin:"0 auto" }}>
            <div style={{ marginBottom:56 }}>
              <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:GREEN, letterSpacing:3, marginBottom:14, textTransform:"uppercase" }}>// Innovation</div>
              <h2 style={{ fontSize:"clamp(32px,5vw,64px)", fontWeight:800, letterSpacing:"-2px", lineHeight:1 }}>Beyond Sentiment</h2>
              <p style={{ color:"#999", marginTop:16, maxWidth:580, fontSize:16, lineHeight:1.75 }}>
                Every news-driven trading system makes the same mistake. KAT doesn't.
              </p>
            </div>

            {/* Problem / Solution */}
            <div style={{ display:"grid", gridTemplateColumns:"repeat(auto-fit,minmax(320px,1fr))", gap:2, marginBottom:2 }}>
              {/* Problem */}
              <div style={{ background:"#080808", border:"1px solid #1a1a1a", padding:"clamp(28px,4vw,44px)" }}>
                <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:"#FF4560", letterSpacing:3, marginBottom:20, textTransform:"uppercase" }}>The Problem</div>
                <h3 style={{ fontSize:"clamp(22px,2.5vw,30px)", fontWeight:800, letterSpacing:"-0.5px", marginBottom:16, color:"#fff" }}>Tone ≠ Direction</h3>
                <p style={{ color:"#888", fontSize:15, lineHeight:1.85, marginBottom:28 }}>
                  FinBERT — and every other financial sentiment model — scores the <span style={{ color:"#ccc" }}>emotional tone</span> of a headline. But in prediction markets, tone and direction are often completely decoupled.
                </p>
                <div style={{ background:"#0d0d0d", border:"1px solid #1e1e1e", borderLeft:"3px solid #FF4560", padding:"18px 20px", fontFamily:"JetBrains Mono", fontSize:13 }}>
                  <div style={{ color:"#555", fontSize:10, letterSpacing:2, marginBottom:12, textTransform:"uppercase" }}>Example</div>
                  <div style={{ color:"#ccc", marginBottom:10, fontSize:13 }}>"Trump indicted on 4 counts"</div>
                  <div style={{ color:"#FF4560", marginBottom:8 }}>FinBERT: NEGATIVE ▼ → sell YES</div>
                  <div style={{ color:"#555", fontSize:12, borderTop:"1px solid #1a1a1a", paddingTop:10, marginTop:4 }}>
                    But "Will Trump win primary?" likely <span style={{ color:GREEN }}>goes UP</span> — controversy rallies his base
                  </div>
                </div>
              </div>

              {/* Solution */}
              <div style={{ background:"rgba(0,209,102,0.03)", border:"1px solid rgba(0,209,102,0.2)", padding:"clamp(28px,4vw,44px)", position:"relative", overflow:"hidden" }}>
                <div style={{ position:"absolute", top:-40, right:-40, width:220, height:220, background:"radial-gradient(circle,rgba(0,209,102,0.07),transparent 70%)", pointerEvents:"none" }} />
                <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:GREEN, letterSpacing:3, marginBottom:20, textTransform:"uppercase" }}>The Innovation</div>
                <h3 style={{ fontSize:"clamp(22px,2.5vw,30px)", fontWeight:800, letterSpacing:"-0.5px", marginBottom:16, color:"#fff" }}>Context-Aware LLM</h3>
                <p style={{ color:"#888", fontSize:15, lineHeight:1.85, marginBottom:28 }}>
                  KAT adds a second-stage <span style={{ color:"#fff", fontWeight:700 }}>Claude Haiku</span> pass that understands both the headline <span style={{ color:"#ccc" }}>and</span> the specific market question — inferring true directional impact, not just tone.
                </p>
                <div style={{ background:"rgba(0,0,0,0.5)", border:"1px solid rgba(0,209,102,0.15)", borderLeft:`3px solid ${GREEN}`, padding:"18px 20px", fontFamily:"JetBrains Mono", fontSize:13 }}>
                  <div style={{ color:"#555", fontSize:10, letterSpacing:2, marginBottom:12, textTransform:"uppercase" }}>Same Headline</div>
                  <div style={{ color:"#ccc", marginBottom:6, fontSize:13 }}>"Trump indicted on 4 counts"</div>
                  <div style={{ color:"#666", fontSize:12, marginBottom:10 }}>+ "Will Trump win the primary?"</div>
                  <div style={{ color:GREEN, marginBottom:8 }}>KAT: DIRECTIONAL ▲ → buy YES</div>
                  <div style={{ color:"#555", fontSize:12, borderTop:"1px solid rgba(0,209,102,0.1)", paddingTop:10, marginTop:4 }}>
                    LLM understands political dynamics, not just tone
                  </div>
                </div>
              </div>
            </div>

            {/* Two-stage diagram */}
            <div style={{ border:"1px solid #1a1a1a", overflow:"hidden", marginTop:2 }}>
              <div style={{ padding:"14px 24px", borderBottom:"1px solid #1a1a1a", fontFamily:"JetBrains Mono", fontSize:11, color:"#555" }}>
                Two-Stage Inference Pipeline
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr auto 1fr", alignItems:"center", padding:"clamp(24px,3vw,36px)", gap:0 }}>
                <div style={{ background:"#080808", border:"1px solid #1a1a1a", padding:"22px 24px" }}>
                  <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:"#555", letterSpacing:2, marginBottom:12, textTransform:"uppercase" }}>Stage 1</div>
                  <div style={{ fontSize:20, fontWeight:800, color:"#fff", marginBottom:6 }}>FinBERT</div>
                  <div style={{ fontFamily:"JetBrains Mono", fontSize:12, color:"#666", marginBottom:16 }}>Financial NLP Model</div>
                  <div style={{ fontFamily:"JetBrains Mono", fontSize:12, color:"#666", lineHeight:1.8 }}>
                    <div>Input: <span style={{ color:"#aaa" }}>raw headline</span></div>
                    <div>Output: <span style={{ color:"#aaa" }}>label · score · signal</span></div>
                  </div>
                  <div style={{ marginTop:18, display:"inline-block", background:"#0d0d0d", border:"1px solid #222", borderRadius:2, padding:"4px 12px", fontFamily:"JetBrains Mono", fontSize:10, color:"#555" }}>Running ✓</div>
                </div>

                <div style={{ display:"flex", flexDirection:"column", alignItems:"center", padding:"0 clamp(16px,2vw,32px)", gap:6 }}>
                  <div style={{ width:1, height:28, background:`linear-gradient(to bottom, transparent, rgba(0,209,102,0.4))` }} />
                  <div style={{ color:GREEN, fontSize:20 }}>→</div>
                  <div style={{ width:1, height:28, background:`linear-gradient(to bottom, rgba(0,209,102,0.4), transparent)` }} />
                </div>

                <div style={{ background:"rgba(0,209,102,0.04)", border:"1px solid rgba(0,209,102,0.25)", padding:"22px 24px", position:"relative", overflow:"hidden" }}>
                  <div style={{ position:"absolute", top:0, right:0, width:120, height:120, background:"radial-gradient(circle,rgba(0,209,102,0.07),transparent 70%)", pointerEvents:"none" }} />
                  <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:GREEN, letterSpacing:2, marginBottom:12, textTransform:"uppercase" }}>Stage 2</div>
                  <div style={{ fontSize:20, fontWeight:800, color:"#fff", marginBottom:6 }}>Claude Haiku</div>
                  <div style={{ fontFamily:"JetBrains Mono", fontSize:12, color:GREEN, opacity:.75, marginBottom:16 }}>Context-Aware LLM</div>
                  <div style={{ fontFamily:"JetBrains Mono", fontSize:12, color:"#666", lineHeight:1.8 }}>
                    <div>Input: <span style={{ color:"#aaa" }}>headline + market question</span></div>
                    <div>Output: <span style={{ color:"#aaa" }}>true direction (+1 / 0 / −1)</span></div>
                  </div>
                  <div style={{ marginTop:18, display:"inline-block", background:"rgba(0,209,102,0.08)", border:`1px solid rgba(0,209,102,0.3)`, borderRadius:2, padding:"4px 12px", fontFamily:"JetBrains Mono", fontSize:10, color:GREEN }}>Innovation ✦</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* LIVE FEED */}
        <section id="live-feed" style={{ padding:"clamp(64px,10vw,100px) clamp(24px,5vw,64px)", width:"100%" }}>
          <div style={{ maxWidth:1200, margin:"0 auto" }}>
            <div style={{ marginBottom:36, display:"flex", justifyContent:"space-between", alignItems:"flex-end", flexWrap:"wrap", gap:16 }}>
              <div>
                <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:GREEN, letterSpacing:3, marginBottom:12, textTransform:"uppercase" }}>// Execution Log</div>
                <h2 style={{ fontSize:"clamp(26px,4vw,48px)", fontWeight:800, letterSpacing:"-2px" }}>Live Trade Feed</h2>
              </div>
              <div style={{ display:"flex", alignItems:"center", gap:7, fontFamily:"JetBrains Mono", fontSize:11, color:GREEN }}>
                <div style={{ width:6, height:6, borderRadius:"50%", background:GREEN, animation:"pulse 1.5s infinite" }} />
                SIMULATED LIVE
              </div>
            </div>
            <div style={{ background:"#050505", border:"1px solid #111" }}>
              <div style={{ display:"flex", gap:6, padding:"12px 16px", borderBottom:"1px solid #0e0e0e", alignItems:"center" }}>
                {["#FF5F56","#FFBD2E","#27C93F"].map(c => <div key={c} style={{ width:10, height:10, borderRadius:"50%", background:c }} />)}
                <span style={{ fontFamily:"JetBrains Mono", fontSize:10, color:"#2a2a2a", marginLeft:8 }}>kat — trade_executor.py — 80×24</span>
              </div>
              <div style={{ padding:"10px 20px 8px", fontFamily:"JetBrains Mono", fontSize:10, color:"#444", letterSpacing:1.5, display:"grid", gridTemplateColumns:"72px 64px 160px 1fr 44px", gap:8, borderBottom:"1px solid #0e0e0e" }}>
                <span>TIME</span><span>SIG</span><span>TICKER</span><span>HEADLINE</span><span style={{ textAlign:"right" }}>CONF</span>
              </div>
              <div style={{ padding:"4px 20px 16px" }}><LiveFeed /></div>
            </div>
          </div>
        </section>

        {/* TECH */}
        <section id="tech" style={{ padding:"clamp(64px,10vw,100px) clamp(24px,5vw,64px)", background:"#040404", width:"100%" }}>
          <div style={{ maxWidth:1200, margin:"0 auto" }}>
            <div style={{ marginBottom:48 }}>
              <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:GREEN, letterSpacing:3, marginBottom:14, textTransform:"uppercase" }}>// Stack</div>
              <h2 style={{ fontSize:"clamp(32px,5vw,64px)", fontWeight:800, letterSpacing:"-2px" }}>Built With</h2>
            </div>
            <div style={{ display:"flex", flexWrap:"wrap", gap:10 }}>
              {TECH.map(t => (
                <div key={t.name} className="chip" style={{ background:"#080808", border:"1px solid #1a1a1a", borderRadius:3, padding:"14px 20px", cursor:"default" }}>
                  <div style={{ fontSize:14, fontWeight:700, marginBottom:4, color:"#fff" }}>{t.name}</div>
                  <div style={{ fontSize:12, color:"#666" }}>{t.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ABOUT */}
        <section id="about" style={{ padding:"clamp(64px,10vw,100px) clamp(24px,5vw,64px)", width:"100%" }}>
          <div style={{ maxWidth:1200, margin:"0 auto", display:"flex", justifyContent:"space-between", alignItems:"flex-start", flexWrap:"wrap", gap:56 }}>
            <div style={{ flex:"1 1 340px" }}>
              <div style={{ fontFamily:"JetBrains Mono", fontSize:10, color:GREEN, letterSpacing:3, marginBottom:14, textTransform:"uppercase" }}>// HackIllinois 2026</div>
              <h2 style={{ fontSize:"clamp(26px,4vw,48px)", fontWeight:800, letterSpacing:"-2px", marginBottom:16, lineHeight:1.1 }}>
                University of Illinois<br /><span style={{ color:GREEN }}>Urbana-Champaign</span>
              </h2>
              <p style={{ color:"#888", lineHeight:1.85, fontSize:15, maxWidth:420 }}>
                Built in 24 hours at HackIllinois 2026. An end-to-end autonomous trading system connecting real-time news, GPU-powered NLP, and live prediction market execution on Kalshi.
              </p>
            </div>
            <div style={{ display:"flex", flexDirection:"column", gap:8, flex:"1 1 400px" }}>
              {[
                { file:"News/rss.py",                     done:true,  desc:"30+ RSS feeds" },
                { file:"NLP/modaltest.py",                done:true,  desc:"GPU deployment" },
                { file:"NLP/sentiment.py",                done:true,  desc:"FinBERT API" },
                { file:"Kalshi/kalshi_auth.py",           done:true,  desc:"RSA auth" },
                { file:"Kalshi/kalshi_order_executor.py", done:true,  desc:"Order execution" },
                { file:"Kalshi/ticker_matcher.py",        done:false, desc:"Semantic match" },
                { file:"main.py",                         done:false, desc:"Orchestration" },
              ].map(f => (
                <div key={f.file} className="file-row">
                  <span style={{ fontSize:13 }}>{f.done?"✅":"🔨"}</span>
                  <span style={{ color:GREEN, flex:1, minWidth:0, overflow:"hidden", textOverflow:"ellipsis", whiteSpace:"nowrap" }}>{f.file}</span>
                  <span style={{ color:"#666", fontSize:11, flexShrink:0 }}>{f.desc}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer style={{ borderTop:"1px solid #0e0e0e", padding:"28px clamp(24px,5vw,64px)", display:"flex", justifyContent:"space-between", alignItems:"center", flexWrap:"wrap", gap:12, width:"100%" }}>
          <div style={{ display:"flex", alignItems:"center", gap:9 }}>
            <div style={{ width:18, height:18, background:GREEN, clipPath:"polygon(50% 0%,100% 25%,100% 75%,50% 100%,0% 75%,0% 25%)" }} />
            <span style={{ fontWeight:800, fontSize:14, letterSpacing:"-0.5px" }}>K<span style={{ color:GREEN }}>A</span>T</span>
          </div>
          <span style={{ color:"#333", fontFamily:"JetBrains Mono", fontSize:10 }}>HackIllinois 2026 — University of Illinois Urbana-Champaign</span>
          <span style={{ color:"#2a2a2a", fontSize:10 }}>Not financial advice. Demo only.</span>
        </footer>

      </div>
    </>
  );
}