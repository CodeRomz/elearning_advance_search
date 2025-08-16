from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.osv import expression

class WebsiteSlidesExtended(WebsiteSlides):

    @http.route([
        '/slides',
        '/slides/tag/<string:slug_tags>',              # Main courses page (alias for all)
        '/slides/all',
        '/slides/all/tag/<string:slug_tags>'           # All courses page with tag filter
    ], type='http', auth="public", website=True, sitemap=True)
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False,
                           page=1, sorting=None, **post):
        """Handle both /slides and /slides/all routes, including tag filtering,
        by delegating to the parent controller."""
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
        """Extend the context values for /slides/all page to include advanced search."""
        # Step 1: Get default values from the core implementation (preserves filters, etc.)
        values = super().slides_channel_all_values(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            page=page,
            sorting=sorting,
            **post
        )

        # Step 2: If a search term is entered, build an extended search domain
        search_term = (post.get('search') or '').strip()
        if search_term:
            # Base domain: published courses + applied filters (tag, category, my)
            base_domain = [('website_published', '=', True)]
            if slug_tags:
                tag_rs = self._channel_search_tags_slug(slug_tags)
                base_domain.append(('tag_ids', 'in', tag_rs.ids))
            if slide_category:
                base_domain.append(('slide_category', '=', slide_category))
            if my:
                base_domain.append(('member_ids.user_id', '=', request.env.user.id))

            # OR clauses for each field to search
            search_term_ilike = [('ilike', search_term)]
            or_domains = [
                [('name',) + search_term_ilike],               # course title
                [('description',) + search_term_ilike],        # course description
                [('tag_ids.name',) + search_term_ilike],       # course tag names
                [('slide_ids.name',) + search_term_ilike],     # slide titles
                [('slide_ids.html_content',) + search_term_ilike],  # slide content
            ]
            search_domain = expression.OR(or_domains)

            # Combine the base filters with the search domain
            full_domain = expression.AND([base_domain, search_domain])

            # Compute total results and prepare pagination
            Channel = request.env['slide.channel'].sudo()
            total = Channel.search_count(full_domain)
            per_page = self._slides_per_page    # default number of courses per page (from core)
            page = int(page) or 1
            pager = request.website.pager(
                url="/slides/all",
                total=total,
                page=page,
                step=per_page,
                url_args={**post, 'search': search_term},
            )

            # Fetch the courses matching the search (for the current page)
            courses = Channel.search(
                full_domain,
                limit=per_page,
                offset=(page-1) * per_page,
                order=self._channel_order_by_criterion.get(sorting) or 'name asc',
            )

            # Step 3: Update values with our search results
            values.update({
                'channels': courses,          # courses to display
                'search_term': search_term,   # echo the search query (for template display)
                'search_count': total,        # number of results found
                'pager': pager,              # updated pager for navigation
            })
            # (We do not touch 'tag_groups' or 'search_tags', they remain from super())
        return values
