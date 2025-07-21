# -*- coding: utf-8 -*-

# from odoo import models, fields, api


# class elearning_advance_search(models.Model):
#     _name = 'elearning_advance_search.elearning_advance_search'
#     _description = 'elearning_advance_search.elearning_advance_search'

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         for record in self:
#             record.value2 = float(record.value) / 100

