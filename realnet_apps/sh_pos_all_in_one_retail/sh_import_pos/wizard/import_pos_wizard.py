# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, _
from odoo.exceptions import UserError
import datetime
import csv
import base64
import xlrd
import pytz
from odoo.tools import ustr
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class ImportPosWizard(models.TransientModel):
    _name = "import.pos.wizard"
    _description = "Import POS Order Wizard"

    import_type = fields.Selection([
        ('csv', 'CSV File'),
        ('excel', 'Excel File')
    ], default="csv", string="Import File Type", required=True)
    file = fields.Binary(string="File", required=True)
    product_by = fields.Selection([
        ('name', 'Name'),
        ('int_ref', 'Internal Reference'),
        ('barcode', 'Barcode')
    ], default="name", string="Product By", required=True)
    is_create_customer = fields.Boolean(string="Create Customer?")
    order_no_type = fields.Selection([
        ('auto', 'Auto'),
        ('as_per_sheet', 'As per sheet')
    ], default="auto", string="POS Order Number", required=True)
    sh_partner_by = fields.Selection([
        ('name', 'Name'),
        ('ref', 'Reference'),
        ('id', 'ID')
    ], default="name", string="Customer By")

    def show_success_msg(self, counter, confirm_rec, skipped_line_no):

        # to close the current active wizard
        # action = self.env.ref('sh_import_pos.sh_import_pos_action').read()[0]
        # action = {'type': 'ir.actions.act_window_close'}

        # open the new success message box
        view = self.env.ref('sh_pos_all_in_one_retail.sh_message_wizard')
        # view_id = view and view.id or False
        context = dict(self._context or {})
        dic_msg = str(counter) + " Records imported successfully \n"
        dic_msg = dic_msg + str(confirm_rec) + " Records Confirm"
        if skipped_line_no:
            dic_msg = dic_msg + "\nNote:"
        for k, v in skipped_line_no.items():
            dic_msg = dic_msg + "\nRow No " + k + " " + v + " "
        context['message'] = dic_msg

        return {
            'name': 'Success',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.message.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context,
        }

    def read_xls_book(self):
        book = xlrd.open_workbook(file_contents=base64.decodebytes(self.file))
        sheet = book.sheet_by_index(0)
        # emulate Sheet.get_rows for pre-0.9.4
        values_sheet = []
        for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
            values = []
            for colx, cell in enumerate(row, 1):
                if cell.ctype is xlrd.XL_CELL_NUMBER:
                    is_float = cell.value % 1 != 0.0
                    values.append(
                        str(cell.value) if is_float else str(int(cell.value)))
                elif cell.ctype is xlrd.XL_CELL_DATE:
                    is_datetime = cell.value % 1 != 0.0
                    # emulate xldate_as_datetime for pre-0.9.3
                    dt = datetime.datetime(*xlrd.xldate.xldate_as_tuple(
                        cell.value, book.datemode))
                    values.append(
                        dt.strftime(DEFAULT_SERVER_DATETIME_FORMAT
                                    ) if is_datetime else dt.
                        strftime(DEFAULT_SERVER_DATE_FORMAT))
                elif cell.ctype is xlrd.XL_CELL_BOOLEAN:
                    values.append('True' if cell.value else 'False')
                elif cell.ctype is xlrd.XL_CELL_ERROR:
                    raise ValueError(
                        _("Invalid cell value at row %(row)s, column %(col)s: %(cell_value)s"
                          ) % {
                              'row':
                              rowx,
                              'col':
                              colx,
                              'cell_value':
                              xlrd.error_text_from_code.get(
                                  cell.value,
                                  _("unknown error code %s") % cell.value)
                        })
                else:
                    values.append(cell.value)
            values_sheet.append(values)
        return values_sheet

    def import_pos_apply(self):
        pos_line_obj = self.env['pos.order.line']
        pos_order_obj = self.env['pos.order']
        
        if self and self.file:
            if self.import_type in ('csv', 'excel'):
                for rec in self:
                    counter = 1
                    skipped_line_no = {}
                    
                    try:
                        values = []
                        created_pos_list_for_confirm = []
                        created_pos_list = []
                        pos_order_dict = {}  # Dictionary to group orders by unique key
                        
                        if self.import_type == 'csv':
                            file = str(base64.decodebytes(self.file).decode('utf-8'))
                            values = csv.reader(file.splitlines())
                            skip_header = True
                        elif self.import_type == 'excel':
                            values = self.read_xls_book()
                            skip_header = True

                        for row in values:
                            try:
                                if skip_header:
                                    skip_header = False
                                    counter += 1
                                    continue

                                if row[0] not in (None, "") and row[5] not in (None, ""):
                                    vals = {}

                                    # Create unique key based on pos, session name, customer, user, and order date
                                    pos_key = (row[0], row[1], row[2], row[4], row[3])

                                    if pos_key in pos_order_dict:
                                        # Use existing POS order if key matches
                                        pos_order = pos_order_dict[pos_key]
                                    else:
                                        # Create a new POS order
                                        pos_vals = {}

                                        # Session
                                        if row[1]:
                                            search_session = self.env['pos.session'].search([('name', '=', row[1])], limit=1)
                                            if search_session:
                                                pos_vals['session_id'] = search_session.id
                                            else:
                                                skipped_line_no[str(counter)] = " - Session not found."
                                                counter += 1
                                                continue

                                        # Customer
                                        if row[2]:
                                            partner_obj = self.env["res.partner"]
                                            domain = []
                                            
                                            if self.sh_partner_by == 'name':
                                                domain.append(('name', '=', row[2]))
                                            elif self.sh_partner_by == 'ref':
                                                domain.append(('ref', '=', row[2]))
                                            elif self.sh_partner_by == 'id':
                                                domain.append(('id', '=', row[2]))

                                            partner = partner_obj.search(domain, limit=1)

                                            if partner:
                                                pos_vals['partner_id'] = partner.id
                                            elif rec.is_create_customer:
                                                partner = partner_obj.create({'company_type': 'person', 'name': row[2]})
                                                pos_vals['partner_id'] = partner.id if partner else False
                                            else:
                                                pos_vals['partner_id'] = False
                                        else:
                                            pos_vals['partner_id'] = False

                                        # Order date
                                        if row[3]:
                                            user_tz = pytz.timezone(self.env.user.tz or self.env.context.get('tz') or 'UTC')
                                            dt = user_tz.localize(fields.Datetime.from_string(row[3])).astimezone(pytz.timezone('UTC'))
                                            pos_vals['date_order'] = fields.Datetime.to_string(dt)

                                        # User
                                        if row[4]:
                                            search_user = self.env['res.users'].search([('name', '=', row[4])], limit=1)
                                            if search_user:
                                                pos_vals['user_id'] = search_user.id
                                            else:
                                                skipped_line_no[str(counter)] = " - User not found."
                                                counter += 1
                                                continue

                                        pos_vals.update({
                                            'amount_tax': 0.0,
                                            'amount_total': 0.0,
                                            'amount_paid': 0.0,
                                            'amount_return': 0.0
                                        })

                                        if rec.order_no_type == 'as_per_sheet':
                                            pos_vals['name'] = row[0]

                                        pos_order = pos_order_obj.create(pos_vals)
                                        pos_order_dict[pos_key] = pos_order
                                        created_pos_list_for_confirm.append(pos_order.id)
                                        created_pos_list.append(pos_order.id)

                                    # Add order line
                                    field_nm = 'name'
                                    if rec.product_by == 'int_ref':
                                        field_nm = 'default_code'
                                    elif rec.product_by == 'barcode':
                                        field_nm = 'barcode'

                                    search_product = self.env['product.product'].search([(field_nm, '=', row[5])], limit=1)

                                    if search_product:
                                        vals.update({
                                            'product_id': search_product.id,
                                            'full_product_name': search_product.display_name,
                                            'order_id': pos_order.id
                                        })

                                        vals['name'] = row[6] if row[6] else ''
                                        vals['qty'] = float(row[7]) if row[7] else 1.0

                                        # UoM
                                        if row[8]:
                                            search_uom = self.env['uom.uom'].search([('name', '=', row[8])], limit=1)
                                            vals['product_uom_id'] = search_uom.id if search_uom else search_product.uom_id.id
                                        else:
                                            vals['product_uom_id'] = search_product.uom_id.id

                                        # Price
                                        vals['price_unit'] = float(row[9]) if row[9] else search_product.lst_price

                                        # Taxes
                                        taxes_list = []
                                        if row[10]:
                                            for tax_name in row[10].split(','):
                                                tax_name = tax_name.strip()
                                                search_tax = self.env['account.tax'].search([('name', '=', tax_name)], limit=1)
                                                if search_tax:
                                                    taxes_list.append(search_tax.id)
                                                else:
                                                    skipped_line_no[str(counter)] = f" - Tax {tax_name} not found."
                                                    continue
                                        
                                        vals['tax_ids'] = [(6, 0, taxes_list)]

                                        # Subtotal calculation
                                        price_subtotal = vals['price_unit'] * vals['qty']
                                        price_subtotal_incl = price_subtotal
                                        
                                        if vals.get('tax_ids'):
                                            tax_obj = self.env['account.tax'].browse(vals['tax_ids'][0][2])
                                            compute_tax = tax_obj.compute_all(vals['price_unit'], product=search_product.product_tmpl_id)
                                            price_subtotal = compute_tax['total_excluded'] * vals['qty']
                                            price_subtotal_incl = compute_tax['total_included'] * vals['qty']

                                        vals.update({
                                            'price_subtotal': price_subtotal,
                                            'price_subtotal_incl': price_subtotal_incl
                                        })

                                        # Create order line
                                        line = pos_line_obj.create(vals)

                                        # Recompute order totals
                                        pos_order._compute_prices()
                                        pos_order._onchange_amount_all()

                                        counter += 1

                                    else:
                                        skipped_line_no[str(counter)] = " - Product not found."
                                        counter += 1
                                        continue

                            except Exception as e:
                                skipped_line_no[str(counter)] = f" - Error: {ustr(e)}"
                                counter += 1
                                continue

                    except Exception as e:
                        raise UserError(_("Error during import: ") + ustr(e))

                    if counter > 1:
                        completed_records = len(created_pos_list)
                        confirm_rec = len(created_pos_list_for_confirm)
                        res = self.show_success_msg(completed_records, confirm_rec, skipped_line_no)
                        return res
