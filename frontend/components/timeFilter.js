/*
 * timeFilter.js — Reusable "Time Period" panel (Monthly / Quarterly / Yearly)
 *
 * Renders a card with a header and vertical buttons, matching the Home dashboard
 * styling. Self-contained: injects its own namespaced styles (.tf-*) so it drops
 * onto any page without relying on page CSS, and builds DOM in JS (file:// safe).
 *
 * Usage:
 *   TimeFilter.mount({
 *     container: "#time-filter",
 *     onChange: (period) => loadData(period),   // 'monthly' | 'quarterly' | 'yearly'
 *   });
 */
window.TimeFilter = (function () {
  let stylesInjected = false;

  function injectStyles() {
    if (stylesInjected) return;
    stylesInjected = true;
    const css = `
      .tf-panel { background:#fff; border:1px solid rgba(212,219,229,0.9); border-radius:18px;
        box-shadow:0 2px 4px rgba(16,24,40,.04), 0 12px 30px rgba(16,24,40,.05); overflow:hidden; }
      .tf-header { padding:1.15rem 1.25rem 0.85rem; font-size:1rem; font-weight:500; color:#50607A; }
      .tf-tabs { display:flex; flex-direction:column; gap:0.55rem; padding:0 1.25rem 1.25rem; }
      .tf-tab { padding:0.7rem 1rem; border-radius:10px; font-weight:600; font-size:0.95rem;
        cursor:pointer; border:1px solid #E0E4E8; background:#EEF2F7; color:#50607A;
        font-family:inherit; transition:all 0.15s; text-align:center; }
      .tf-tab.active { background:#FF6B35; color:#fff; border-color:#FF6B35; }
      .tf-tab:not(.active):hover { background:#E4EAF2; }
    `;
    const style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
  }

  function mount({ container, periods, active, onChange, header = "Time Period" } = {}) {
    injectStyles();
    const el = typeof container === "string" ? document.querySelector(container) : container;
    if (!el) {
      console.warn("TimeFilter: container not found:", container);
      return null;
    }

    periods = periods || [
      { value: "monthly",   label: "Monthly" },
      { value: "quarterly", label: "Quarterly" },
      { value: "yearly",    label: "Yearly" },
    ];
    let current = active || periods[0].value;

    const tabsHtml = periods
      .map((p) => `<button class="tf-tab${p.value === current ? " active" : ""}" type="button" data-period="${p.value}">${p.label}</button>`)
      .join("");
    el.innerHTML = `<div class="tf-panel"><div class="tf-header">${header}</div><div class="tf-tabs">${tabsHtml}</div></div>`;

    const btns = el.querySelectorAll(".tf-tab");
    btns.forEach((btn) => btn.addEventListener("click", () => {
      const period = btn.dataset.period;
      if (period === current) return;
      current = period;
      btns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      if (typeof onChange === "function") onChange(current);
    }));

    return {
      get value() { return current; },
    };
  }

  return { mount };
})();
