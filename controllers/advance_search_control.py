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
        # Delegate GET/POST handling (redirects, filters, etc.) to the parent
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
        # 1) Start from the original context
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
            # 2) Build your extended search domain
            base_domain = [('website_published', '=', True)]
            if slug_tags:
                # preserve the tag-filter logic
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
            search_domain = expression.OR(or_clauses)
            full_domain = expression.AND([base_domain, search_domain])

            # 3) Rebuild pager from the `page` arg and our per-page setting
            Channel = request.env['slide.channel'].sudo()
            total = Channel.search_count(full_domain)
            pager = request.website.pager(
                url="/slides/all",
                total=total,
                page=page,
                step=self._slides_per_page,
                url_args={**post, 'search': search_term},
            )

            # 4) Fetch only the slice we need
            channels = Channel.search(
                full_domain,
                limit=pager['step'],
                offset=pager['offset'],
                order=self._channel_order_by_criterion.get(sorting) or 'name asc'
            )

            # 5) Overwrite only the bits we need in the context
            values.update({
                'channels':     channels,
                'search_term':  search_term,
                'search_count': total,
                'pager':        pager,
            })

        return values
