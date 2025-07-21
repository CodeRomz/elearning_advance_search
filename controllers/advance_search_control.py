from odoo import http, _
from odoo.http import request
from odoo.exceptions import MissingError, UserError
import logging
_logger = logging.getLogger(__name__)

class SlideCourseSearchController(http.Controller):

    @http.route(['/slides/all'], type='http', auth="public", website=True, sitemap=True)
    def custom_slide_search(self, search='', tag_id=None, page=1, order='name asc', **kwargs):
        try:
            SlideChannel = request.env['slide.channel'].sudo()
            domain = [('website_published', '=', True)]

            # Search logic (slides and channel titles, description, tags)
            if search:
                domain += ['|', '|', '|',
                           ('name', 'ilike', search),
                           ('description', 'ilike', search),
                           ('tag_ids.name', 'ilike', search),
                           ('slide_ids.name', 'ilike', search)]

            total = SlideChannel.search_count(domain)
            pager = request.website.pager(
                url="/slides/all",
                total=total,
                page=page,
                step=12,
                url_args={'search': search, 'tag_id': tag_id, 'order': order},
            )

            channels = SlideChannel.search(domain, limit=12, offset=pager['offset'], order=order)

            values = request.env['slide.channel']._prepare_website_values(
                channels=channels,
                search=search,
                order=order,
                page=page,
                tag_id=tag_id,
            )

            return request.render('website_slides.courses_all', values)

        except Exception as e:
            _logger.error("Error in custom /slides/all search controller: %s", e)
            raise e
