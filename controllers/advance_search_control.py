# controllers/advance_search_control.py
from odoo import http
from odoo.http import request

class SlideSearchController(http.Controller):

    @http.route('/slides/extended_search', type='json', auth='public', website=True)
    def extended_search(self, search='', **kwargs):
        Slide = request.env['slide.slide'].sudo()
        domain = ['|', ('name', 'ilike', search), ('description', 'ilike', search)]
        slides = Slide.search_read(domain, ['id', 'name', 'description'], limit=12)
        return {'slides': slides}
