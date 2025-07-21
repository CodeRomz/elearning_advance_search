# Directory: slides_course_search_extension/controllers/advanced_slide_search.py
from odoo import http, _
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
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False,
                           page=1, sorting=None, **post):
        # Delegate to the parent for default filters, redirects, etc.
        return super().slides_channel_all(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            page=page,
            sorting=sorting,
            **post
        )

    def slides_channel_all_values(self, slide_category=None, slug_tags=None, my=False,
                                  page=1, sorting=None, **post):
        # Start with the original context: channels, pager, etc.
        values = super().slides_channel_all_values(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            page=page,
            sorting=sorting,
            **post
        )

        search_term = (post.get('search') or '').strip()
        if search_term:
            # 1) Build domain for channels (already in parent) and reused in channel search
            base_chan_dom = [('website_published', '=', True)]
            if slug_tags:
                tag_rs = self._channel_search_tags_slug(slug_tags)
                base_chan_dom.append(('tag_ids', 'in', tag_rs.ids))
            if slide_category:
                base_chan_dom.append(('slide_category', '=', slide_category))
            if my:
                base_chan_dom.append(('member_ids.user_id', '=', request.env.user.id))

            # 2) Extended OR clauses for channel-level search
            chan_or = [
                [('name', 'ilike', search_term)],
                [('description', 'ilike', search_term)],
                [('tag_ids.name', 'ilike', search_term)],
            ]
            chan_search_dom = expression.AND([base_chan_dom, expression.OR(chan_or)])

            # 3) Re-page channels manually to avoid KeyError on pager['step']
            Channel = request.env['slide.channel'].sudo()
            total_chan = Channel.search_count(chan_search_dom)
            per_page = self._slides_per_page
            offset = (int(page) - 1) * per_page
            pager = request.website.pager(
                url="/slides/all",
                total=total_chan,
                page=page,
                step=per_page,
                url_args={**post, 'search': search_term},
            )
            channels = Channel.search(
                chan_search_dom,
                limit=per_page,
                offset=offset,
                order=self._channel_order_by_criterion.get(sorting) or 'name asc',
            )

            # 4) Build a domain to pull matching slides *across all channels*
            Slide = request.env['slide.slide'].sudo()
            slide_or = [
                [('name', 'ilike', search_term)],
                [('description', 'ilike', search_term)],
                [('html_content', 'ilike', search_term)],
                [('tag_ids.name', 'ilike', search_term)],
                [('channel_id.name', 'ilike', search_term)],
            ]
            slide_dom = expression.AND([[('website_published', '=', True)], expression.OR(slide_or)])
            matched_slides = Slide.search(slide_dom)

            _logger.info("Search '%s': %d channels, %d slides", search_term, total_chan, len(matched_slides))

            # 5) Update only the parts that changed
            values.update({
                'channels':      channels,
                'pager':         pager,
                'search_term':   search_term,
                'search_count':  total_chan,
                'matched_slides': matched_slides,
            })

        return values
