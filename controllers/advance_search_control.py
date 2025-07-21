from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.osv import expression

class WebsiteSlidesExtended(WebsiteSlides):

    @http.route(
        ['/slides/all', '/slides/all/tag/'],
        type='http', auth="public", website=True, sitemap=True
    )
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False,
                           page=1, sorting=None, **post):
        # Delegate GET/POST handling to the parent, which calls slides_channel_all_values()
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
        # 1) Get the original context (searchbar, tag_groups, pager, etc.)
        values = super().slides_channel_all_values(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            page=page,
            sorting=sorting,
            **post
        )

        # 2) If there's a search term, extend both channel and slide searches
        search_term = (post.get('search') or '').strip()
        if search_term:
            # --- Channel Search (your existing code) ---
            base_domain = [('website_published', '=', True)]
            if slug_tags:
                tag_rs = self._channel_search_tags_slug(slug_tags)
                base_domain.append(('tag_ids', 'in', tag_rs.ids))
            if slide_category:
                base_domain.append(('slide_category', '=', slide_category))
            if my:
                base_domain.append(('member_ids.user_id', '=', request.env.user.id))

            or_clauses = [
                [('name', 'ilike', search_term)],
                [('description', 'ilike', search_term)],
                [('tag_ids.name', 'ilike', search_term)],
                [('slide_ids.name', 'ilike', search_term)],
                [('slide_ids.html_content', 'ilike', search_term)],
            ]
            chan_search = expression.AND([base_domain, expression.OR(or_clauses)])

            Channel = request.env['slide.channel'].sudo()
            total = Channel.search_count(chan_search)
            per_page = self._slides_per_page
            offset = (int(page) - 1) * per_page
            pager = request.website.pager(
                url="/slides/all",
                total=total,
                page=page,
                step=per_page,
                url_args={**post, 'search': search_term},
            )
            channels = Channel.search(
                chan_search,
                limit=per_page,
                offset=offset,
                order=self._channel_order_by_criterion.get(sorting) or 'name asc',
            )

            # --- Slide Search (new) ---
            slide_base = [('website_published', '=', True)]
            if slug_tags:
                slide_base.append(('tag_ids', 'in', tag_rs.ids))
            if my:
                slide_base.append(('member_ids.user_id', '=', request.env.user.id))

            slide_clauses = [
                [('name', 'ilike', search_term)],
                [('description', 'ilike', search_term)],
                [('html_content', 'ilike', search_term)],
                [('tag_ids.name', 'ilike', search_term)],
            ]
            slide_search = expression.AND([slide_base, expression.OR(slide_clauses)])

            Slide = request.env['slide.slide'].sudo()
            matched_slides = Slide.search(slide_search, limit=50)

            # --- Update only the changed context keys ---
            values.update({
                'channels':      channels,
                'search_term':   search_term,
                'search_count':  total,
                'pager':         pager,
                'matched_slides': matched_slides,
            })

        return values
