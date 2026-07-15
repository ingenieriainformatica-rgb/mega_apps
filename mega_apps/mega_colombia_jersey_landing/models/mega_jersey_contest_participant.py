import re
import secrets
import string

from psycopg2 import IntegrityError, sql  # type: ignore

from odoo import api, fields, models  # type: ignore
from odoo.exceptions import ValidationError  # type: ignore


DUPLICATE_PARTICIPANT_MESSAGE = (
    "Ya existe una inscripción registrada para esta cédula y esta placa."
)
LEGACY_VAT_CONSTRAINT = "mega_jersey_contest_participant_vat_normalized_uniq"
CODE_PREFIX = "MEGA-"
CODE_ALPHABET = "".join(
    ch for ch in string.ascii_uppercase + string.digits if ch not in "O0I1"
)


class MegaJerseyContestParticipant(models.Model):
    _name = "mega.jersey.contest.participant"
    _description = "Participante Concurso Camiseta Selección Colombia / Mega Eventos"
    _order = "create_date desc"

    name = fields.Char(string="Nombre completo", required=True)
    vat = fields.Char(string="Cédula", required=True)
    vat_normalized = fields.Char(
        string="Cédula normalizada",
        compute="_compute_vat_normalized",
        store=True,
        index=True,
        readonly=True,
    )
    phone = fields.Char(string="Número de celular", required=True)
    email = fields.Char(string="Correo electrónico", required=True)
    street = fields.Char(string="Dirección", required=True)
    license_plate = fields.Char(string="Placa", required=True)
    license_plate_normalized = fields.Char(
        string="Placa normalizada",
        compute="_compute_license_plate_normalized",
        store=True,
        index=True,
        readonly=True,
    )
    vehicle_info = fields.Char(string="Marca y modelo", required=True)
    service_acquired = fields.Selection(
        [
            ("baterias", "Baterías"),
            ("llantas", "Llantas"),
            ("mega_combo", "MegaCombo"),
            ("mecanica_especializada", "Mecánica especializada"),
            ("cambio_aceite", "Cambio de aceite"),
            ("trabajos_autorizados", "Trabajos autorizados"),
            ("revision_bateria", "Revisión de batería"),
        ],
        string="Servicio adquirido",
        required=True,
    )
    accept_data_policy = fields.Boolean(string="Autoriza tratamiento de datos", required=True)
    accept_commercial_info = fields.Boolean(string="Autoriza información comercial", required=True)
    website_id = fields.Many2one("website", string="Sitio web")
    ip_address = fields.Char(string="IP")
    user_agent = fields.Char(string="User Agent")
    state = fields.Selection(
        [
            ("new", "Nuevo"),
            ("processed", "Procesado"),
        ],
        default="new",
    )
    registration_source = fields.Selection(
        [
            ("jersey_contest", "Concurso Camiseta Selección"),
            ("mega_eventos", "Mega Eventos"),
        ],
        string="Origen de la inscripción",
        required=True,
        default="jersey_contest",
        index=True,
    )
    code = fields.Char(string="Código", readonly=True, copy=False, index=True)

    _sql_constraints = [
        (
            "code_uniq",
            "unique(code)",
            "Ya existe una inscripción con este código.",
        ),
    ]

    @api.depends("vat")
    def _compute_vat_normalized(self):
        for record in self:
            record.vat_normalized = self._normalize_vat(record.vat)

    @api.depends("license_plate")
    def _compute_license_plate_normalized(self):
        for record in self:
            record.license_plate_normalized = self._normalize_license_plate(
                record.license_plate
            )

    @api.model
    def _normalize_vat(self, vat):
        return re.sub(r"\D", "", vat or "")

    @api.model
    def _normalize_license_plate(self, license_plate):
        return re.sub(r"[^A-Z0-9]", "", (license_plate or "").upper())

    @api.model
    def _generate_unique_code(self):
        for _attempt in range(20):
            candidate = CODE_PREFIX + "".join(
                secrets.choice(CODE_ALPHABET) for _ in range(6)
            )
            if not self.sudo().search_count([("code", "=", candidate)]):
                return candidate
        raise ValidationError("No se pudo generar un código único, intenta de nuevo.")

    @api.model
    def _validate_participant_values(self, vals_list, existing_records=None):
        seen = {}
        existing_records = existing_records or self.browse()

        for index, vals in enumerate(vals_list):
            if "vat" not in vals and "license_plate" not in vals:
                continue

            existing_record = (
                existing_records[index]
                if len(existing_records) == len(vals_list)
                else self.browse()
            )
            vat = vals.get("vat", existing_record.vat)
            license_plate = vals.get("license_plate", existing_record.license_plate)
            registration_source = vals.get(
                "registration_source",
                existing_record.registration_source or "jersey_contest",
            )
            service_acquired = vals.get(
                "service_acquired", existing_record.service_acquired
            )

            vat_normalized = self._normalize_vat(vat)
            license_plate_normalized = self._normalize_license_plate(license_plate)
            if not vat_normalized:
                raise ValidationError("La cédula debe contener al menos un número.")
            if not license_plate_normalized:
                raise ValidationError("La placa debe contener al menos una letra o número.")

            participant_key = (
                registration_source,
                vat_normalized,
                license_plate_normalized,
                service_acquired,
            )
            if participant_key in seen:
                raise ValidationError(DUPLICATE_PARTICIPANT_MESSAGE)
            seen[participant_key] = index

            domain = [
                ("registration_source", "=", registration_source),
                ("vat_normalized", "=", vat_normalized),
                ("license_plate_normalized", "=", license_plate_normalized),
                ("service_acquired", "=", service_acquired),
            ]
            if existing_records:
                domain.append(("id", "not in", existing_records.ids))

            if self.sudo().search_count(domain):
                raise ValidationError(DUPLICATE_PARTICIPANT_MESSAGE)

    def init(self):
        constraint_names = [
            LEGACY_VAT_CONSTRAINT,
            "mega_jersey_contest_participant_vat_plate_normalized_uniq",
            "mega_jersey_contest_participant_mega_jersey_contest_pa_956edd3e",
        ]
        for constraint_name in constraint_names:
            self.env.cr.execute(
                sql.SQL("ALTER TABLE {} DROP CONSTRAINT IF EXISTS {}").format(
                    sql.Identifier(self._table),
                    sql.Identifier(constraint_name),
                )
            )
        self.env.cr.execute(
            """
            DO $$
            DECLARE
                unique_constraint_name text;
                unique_index_name text;
            BEGIN
                FOR unique_constraint_name IN
                    SELECT c.conname
                      FROM pg_constraint c
                      JOIN pg_class t ON t.oid = c.conrelid
                     WHERE t.relname = 'mega_jersey_contest_participant'
                       AND c.contype = 'u'
                       AND pg_get_constraintdef(c.oid) ILIKE '%vat_normalized%'
                       AND pg_get_constraintdef(c.oid) ILIKE '%license_plate_normalized%'
                LOOP
                    EXECUTE format(
                        'ALTER TABLE mega_jersey_contest_participant DROP CONSTRAINT IF EXISTS %I',
                        unique_constraint_name
                    );
                END LOOP;

                FOR unique_index_name IN
                    SELECT indexname
                      FROM pg_indexes
                     WHERE schemaname = current_schema()
                       AND tablename = 'mega_jersey_contest_participant'
                       AND indexdef ILIKE '%UNIQUE%'
                       AND indexdef ILIKE '%vat_normalized%'
                       AND indexdef ILIKE '%license_plate_normalized%'
                LOOP
                    EXECUTE format('DROP INDEX IF EXISTS %I', unique_index_name);
                END LOOP;
            END $$;
            """
        )

    @api.model_create_multi
    def create(self, vals_list):
        self._validate_participant_values(vals_list)
        for vals in vals_list:
            if not vals.get("code"):
                vals["code"] = self._generate_unique_code()
        try:
            return super().create(vals_list)
        except IntegrityError:
            self.env.cr.rollback()
            raise ValidationError(DUPLICATE_PARTICIPANT_MESSAGE)

    def write(self, vals):
        if "vat" in vals or "license_plate" in vals:
            self._validate_participant_values(
                [vals for _record in self],
                existing_records=self,
            )
        try:
            return super().write(vals)
        except IntegrityError:
            self.env.cr.rollback()
            raise ValidationError(DUPLICATE_PARTICIPANT_MESSAGE)

    @api.constrains("accept_data_policy", "accept_commercial_info")
    def _check_authorizations(self):
        for record in self:
            if not record.accept_data_policy:
                raise ValidationError("Debes autorizar el tratamiento de datos personales.")
            if not record.accept_commercial_info:
                raise ValidationError("Debes autorizar el envío de información comercial.")
