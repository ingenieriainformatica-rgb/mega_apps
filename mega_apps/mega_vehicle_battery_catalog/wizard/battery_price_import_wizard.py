import base64
import csv
import io
import logging
import re
import unicodedata

from odoo import models, _ , fields # type: ignore
from odoo.exceptions import UserError  # type: ignore

_logger = logging.getLogger(__name__)


class MegaBatteryPriceImportWizard(models.TransientModel):
    _name = "mega.battery.price.import.wizard"
    _description = "Importar precios de baterías MAC"

    file = fields.Binary(
        string="Archivo",
        required=True,
    )

    filename = fields.Char(
        string="Nombre del archivo",
    )

    update_description = fields.Boolean(
        string="Actualizar descripción",
        default=True,
    )

    update_stock = fields.Boolean(
        string="Actualizar existencias",
        default=True,
    )

    update_prices = fields.Boolean(
        string="Actualizar precios",
        default=True,
    )

    summary = fields.Text(
        string="Resumen",
        readonly=True,
    )

    def action_import_prices(self):
        self.ensure_one()

        rows = self._read_file()
        if not rows:
            raise UserError(_("El archivo no contiene filas para importar."))

        Option = self.env["mega.battery.application.option"].sudo()
        currency = self.env.company.currency_id

        total_rows = 0
        updated_references = 0
        updated_options = 0
        not_found = 0
        skipped = 0

        updated_option_ids = []
        not_found_refs = []

        for row_number, row in rows:
            total_rows += 1

            description = self._get_value(row, ["descripcion", "description"])
            reference = self._extract_reference(description)

            if not reference:
                skipped += 1
                continue

            options = Option.search([
                ("reference", "=ilike", reference),
            ])

            if not options:
                not_found += 1
                not_found_refs.append(reference)
                continue

            vals = {
                "currency_id": currency.id,
            }

            if self.update_description:
                vals.update({
                    "description": description,
                    "uom_name": self._get_value(row, ["um", "unidad", "u_m"]),
                })

            if self.update_stock:
                vals.update({
                    "stock_qty": self._parse_number(
                        self._get_value(row, ["existencias", "stock"])
                    ),
                })

            if self.update_prices:
                average_cost = self._parse_money(
                    self._get_value(row, ["promedio"])
                )

                tax_amount = self._parse_money(
                    self._get_value(row, ["iva"])
                )

                cost_with_tax = self._parse_money(
                    self._get_value(row, [
                        "costo_iva",
                        "costo_mas_iva",
                        "costo_con_iva",
                        "costo_iva_moneda",
                        "costo_total",
                    ])
                )

                sale_price_from_file = self._get_sale_price_from_file(row)
                sale_price = self._calculate_sale_price(
                    cost_with_tax=cost_with_tax,
                    sale_price_from_file=sale_price_from_file,
                )

                vals.update({
                    "average_cost": average_cost,
                    "tax_amount": tax_amount,
                    "cost_with_tax": cost_with_tax,
                    "sale_price": sale_price,
                })

                _logger.info(
                    "[MAC Price Import] Fila %s | Ref %s | Promedio=%s | IVA=%s | "
                    "Costo+IVA=%s | Venta archivo=%s | Venta final=%s | Columnas=%s",
                    row_number,
                    reference,
                    average_cost,
                    tax_amount,
                    cost_with_tax,
                    sale_price_from_file,
                    sale_price,
                    sorted(row.keys()),
                )

            options.write(vals)

            updated_references += 1
            updated_options += len(options)
            updated_option_ids.extend(options.ids)

            _logger.info(
                "[MAC Price Import] Ref %s actualizada en %s opciones.",
                reference,
                len(options),
            )

        not_found_refs = sorted(set(not_found_refs))

        self.summary = _(
            "Importación de precios finalizada.\n\n"
            "Filas leídas: %(total_rows)s\n"
            "Referencias actualizadas: %(updated_references)s\n"
            "Opciones actualizadas: %(updated_options)s\n"
            "Referencias no encontradas: %(not_found)s\n"
            "Filas omitidas: %(skipped)s\n\n"
            "No encontradas:\n%(not_found_refs)s"
        ) % {
            "total_rows": total_rows,
            "updated_references": updated_references,
            "updated_options": updated_options,
            "not_found": not_found,
            "skipped": skipped,
            "not_found_refs": "\n".join(not_found_refs[:80]),
        }

        if updated_options:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Importación finalizada"),
                    "message": _(
                        "Importación terminada correctamente.\n"
                        "Filas leídas: %(total_rows)s\n"
                        "Referencias actualizadas: %(updated_references)s\n"
                        "Opciones actualizadas: %(updated_options)s\n"
                        "Referencias no encontradas: %(not_found)s\n"
                        "Filas omitidas: %(skipped)s"
                    ) % {
                        "total_rows": total_rows,
                        "updated_references": updated_references,
                        "updated_options": updated_options,
                        "not_found": not_found,
                        "skipped": skipped,
                    },
                    "type": "success",
                    "sticky": False,
                    "next": {
                        "type": "ir.actions.act_window_close",
                    },
                },
            }

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Importación de precios"),
                "message": _(
                    "No se actualizó ninguna referencia.\n"
                    "Filas leídas: %(total_rows)s\n"
                    "Referencias no encontradas: %(not_found)s\n"
                    "Filas omitidas: %(skipped)s"
                ) % {
                    "total_rows": total_rows,
                    "not_found": not_found,
                    "skipped": skipped,
                },
                "type": "warning",
                "sticky": True,
                "next": {
                    "type": "ir.actions.act_window_close",
                },
            },
        }

    # ============================================================
    # Lectura de archivo
    # ============================================================

    def _read_file(self):
        self.ensure_one()

        file_content = base64.b64decode(self.file or b"")
        filename = (self.filename or "").lower()

        if filename.endswith(".xlsx"):
            return self._read_xlsx(file_content)

        if filename.endswith(".csv"):
            return self._read_csv(file_content)

        raise UserError(_("Formato no soportado. Usa archivo .xlsx o .csv."))

    def _read_xlsx(self, file_content):
        try:
            from openpyxl import load_workbook  # type: ignore
        except ImportError as exc:
            raise UserError(_(
                "Para importar XLSX debes instalar openpyxl en el entorno de Odoo."
            )) from exc

        workbook = load_workbook(
            filename=io.BytesIO(file_content),
            read_only=True,
            data_only=True,
        )

        sheet = workbook.worksheets[0]
        iterator = sheet.iter_rows(values_only=True)

        try:
            raw_headers = next(iterator)
        except StopIteration:
            return []

        headers = []
        for index, header in enumerate(raw_headers):
            normalized = self._normalize_header(header)
            headers.append(normalized or f"column_{index}")

        rows = []
        for row_number, raw_row in enumerate(iterator, start=2):
            row = {}

            for index, value in enumerate(raw_row):
                if index >= len(headers):
                    continue

                row[headers[index]] = self._cell_to_str(value)

            if any(row.values()):
                rows.append((row_number, row))

        return rows

    def _read_csv(self, file_content):
        text = None

        for encoding in ("utf-8-sig", "latin-1"):
            try:
                text = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            raise UserError(_("No fue posible leer el CSV. Revisa la codificación."))

        sample = text[:4096]

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=";,")
        except csv.Error:
            dialect = csv.excel

        reader = csv.DictReader(io.StringIO(text), dialect=dialect)

        headers = {
            original: self._normalize_header(original)
            for original in reader.fieldnames or []
        }

        rows = []
        for row_number, raw_row in enumerate(reader, start=2):
            row = {}

            for original_key, value in raw_row.items():
                normalized_key = headers.get(original_key)
                if normalized_key:
                    row[normalized_key] = self._cell_to_str(value)

            if any(row.values()):
                rows.append((row_number, row))

        return rows

    # ============================================================
    # Precios
    # ============================================================

    def _get_sale_price_from_file(self, row):
        """
        Intenta tomar el precio de venta directamente del archivo.

        Primero busca nombres exactos normalizados.
        Luego hace una búsqueda flexible por columnas que parezcan precio de venta.
        """

        exact_keys = [
            "30",
            "30_",
            "30_porcentaje",
            "precio_venta",
            "precio_de_venta",
            "precio_publico",
            "precio_al_publico",
            "venta",
            "pvp",
            "valor_venta",
            "precio",
        ]

        value = self._get_value(row, exact_keys)
        parsed_value = self._parse_money(value)

        if parsed_value:
            return parsed_value

        excluded_words = [
            "costo",
            "iva",
            "promedio",
            "existencia",
            "stock",
            "descripcion",
            "description",
            "unidad",
            "um",
            "u_m",
        ]

        included_words = [
            "venta",
            "publico",
            "pvp",
            "precio",
            "30",
        ]

        for key, raw_value in row.items():
            if not raw_value:
                continue

            normalized_key = self._normalize_header(key)

            if any(word in normalized_key for word in excluded_words):
                continue

            if any(word in normalized_key for word in included_words):
                parsed_value = self._parse_money(raw_value)
                if parsed_value:
                    return parsed_value

        return 0.0

    def _calculate_sale_price(self, cost_with_tax, sale_price_from_file):
        """
        Si el archivo trae precio de venta, se respeta.

        Si no lo trae o no se puede leer, se calcula como margen del 30%:
        Precio venta = Costo con IVA / 0.70

        Ejemplo:
        294.983,42 / 0.70 = 421.404,88
        Redondeado = 421.405
        """

        if sale_price_from_file:
            return sale_price_from_file

        if not cost_with_tax:
            return 0.0

        return round(cost_with_tax / 0.70, 0)

    # ============================================================
    # Utilidades
    # ============================================================

    def _extract_reference(self, description):
        description = self._cell_to_str(description)

        if not description:
            return ""

        match = re.search(r"^\s*([A-Za-z0-9\-]+)", description)
        if not match:
            return ""

        return match.group(1).strip().upper()

    def _get_value(self, row, keys):
        for key in keys:
            value = row.get(key)
            if value not in (None, ""):
                return self._cell_to_str(value)

        return ""

    def _parse_number(self, value):
        return self._parse_money(value)

    def _parse_money(self, value):
        value = self._cell_to_str(value)

        if not value:
            return 0.0

        value = value.replace("$", "")
        value = value.replace("COP", "")
        value = value.replace(" ", "")
        value = value.strip()

        # Formato colombiano: 374.739,72
        if "," in value:
            value = value.replace(".", "")
            value = value.replace(",", ".")
        else:
            # Formato miles: 421.405 => 421405
            parts = value.split(".")
            if len(parts) > 1 and len(parts[-1]) == 3:
                value = value.replace(".", "")

        try:
            return float(value)
        except ValueError:
            return 0.0

    def _cell_to_str(self, value):
        if value is None:
            return ""

        if isinstance(value, float) and value.is_integer():
            return str(int(value))

        return str(value).strip()

    def _normalize_header(self, value):
        value = self._cell_to_str(value)
        value = self._strip_accents(value)
        value = value.lower()
        value = value.replace("%", "")
        value = value.replace("+", " mas ")
        value = re.sub(r"[^a-z0-9]+", "_", value)
        value = re.sub(r"_+", "_", value)

        return value.strip("_")

    def _strip_accents(self, value):
        value = self._cell_to_str(value)

        return "".join(
            char
            for char in unicodedata.normalize("NFKD", value)
            if not unicodedata.combining(char)
        )
