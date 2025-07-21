# -*- coding: utf-8 -*-
from odoo import http, _, tools
from odoo.http import request
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging

_logger = logging.getLogger(__name__)


class SlideSearchExtension(http.Controller):

    @http.route(['/slides'], type='http', auth="public", website=True, sitemap=True)
    def enhanced_slide_search(self, search=None, page=1, **kwargs):
        try:
            domain = []
            slide_domain = []
            channel_domain = []
            search_term = tools.ustr(search or '').strip()

            if search_term:
                channel_domain += ['|', '|',
                                   ('name', 'ilike', search_term),
                                   ('description', 'ilike', search_term),
                                   ('tag_ids.name', 'ilike', search_term),
                                   ]
                slide_domain += ['|', ('name', 'ilike', search_term), ('description', 'ilike', search_term)]

            # Multi-company & publish rule-safe search
            channel_obj = request.env['slide.channel'].sudo().search(channel_domain)
            slide_obj = request.env['slide.slide'].sudo().search(slide_domain)

            # Pagination logic for slides
            slide_count = len(slide_obj)
            pager = request.website.pager(
                url="/slides",
                total=slide_count,
                page=page,
                step=6,
                url_args={'search': search_term}
            )
            paged_slides = slide_obj[pager['offset']: pager['offset'] + 6]

        except Exception as e:
            _logger.error("[Slides Search] Error: %s", str(e))
            channel_obj = slide_obj = paged_slides = []
            pager = request.website.pager(url="/slides", total=0, page=1, step=6)

        else:
            _logger.info("[Slides Search] Search completed for: %s", search_term)

        finally:
            return request.render("website_slides.slide_channels", {
                'search_term': search_term,
                'channels': channel_obj,
                'slides': paged_slides,
                'pager': pager,
            })
