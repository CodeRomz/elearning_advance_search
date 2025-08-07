from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.osv import expression


class WebsiteSlidesExtended(WebsiteSlides):

    @http.route(
        ['/slides/all', '/slides/all/tag/<slug:slug_tags>'],
        type='http', auth="public", website=True, sitemap=True
    )
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False,
                           page=1, sorting=None, **post):
        values = self.slides_channel_all_values(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            page=page,
            sorting=sorting,
            **post
        )
        return request.render("website_slides.course_search_results", values)

    def slides_channel_all_values(self, slide_category=None, slug_tags=None, my=False,
                                  page=1, sorting=None, **post):
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
            base_domain = [('website_published', '=', True)]
            if slug_tags:
                tag_rs = self._channel_search_tags_slug(slug_tags)
                base_domain.append(('tag_ids', 'in', tag_rs.ids))
            if slide_category:
                base_domain.append(('category_id', '=', slide_category))
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
            channels = Channel.search(
                full_domain,
                limit=per_page,
                offset=offset,
                order=self._channel_order_by_criterion.get(sorting) or 'name asc',
            )

            values.update({
                'channels': channels,
                'pager': pager,
                'search_term': search_term,
                'search_count': total,
            })

        return values
