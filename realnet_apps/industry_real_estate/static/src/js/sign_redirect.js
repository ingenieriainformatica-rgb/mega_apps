/** @odoo-module **/

// ===== Destinos por contexto =====
const ACTIONS = {
    rental: "/odoo/action-871",  // Contratos de alquiler
    owner:  "/odoo/action-872",  // Contratos de administración / propietario
    home:   "/odoo/action-873",  // Inicio del módulo (fallback sin contexto)
};

// ===== Flags / storage keys =====
const FLAG_DONE    = "ire_sign_redirect_done";
const FLAG_PENDING = "ire_sign_redirect_pending";
const SCOPE_KEY    = "ire_scope";  // 'rental' | 'owner' | null

// ===== Regex robustos (pathname y hash) =====
const RX_ACT_829_PATH = /\/action-871(?:\/|$)/i;         // /odoo/action-829  o  /odoo/action-829/52
const RX_ACT_830_PATH = /\/action-872(?:\/|$)/i;         // /odoo/action-830  o  /odoo/action-830/77
const RX_ACT_829_HASH = /(^|[?&#])action-871(?!\d)/i;    // #...action=829&...
const RX_ACT_830_HASH = /(^|[?&#])action-872(?!\d)/i;    // #...action=830&...

function pPath() { return (location.pathname || "").toLowerCase(); }
function pHash() { return (location.hash || "").toLowerCase(); }
function pFull() { return (location.pathname + location.search).toLowerCase(); }

// === Detecta y guarda scope mirando pathname y hash ===
function detectScopeFromLocation() {
    const path = pPath(), hash = pHash(), full = pFull();

    if (RX_ACT_829_PATH.test(full) || RX_ACT_829_HASH.test(hash)) {
        sessionStorage.setItem(SCOPE_KEY, "rental");
        return "rental";
    }
    if (RX_ACT_830_PATH.test(full) || RX_ACT_830_HASH.test(hash)) {
        sessionStorage.setItem(SCOPE_KEY, "owner");
        return "owner";
    }
    return sessionStorage.getItem(SCOPE_KEY) || null;
}

// === ¿Estamos en Sign standalone (sin venir de 829/830)? ===
function isStandaloneSign() {
    const path = pPath(), hash = pHash(), full = pFull();
    const inSign = path.includes("/sign"); // /odoo/sign, /odoo/sign/xyz, /odoo/sign-documents
    const hasActionScope =
        RX_ACT_829_PATH.test(full) || RX_ACT_830_PATH.test(full) ||
        RX_ACT_829_HASH.test(hash) || RX_ACT_830_HASH.test(hash);
    return inSign && !hasActionScope;
}

// === Limpiar scope/banderas si estamos en Sign standalone y no hay redirect pendiente ===
function clearScopeIfStandaloneSign() {
    if (isStandaloneSign() && sessionStorage.getItem(FLAG_PENDING) !== "1") {
        // Esta navegación a Sign no viene “atada” a un contrato: resetea.
        sessionStorage.removeItem(SCOPE_KEY);
        sessionStorage.removeItem(FLAG_DONE);
    }
}

// === Resolver destino final según scope guardado ===
function resolveDest() {
    const scope = sessionStorage.getItem(SCOPE_KEY);
    if (scope === "rental") return ACTIONS.rental;
    if (scope === "owner")  return ACTIONS.owner;
    return ACTIONS.home;
}

// === 1) Captura scope fuera de /sign + limpia si es Sign standalone ===
(function installScopeCapturers() {
    if (window.__ire_scope_capturers_installed__) return;
    window.__ire_scope_capturers_installed__ = true;

    // Primer pase: detecta scope o limpia si ya estás en Sign standalone
    if (!pPath().includes("/sign")) {
        detectScopeFromLocation();
    } else {
        clearScopeIfStandaloneSign();
    }

    // Cambios de hash: Odoo suele re-navegar con hash
    window.addEventListener("hashchange", () => {
        if (!pPath().includes("/sign")) {
            detectScopeFromLocation();
        } else {
            clearScopeIfStandaloneSign();
        }
    });

    // También en pageshow/popstate
    window.addEventListener("pageshow", clearScopeIfStandaloneSign);
    window.addEventListener("popstate", clearScopeIfStandaloneSign);

    // Poll suave por 2s (por si el hash entra tarde)
    const t0 = Date.now();
    const poll = setInterval(() => {
        if (!pPath().includes("/sign")) {
            detectScopeFromLocation();
        } else {
            clearScopeIfStandaloneSign();
        }
        if (Date.now() - t0 > 2000) clearInterval(poll);
    }, 150);
})();

// === 2) Antes de ir a Sign desde botones/enlaces: guarda scope SI estás en contratos, o limpia si vas al app Sign ===
(function interceptOpenClicks() {
    if (window.__ire_sign_click_hook_installed__) return;
    window.__ire_sign_click_hook_installed__ = true;

    document.addEventListener("click", (ev) => {
        const el = ev.target && ev.target.closest("a, button, .btn, .o_button, .o_app");
        if (!el) return;

        const href = (el.getAttribute("href") || "").toLowerCase();
        const cls  = (el.className || "").toLowerCase();
        const txt  = (el.innerText || "").toLowerCase().trim();

        // 2.a) Si el click abre el app Sign directamente, limpia scope ANTES
        const navToSignApp = href.includes("/odoo/sign") || cls.includes("o_app") && (txt.includes("sign") || txt.includes("firmas"));
        if (navToSignApp) {
            sessionStorage.removeItem(SCOPE_KEY);
            sessionStorage.removeItem(FLAG_DONE);
            return;
        }

        // 2.b) Si parece que abre flujo de firma desde contrato, guarda scope ANTES
        const looksLikeSign =
            cls.includes("o_sign_") || cls.includes("o_button_sign") ||
            txt.includes("solicitar firma") || txt.includes("firmar ahora") || txt === "firmar" || txt.includes("enviar para firma");

        if (looksLikeSign) {
            detectScopeFromLocation(); // memoriza rental/owner si estás en 829/830
        }
    }, true);
})();

// === 3) Guard global: si estás en /sign* y hay redirección pendiente, volver al destino correcto ===
(function installGlobalGuard() {
    if (window.__ire_guard_installed__) return;
    window.__ire_guard_installed__ = true;

    const mustRedirectNow = () => {
        const p = pPath();
        return (p.includes("/sign") || p.includes("/sign-")) && sessionStorage.getItem(FLAG_PENDING) === "1";
    };

    const force = () => {
        const dest = resolveDest();
        console.log("[IRE] Guard: forzando redirección a", dest);
        sessionStorage.setItem(FLAG_DONE, "1");
        sessionStorage.removeItem(FLAG_PENDING);
        window.top.location.replace(dest);
    };

    if (mustRedirectNow()) force();
    window.addEventListener("popstate",  () => { if (mustRedirectNow()) force(); });
    window.addEventListener("pageshow",  () => { if (mustRedirectNow()) force(); });
    document.addEventListener("odoo:systray_menu_opened", () => { if (mustRedirectNow()) force(); }, true);
})();

// === 4) Botón “Cerrar” del diálogo “Está firmado” ===
(function installThankYouCloseHook() {
    if (window.__ire_sign_redirect_installed__) return;
    window.__ire_sign_redirect_installed__ = true;

    document.addEventListener("click", (ev) => {
        const btn = ev.target && ev.target.closest(".o_sign_thankyou_close_button");
        if (!btn) return;

        // Si ya redirigimos, no repitas
        if (sessionStorage.getItem(FLAG_DONE) === "1") return;

        // Marca redirección pendiente y bloquea el click nativo
        sessionStorage.setItem(FLAG_PENDING, "1");
        ev.preventDefault();
        ev.stopImmediatePropagation();

        const dest = resolveDest();

        // Watchdog: si el router nos lleva a listados de sign, forzar
        const t0 = Date.now();
        const watchdog = setInterval(() => {
            const tooLong = Date.now() - t0 > 2000;
            const p = pPath();
            const gotListed = p.includes("/sign-documents") || p.endsWith("/sign");
            if (tooLong || gotListed) {
                clearInterval(watchdog);
                console.log("[IRE] Watchdog: redirigiendo a", dest);
                sessionStorage.setItem(FLAG_DONE, "1");
                sessionStorage.removeItem(FLAG_PENDING);
                window.top.location.replace(dest);
            }
        }, 120);

        console.log("[IRE] Click Cerrar detectado. Redirigiendo a", dest);
        window.top.location.replace(dest);
    }, true);
})();
