# -*- coding: utf-8 -*-
from odoo import api, fields, models, _  #type: ignore
from odoo.exceptions import UserError  #type: ignore


class PartnerMergeProposalLine(models.Model):
    _name = "partner.merge.proposal.line"
    _description = "Contacto candidato dentro de una propuesta de fusion"
    _order = "id"

    proposal_id = fields.Many2one(
        "partner.merge.proposal", string="Propuesta", required=True,
        ondelete="cascade", index=True,
    )
    partner_id = fields.Many2one(
        "res.partner", string="Contacto", ondelete="set null",
        help="Puede quedar vacio despues de la fusion: el contacto origen se elimina. "
             "Los campos snapshot conservan su informacion.",
    )
    original_partner_id = fields.Integer(
        string="ID original del contacto", readonly=True,
        help="Se conserva aunque el contacto sea eliminado por la fusion.",
    )
    role = fields.Selection([
        ("candidate", "Candidato"),
        ("destination", "Destino sugerido"),
        ("related_child", "Hijo relacionado (no se fusiona)"),
    ], required=True, default="candidate")

    snapshot_name = fields.Char(string="Nombre (snapshot)")
    snapshot_vat = fields.Char(string="VAT (snapshot)")
    snapshot_email = fields.Char(string="Email (snapshot)")
    snapshot_phone = fields.Char(string="Telefono (snapshot)")
    snapshot_city = fields.Char(string="Ciudad (snapshot)")
    snapshot_company_id = fields.Many2one("res.company", string="Compania (snapshot)")
    snapshot_parent_id = fields.Integer(string="ID padre (snapshot)")
    snapshot_user_logins = fields.Char(string="Usuarios vinculados (snapshot)")
    snapshot_write_date = fields.Datetime(string="Ultima modificacion (snapshot)")

    is_company_partner = fields.Boolean(
        string="Es partner base de compania",
        help="True si este contacto es el res.company.partner_id de alguna compania.",
    )
    has_dian_validated_invoice = fields.Boolean(
        string="Tiene factura DIAN validada",
    )
    is_archived = fields.Boolean(
        string="Archivado",
        help="Estado del contacto (activo/archivado) al momento del ultimo snapshot.",
    )
    still_exists = fields.Boolean(
        string="El contacto aun existe", compute="_compute_still_exists",
    )

    @api.depends("original_partner_id")
    def _compute_still_exists(self):
        Partner = self.env["res.partner"]
        for line in self:
            line.still_exists = bool(
                line.original_partner_id and Partner.browse(line.original_partner_id).exists()
            )

    def write(self, vals):
        if vals.get("role") == "destination":
            for line in self:
                if line.proposal_id.state != "pending":
                    raise UserError(_(
                        "Solo se puede cambiar el contacto destino mientras la propuesta esta pendiente."
                    ))
        res = super().write(vals)
        if vals.get("role") == "destination":
            for line in self:
                siblings = line.proposal_id.line_ids - line
                to_demote = siblings.filtered(lambda l: l.role == "destination")
                if to_demote:
                    to_demote.write({"role": "candidate"})
        return res
