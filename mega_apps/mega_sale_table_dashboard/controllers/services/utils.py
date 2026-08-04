import logging
from odoo.exceptions import AccessError  # type: ignore
from odoo.http import request  # type: ignore

JOURNAL_WH_FIELD = "warehouse_ids"
JOURNAL_TYPE = "sale"
WH_ACTIVE_FIELD = "show_in_sales_dashboard"
ALL_HEADQUARTERS = "allHeadquarters"
ALL_COMPANIES = "allCompanies"
ALL_TEAMS = "allTeams"


def state_domain(state_filter):
    """'posted' (default) reproduce el filtro histórico (solo documentos
    contabilizados). 'all' quita el filtro de estado. Cualquier otro valor
    filtra por ese estado puntual. Vive aquí (no en sales.py) para que
    tanto sales.py como analytics.py puedan importarlo sin crear un ciclo
    (sales.py ya importa analytics.py)."""
    if not state_filter or state_filter == "posted":
        return [("state", "not in", ("draft", "cancel"))]
    if state_filter == "all":
        return []
    return [("state", "=", state_filter)]

# Grupos habilitados para consultar el tablero. La agregación interna sigue
# usando sudo() (es un tablero gerencial que cruza sedes/diarios), pero sin
# este chequeo cualquier usuario interno autenticado -sin ningún rol de
# Ventas/Facturación- podía llamar las rutas JSON y obtener cifras de toda
# la compañía. Esto cierra ese hueco sin tocar el comportamiento para los
# usuarios que ya usan el tablero hoy.
_ALLOWED_GROUPS = (
    "sales_team.group_sale_salesman",
    "account.group_account_readonly",
    "account.group_account_invoice",
    "account.group_account_manager",
)

_logger = logging.getLogger(__name__)


def check_dashboard_access():
    """Lanza AccessError si el usuario no pertenece a ningún grupo de
    Ventas o Contabilidad/Facturación. Debe llamarse al inicio de cada
    ruta del controlador, antes de cualquier consulta sudo()."""
    user = request.env.user
    if user._is_admin():
        return
    if not any(user.has_group(g) for g in _ALLOWED_GROUPS):
        raise AccessError("No tienes permisos para consultar el tablero de ventas.")


def get_allowed_company_ids(company_id=None):
    """Compañías permitidas para el usuario actual (respeta allowed_company_ids).
    Si se pide una compañía puntual, la valida contra las permitidas."""
    allowed = request.env.companies.ids
    if company_id and company_id not in (None, "", ALL_COMPANIES):
        cid = int(company_id)
        return [cid] if cid in allowed else []
    return allowed


def get_sale_teams():
    """Equipos de venta (crm.team) realmente usados en facturas de venta
    de las compañías permitidas -evita listar equipos sin datos-."""
    Move = request.env["account.move"].sudo()
    rows = Move.read_group(
        domain=[
            ("company_id", "in", get_allowed_company_ids()),
            ("move_type", "in", ("out_invoice", "out_refund")),
            ("state", "=", "posted"),
            ("team_id", "!=", False),
        ],
        fields=["team_id"],
        groupby=["team_id"],
        lazy=False,
    )
    teams = [{"id": r["team_id"][0], "name": r["team_id"][1]} for r in rows if r.get("team_id")]
    teams.sort(key=lambda t: t["name"])
    return teams


def get_active_warehouses(warehouse_id=None, company_id=None):
    Warehouse = request.env["stock.warehouse"].sudo()
    company_ids = get_allowed_company_ids(company_id)

    domain = [
        ("company_id", "in", company_ids),
        ("show_in_sales_dashboard", "=", True),
    ]
    if warehouse_id:
        domain.append(("id", "=", int(warehouse_id)))

    warehouses = Warehouse.search(domain, order="name")

    # ✅ filtra: solo bodegas que tengan journals sale mapeados
    Journal = request.env["account.journal"].sudo()
    mapped_wh_ids = set(Journal.search([
        ("company_id", "in", company_ids),
        ("type", "=", "sale"),
        ("warehouse_ids", "!=", False),
    ]).mapped("warehouse_ids").ids)

    warehouses = warehouses.filtered(lambda w: w.id in mapped_wh_ids)
    return warehouses



def get_sale_journals(warehouse_id=None, company_id=None):
    Journal = request.env["account.journal"].sudo()
    Warehouse = request.env["stock.warehouse"].sudo()
    company_ids = get_allowed_company_ids(company_id)

    # 1) Warehouses activos (los que deben salir en dashboard)
    active_whs = Warehouse.search([
        ("company_id", "in", company_ids),
        (WH_ACTIVE_FIELD, "=", True),
    ])
    active_wh_ids = active_whs.ids

    domain = [
        ("company_id", "in", company_ids),
        ("type", "=", JOURNAL_TYPE),
        # 2) Solo journals que tengan relación con warehouses ACTIVOS
        (JOURNAL_WH_FIELD, "in", active_wh_ids),
    ]

    # 3) Si mandan sede específica, filtra por ese warehouse (siempre que no sea "Todos")
    if warehouse_id and warehouse_id != ALL_HEADQUARTERS:
        wid = int(warehouse_id)
        # si el warehouse no está activo, no debe traer nada
        if wid not in active_wh_ids:
            return Journal.browse([])  # vacío
        domain.append((JOURNAL_WH_FIELD, "in", [wid]))

    journals = Journal.search(domain, order="name")
    return journals


def get_advisors():
    """Contactos marcados como asesor (res.partner.is_advisor = True)."""
    Partner = request.env["res.partner"].sudo()
    return Partner.search([("is_advisor", "=", True)], order="name")


def get_allowed_companies():
    """Compañías permitidas del usuario actual (request.env.companies).
    El selector de 'Empresa' en el frontend solo debe mostrarse cuando
    esta lista tiene más de un elemento."""
    return request.env.companies.sorted("name")
