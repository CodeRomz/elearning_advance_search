from odoo import http, _
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
import logging

_logger = logging.getLogger(__name__)


class WebsiteSlidesExtended(WebsiteSlides):

    @http.route(['/slides/all'], type='http', auth="public", website=True, sitemap=True)
    def custom_slide_search(self, **kwargs):
        search_term = kwargs.get('search')
        domain = [('website_published', '=', True)]

        if search_term:
            search_term = search_term.strip()
            # Extend the search to title, description, tags, and slide contents
            domain += ['|', '|', '|',
                       ('name', 'ilike', search_term),
                       ('description', 'ilike', search_term),
                       ('tag_ids.name', 'ilike', search_term),
                       ('slide_ids.name', 'ilike', search_term)]

        channels = request.env['slide.channel'].sudo().search(domain)

        values = {
            'tag_groups': request.env['slide.channel.tag'].sudo().get_tag_groups(),
            'search': search_term,
            'search_tags': [],  # Preserved for QWeb compatibility
            'slides': channels,
            'channels': channels,
        }
        return request.render("website_slides.courses_all", values)
