# slides_course_search_extension/controllers/advanced_slide_search.py

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
        # Step 1: Delegate request handling (filters, redirects) to the parent
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
        # Step 2: Get the original context (searchbar, tag_groups, sortings, etc.)
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
            # Step 3: Build base domain (published + existing filters)
            base_domain = [('website_published', '=', True)]
            if slug_tags:
                tag_rs = self._channel_search_tags_slug(slug_tags)
                base_domain.append(('tag_ids', 'in', tag_rs.ids))
            if slide_category:
                base_domain.append(('slide_category', '=', slide_category))
            if my:
                base_domain.append(('member_ids.user_id', '=', request.env.user.id))

            # Step 4: Build OR-clause list for extended search
            or_clauses = [
                [('name', 'ilike', search_term)],                    # channel title
                [('description', 'ilike', search_term)],             # channel description
                [('tag_ids.name', 'ilike', search_term)],            # channel tags
                [('slide_ids.name', 'ilike', search_term)],          # slide titles
                [('slide_ids.html_content', 'ilike', search_term)],  # slide HTML content
            ]
            search_domain = expression.OR(or_clauses)

            # Combine filters + search
            full_domain = expression.AND([base_domain, search_domain])

            # Step 5: Rebuild pagination (avoid pager['step'] KeyError)
            Channel = request.env['slide.channel'].sudo()
            total = Channel.search_count(full_domain)
            per_page = self._slides_per_page
            offset = (int(page) - 1) * per_page
            pager = request.website.pager(
                url="/slides/all",
                total=total,
                page=page,
                step=per_page,
                url_args={**post, 'search': search_term},
            )

            # Step 6: Fetch the current page of channels
            channels = Channel.search(
                full_domain,
                limit=per_page,
                offset=offset,
                order=self._channel_order_by_criterion.get(sorting) or 'name asc',
            )

            # Step 7: Overwrite only the changed context keys
            values.update({
                'channels':     channels,
                'search_term':  search_term,
                'search_count': total,
                'pager':        pager,
            })

        return values
