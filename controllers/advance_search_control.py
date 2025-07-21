"""
# File: slides_course_search_extension/controllers/advance_search_control.py
# Description: Enhanced search for /slides/all in Odoo 17 CE, following ORM and OWL standards.
"""

from odoo import http, tools, _
from odoo.http import request
from odoo.osv import expression
from odoo.addons.website_slides.controllers.main import WebsiteSlides

import logging
_logger = logging.getLogger(__name__)


class SlideSearchExtension(WebsiteSlides):

    def _extended_search_domain(self, search_term):
        """
        Build a search domain that includes:
        - Slide channel title, description
        - Slide title, html_content
        - Tag names (for both channels and slides)
        """
        try:
            domain_list = []

            # Search in course (channel) fields
            domain_list.append(('name', 'ilike', search_term))
            domain_list.append(('description', 'ilike', search_term))
            domain_list.append(('tag_ids.name', 'ilike', search_term))

            # Find slide.channel from slide.slide matching title/html/tags
            Slide = request.env['slide.slide'].sudo()
            slide_domain = expression.OR([
                ('name', 'ilike', search_term),
                ('html_content', 'ilike', search_term),
                ('tag_ids.name', 'ilike', search_term)
            ])

            matching_slides = Slide.search(expression.AND([
                slide_domain,
                ('is_published', '=', True)
            ]))

            matching_channel_ids = matching_slides.mapped('channel_id').ids
            if matching_channel_ids:
                domain_list.append(('id', 'in', matching_channel_ids))

            # Combine using ORs
            full_domain = expression.OR([tuple(d) for d in domain_list])
            return full_domain

        except Exception as e:
            _logger.error("Error in _extended_search_domain: %s", str(e))
            return []

    @http.route(['/slides/all'], type='http', auth="public", website=True, sitemap=False)
    def slides_all(self, **kwargs):
        try:
            res = super().slides_all(**kwargs)

            search_term = kwargs.get('search')
            if not search_term:
                return res

            # Get existing values
            values = res.qcontext

            website_domain = request.website.website_domain()
            default_domain = expression.AND([
                website_domain,
                ('website_published', '=', True)
            ])

            # Add enhanced search domain
            extended_domain = self._extended_search_domain(search_term)
            full_domain = expression.AND([default_domain, extended_domain])

            channels = request.env['slide.channel'].sudo().search(full_domain)
            values['channels'] = channels
            values['search'] = search_term

            return request.render("website_slides.courses_all", values)

        except Exception as e:
            _logger.error("slides_all override failed: %s", str(e))
            return request.render("website_slides.courses_all", {})
