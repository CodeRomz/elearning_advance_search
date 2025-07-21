# -*- coding: utf-8 -*-
# from odoo import http


# class ElearningAdvanceSearch(http.Controller):
#     @http.route('/elearning_advance_search/elearning_advance_search', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/elearning_advance_search/elearning_advance_search/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('elearning_advance_search.listing', {
#             'root': '/elearning_advance_search/elearning_advance_search',
#             'objects': http.request.env['elearning_advance_search.elearning_advance_search'].search([]),
#         })

#     @http.route('/elearning_advance_search/elearning_advance_search/objects/<model("elearning_advance_search.elearning_advance_search"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('elearning_advance_search.object', {
#             'object': obj
#         })

