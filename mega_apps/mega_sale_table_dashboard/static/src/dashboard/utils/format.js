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
