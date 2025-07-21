# slides_course_search_extension/controllers/advanced_slide_search.py

from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.osv import expression
import logging

_logger = logging.getLogger(__name__)


class WebsiteSlidesExtended(WebsiteSlides):

    @http.route(
        ['/slides/all', '/slides/all/tag/'],
        type='http', auth="public", website=True, sitemap=True
    )
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False, **post):
        # Delegate all GET/POST handling to the parent,
        # which calls slides_channel_all_values() and renders.
        return super().slides_channel_all(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            **post
        )

    def slides_channel_all_values(self,
                                  slide_category=None, slug_tags=None, my=False,
                                  page=1, order=None, sorting=None,
                                  **post):
        """
        1) Call parent to get the full original context (pager, sortings, tag_groups, etc.).
        2) If a search term is present in `post['search']`, rebuild the channels + count + pager
           using an extended ORM domain that covers channel title, description, tags,
           slide title and slide html_content.
        """
        # 1) Get original context
        values = super().slides_channel_all_values(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            page=page,
            order=order,
            sorting=sorting,
            **post
        )

        search_term = (post.get('search') or '').strip()
        if search_term:
            # Base domain: only published channels + preserve existing filters
            domain = [('website_published', '=', True)]
            if slug_tags:
                tag_rs = self._channel_search_tags_slug(slug_tags)
                domain.append(('tag_ids', 'in', tag_rs.ids))
            if slide_category:
                domain.append(('slide_category', '=', slide_category))
            if my:
                domain.append(('member_ids.user_id', '=', request.env.user.id))

            # Build OR conditions: each item is its own domain list
            or_domains = [
                [('name', 'ilike', search_term)],
                [('description', 'ilike', search_term)],
                [('tag_ids.name', 'ilike', search_term)],
                [('slide_ids.name', 'ilike', search_term)],
                [('slide_ids.html_content', 'ilike', search_term)],
            ]
            search_domain = expression.OR(or_domains)

            # Combine base domain and search_domain
            full_domain = expression.AND([domain, search_domain])

            # Recompute channels, count, pager
            Channel = request.env['slide.channel'].sudo()
            total = Channel.search_count(full_domain)
            pager = request.website.pager(
                url="/slides/all",
                total=total,
                page=values['pager']['page'],
                step=values['pager']['step'],
                url_args={**post, 'search': search_term},
            )
            channels = Channel.search(
                full_domain,
                limit=pager['step'],
                offset=pager['offset'],
                order=values['pager'].get('order') or order or 'name asc'
            )

            # Overwrite only the parts we need
            values.update({
                'channels': channels,
                'search_term': search_term,
                'search_count': total,
                'pager': pager,
            })

        return values
