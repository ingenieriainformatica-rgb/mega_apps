from odoo import api, fields, models


class MegaCajaLegalizacionMixin(models.AbstractModel):
    # Mixin reutilizable para que el futuro modulo de caja pueda heredar
    # exactamente la misma semantica de legalizacion en sus lineas reales.
    _name = "mega.caja.legalizacion.mixin"
    _description = "Mixin de legalizacion para movimientos de caja"

    requires_legalization = fields.Boolean(
        # Bandera funcional:
        # distingue gastos o movimientos que exigen soporte posterior.
        string="Requiere legalizacion",
        default=False,
        help="Indica si el movimiento necesita soporte administrativo.",
    )
    legalization_state = fields.Selection(
        # Estado administrativo del soporte.
        # No representa una nueva salida de caja; solo su situacion documental.
        selection=[
            ("not_applicable", "No aplica"),
            ("pending", "Pendiente por legalizar"),
            ("legalized", "Legalizado"),
        ],
        string="Estado de legalizacion",
        default="not_applicable",
        required=True,
    )
    legalized_at = fields.Datetime(
        # Fecha en la que se cierra la gestion documental.
        string="Fecha de legalizacion",
        readonly=True,
        copy=False,
    )
    support_attachment_count = fields.Integer(
        # Indicador rapido para saber si ya existen soportes adjuntos.
        string="Adjuntos",
        compute="_compute_support_attachment_count",
    )

    @api.depends()
    def _compute_support_attachment_count(self):
        # Cuenta adjuntos por res_model/res_id sin cargar cada attachment.
        # Esta misma logica podra servir luego para lineas reales de caja.
        if not self.ids:
            for record in self:
                record.support_attachment_count = 0
            return

        grouped = self.env["ir.attachment"].read_group(
            [
                ("res_model", "=", self._name),
                ("res_id", "in", self.ids),
            ],
            ["res_id"],
            ["res_id"],
        )
        counts = {
            item["res_id"]: item["res_id_count"]
            for item in grouped
            if item.get("res_id")
        }
        for record in self:
            record.support_attachment_count = counts.get(record.id, 0)

    @api.onchange("requires_legalization")
    def _onchange_requires_legalization(self):
        # Regla UX:
        # si un usuario marca "requiere legalizacion", el estado minimo util
        # pasa a "pendiente". Si se desmarca, el estado vuelve a "no aplica".
        for record in self:
            if record.requires_legalization and record.legalization_state == "not_applicable":
                record.legalization_state = "pending"
            elif not record.requires_legalization:
                record.legalization_state = "not_applicable"

    def action_mark_legalized(self):
        # Atajo de formulario para cerrar la gestion documental.
        self.write(
            {
                "legalization_state": "legalized",
                "legalized_at": fields.Datetime.now(),
            }
        )

    def action_mark_pending(self):
        # Permite reabrir un caso cuando el soporte aun no es valido o falta.
        self.write(
            {
                "legalization_state": "pending",
                "legalized_at": False,
            }
        )

    def action_mark_not_applicable(self):
        # Resetea el flujo documental cuando el movimiento finalmente
        # no requiere soporte administrativo.
        self.write(
            {
                "requires_legalization": False,
                "legalization_state": "not_applicable",
                "legalized_at": False,
            }
        )
