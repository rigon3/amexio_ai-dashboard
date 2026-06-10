/*
 * timeFilter.js — Reusable Monthly / Quarterly / Yearly tab control
 *
 * Renders into an existing container (keep the container's `time-tabs` class so
 * the styling is unchanged). Calls onChange(period) when the active tab changes.
 *
 * Usage:
 *   TimeFilter.mount({
 *     container: "#time-filter",
 *     onChange: (period) => loadData(period),   // 'monthly' | 'quarterly' | 'yearly'
 *   });
 *
 * Rendered DOM is built in JS (no HTML-partial fetch) so it works under file://.
 */
window.TimeFilter = {
  mount({ container, periods, active, onChange } = {}) {
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

    el.innerHTML = "";
    periods.forEach((p) => {
      const btn = document.createElement("button");
      btn.className = "time-tab" + (p.value === current ? " active" : "");
      btn.textContent = p.label;
      btn.addEventListener("click", () => {
        if (p.value === current) return;
        current = p.value;
        el.querySelectorAll(".time-tab").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        if (typeof onChange === "function") onChange(current);
      });
      el.appendChild(btn);
    });

    return {
      get value() { return current; },
    };
  },
};
