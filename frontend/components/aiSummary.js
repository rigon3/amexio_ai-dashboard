/*
 * aiSummary.js — Reusable "AI Insights" summary panel
 *
 * Collapsed by default (header bar only: logo + title + Generate button).
 * Expands to reveal Brief/Standard tabs + text once Generate is clicked.
 * Self-contained: injects its own styles, builds DOM in JS (file:// safe).
 *
 * Usage:
 *   const summary = AISummary.mount({
 *     container: "#ai-summary",
 *     view: "training_budget",            // backend prompt selector
 *     title: "Training Budget Analysis",
 *     apiUrl: "http://127.0.0.1:8000",
 *     getPeriod: () => currentPeriod,     // sent as ?period=
 *   });
 *   summary.reset();   // collapse + clear (e.g. when the period changes)
 */
window.AISummary = (function () {
  let stylesInjected = false;

  // "AI sparkles" logo — a large 4-point star with a small companion.
  const LOGO = `<svg class="ais-logo" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <path d="M12 2.3l1.7 5.2 5.2 1.7-5.2 1.7L12 16.1l-1.7-5.2L5.1 9.2l5.2-1.7L12 2.3z" fill="currentColor"/>
      <path d="M18.6 14.2l.85 2.55 2.55.85-2.55.85-.85 2.55-.85-2.55-2.55-.85 2.55-.85.85-2.55z" fill="currentColor" opacity="0.65"/>
    </svg>`;

  function injectStyles() {
    if (stylesInjected) return;
    stylesInjected = true;
    const css = `
      .ais-card { border-radius:12px; padding:1.25rem 1.35rem; color:#fff;
        background:linear-gradient(135deg,#15384F 0%,#1B4965 45%,#2C6F8F 100%);
        box-shadow:0 4px 16px rgba(27,73,101,.22); }
      .ais-bar { display:flex; align-items:center; justify-content:space-between;
        gap:.75rem; flex-wrap:wrap; }
      .ais-title { display:flex; align-items:center; gap:.5rem;
        font-weight:700; font-size:.95rem; }
      .ais-logo { color:#00D9FF; flex-shrink:0; }
      .ais-gen { background:#FF6B35; color:#fff; border:none; border-radius:8px;
        padding:.55rem 1.1rem; font-weight:600; font-size:.85rem; cursor:pointer;
        font-family:inherit; transition:background .15s; white-space:nowrap; }
      .ais-gen:hover { background:#FF7A45; }
      .ais-gen:disabled { opacity:.7; cursor:not-allowed; }
      .ais-body { margin-top:1rem; }
      .ais-body[hidden] { display:none; }
      .ais-tabs { display:flex; border-bottom:1px solid rgba(255,255,255,.15);
        margin-bottom:.85rem; }
      .ais-tab { padding:.4rem .9rem; font-size:.82rem; font-weight:600; cursor:pointer;
        color:rgba(255,255,255,.45); background:transparent; border:none;
        border-bottom:2px solid transparent; font-family:inherit; transition:all .15s; }
      .ais-tab.active { color:#00D9FF; border-bottom-color:#00D9FF; }
      .ais-text { font-size:.9rem; line-height:1.7; color:#fff; margin:0; }
      .ais-text[hidden] { display:none; }
      .ais-spinner { display:inline-block; width:13px; height:13px;
        border:2px solid rgba(255,255,255,.3); border-top-color:#fff; border-radius:50%;
        animation:ais-spin .7s linear infinite; margin-right:.4rem; vertical-align:middle; }
      @keyframes ais-spin { to { transform:rotate(360deg); } }
    `;
    const style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
  }

  function mount({ container, view = "training_budget", title = "",
                   apiUrl = "http://127.0.0.1:8000", getPeriod = () => "monthly" } = {}) {
    injectStyles();
    const el = typeof container === "string" ? document.querySelector(container) : container;
    if (!el) { console.warn("AISummary: container not found:", container); return null; }

    el.innerHTML = `
      <div class="ais-card">
        <div class="ais-bar">
          <div class="ais-title">${LOGO}<span>AI Insights${title ? " — " + title : ""}</span></div>
          <button class="ais-gen" type="button">Generate Insights</button>
        </div>
        <div class="ais-body" hidden>
          <div class="ais-tabs">
            <button class="ais-tab active" data-tab="brief" type="button">Brief Summary</button>
            <button class="ais-tab" data-tab="standard" type="button">Standard Summary</button>
          </div>
          <p class="ais-text" data-panel="brief"></p>
          <p class="ais-text" data-panel="standard" hidden></p>
        </div>
      </div>`;

    const btn = el.querySelector(".ais-gen");
    const body = el.querySelector(".ais-body");
    const tabs = el.querySelectorAll(".ais-tab");
    const panels = el.querySelectorAll(".ais-text");
    const briefP = el.querySelector('[data-panel="brief"]');
    const standardP = el.querySelector('[data-panel="standard"]');

    function showTab(name) {
      tabs.forEach(t => t.classList.toggle("active", t.dataset.tab === name));
      panels.forEach(p => { p.hidden = p.dataset.panel !== name; });
    }
    tabs.forEach(tab => tab.addEventListener("click", () => showTab(tab.dataset.tab)));

    function reset() {
      body.hidden = true;
      briefP.textContent = "";
      standardP.textContent = "";
      showTab("brief");
    }

    btn.addEventListener("click", async () => {
      btn.innerHTML = '<span class="ais-spinner"></span>Generating...';
      btn.disabled = true;
      try {
        const res = await fetch(`${apiUrl}/summary?view=${view}&period=${getPeriod()}`, { method: "POST" });
        if (!res.ok) throw new Error("HTTP " + res.status);
        const { brief, standard } = await res.json();
        briefP.textContent = brief;
        standardP.textContent = standard;
        showTab("brief");
        body.hidden = false;
      } catch (e) {
        briefP.textContent = "Could not generate summary. Make sure the backend is running and Ollama has the model pulled.";
        standardP.textContent = "";
        showTab("brief");
        body.hidden = false;
      } finally {
        btn.textContent = "Generate Insights";
        btn.disabled = false;
      }
    });

    return { reset };
  }

  return { mount };
})();
