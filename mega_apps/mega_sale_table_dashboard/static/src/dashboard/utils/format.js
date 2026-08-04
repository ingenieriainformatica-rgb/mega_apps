/** @odoo-module */

/**
 * Formats a Date object to YYYY-MM-DD string (ISO local date, no UTC shift).
 */
export function formatYMD(dateObj) {
    const y = dateObj.getFullYear();
    const m = String(dateObj.getMonth() + 1).padStart(2, "0");
    const d = String(dateObj.getDate()).padStart(2, "0");
    return `${y}-${m}-${d}`;
}

/**
 * Returns {date_from, date_to} for the current calendar month (day 1 → today).
 */
export function getCurrentMonthRange() {
    const today = new Date();
    const firstOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    return { date_from: formatYMD(firstOfMonth), date_to: formatYMD(today) };
}

/**
 * Returns {date_from, date_to} for the current ISO week (Monday → today).
 */
export function getCurrentWeekRange() {
    const today = new Date();
    const day = today.getDay(); // 0=Sun, 1=Mon, ...
    const monday = new Date(today);
    monday.setDate(today.getDate() - (day === 0 ? 6 : day - 1));
    return { date_from: formatYMD(monday), date_to: formatYMD(today) };
}

/**
 * Returns {date_from, date_to} for today only.
 */
export function getTodayRange() {
    const t = formatYMD(new Date());
    return { date_from: t, date_to: t };
}

/**
 * Formats a number as a currency string (Colombian locale, no decimals by default).
 * Does NOT prepend currency symbol — caller is responsible.
 */
export function formatCurrency(value, decimals = 0) {
    if (value === null || value === undefined || isNaN(Number(value))) return "0";
    return Number(value).toLocaleString("es-CO", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
    });
}

/**
 * Calculates the percentage delta between current and previous values.
 * Returns null if previous is 0, null, or undefined (can't calculate).
 */
export function calcDelta(current, prev) {
    const c = Number(current);
    const p = Number(prev);
    if (!p || isNaN(c) || isNaN(p)) return null;
    return ((c - p) / Math.abs(p)) * 100;
}

/**
 * Paleta de colores compartida por todas las gráficas del tablero
 * (misma familia que ya usan el KpiBanner y el acordeón de sedes).
 */
export const CHART_COLORS = [
    "#1A3C6B", "#7FB342", "#C0392B", "#0D6EFD",
    "#9C27B0", "#F39C12", "#17A2B8", "#8D6E63",
];

/** "$ 1.234.567" — formato monetario colombiano usado en tooltips/ejes. */
export function formatCOP(value) {
    return "$ " + formatCurrency(value, 0);
}

/**
 * Callback de Chart.js para truncar etiquetas largas en los ejes (nombres
 * de asesor/cliente/producto) sin afectar el tooltip -Chart.js muestra el
 * título del tooltip a partir de `data.labels` original, no del texto
 * truncado que dibuja el eje-. Uso: `ticks: { callback: tickTruncate(22) }`.
 */
export function tickTruncate(maxLen = 22) {
    return function (value) {
        const label = this.getLabelForValue ? this.getLabelForValue(value) : value;
        if (typeof label !== "string" || label.length <= maxLen) return label;
        return label.slice(0, maxLen - 1) + "…";
    };
}

/** Opciones base de Chart.js: leyenda, tooltip en COP, sin animación larga. */
export function baseChartOptions(overrides = {}) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 250 },
        plugins: {
            legend: { display: true, labels: { boxWidth: 12, font: { size: 11 } } },
            tooltip: {
                callbacks: {
                    label(ctx) {
                        const raw = ctx.parsed.y ?? ctx.parsed.x ?? ctx.parsed;
                        const label = ctx.dataset.label ? ctx.dataset.label + ": " : "";
                        return label + formatCOP(raw);
                    },
                },
            },
            ...(overrides.plugins || {}),
        },
        ...overrides,
    };
}
