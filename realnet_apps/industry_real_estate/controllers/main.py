from odoo import http, models, fields
# from odoo.http import request

class ReceptionController(http.Controller):

    captured_image = fields.Image("Foto Recepción", max_width=1024, max_height=768)

    # @http.route('/reception/save_photo', type='json', auth='user')
    # def save_photo(self, res_id, image):
    #     record = request.env['rental.reception'].sudo().browse(res_id)
    #     record.write({'captured_image': image})
    #     return True
    