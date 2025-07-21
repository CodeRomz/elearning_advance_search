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
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False, **post):
        """
        Delegate to parent for all the GET/redirect logic,
        then our slides_channel_all_values will apply the extended search.
        """
        return super().slides_channel_all(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            **post
        )

    def slides_channel_all_values(self, slide_category=None, slug_tags=None, my=False, **post):
        """
        1) Call the original to assemble all the standard context:
           searchbar, pager, tag_groups, search_tags, sortings, etc.
        2) If `post['search']` is set, replace `values['channels']`
           and `values['search_count']` with our extended-domain results.
        """
        # 1) Fetch the original values
        values = super().slides_channel_all_values(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            **post
        )

        search_term = (post.get('search') or "").strip()
        if search_term:
            # Base: only published channels
            domain = [('website_published', '=', True)]

            # Preserve any existing filters:
            if slug_tags:
                # this helper returns a recordset of the selected tags
                tag_rs = self._channel_search_tags_slug(slug_tags)
                domain.append(('tag_ids', 'in', tag_rs.ids))
            if slide_category:
                domain.append(('slide_category', '=', slide_category))
            if my:
                domain.append(('member_ids.user_id', '=', request.env.user.id))

            # Build OR list for title/desc/tags/slides:
            or_list = [
                ('name', 'ilike', search_term),                   # Channel title
                ('description', 'ilike', search_term),            # Channel description
                ('tag_ids.name', 'ilike', search_term),           # Channel tags
                ('slide_ids.name', 'ilike', search_term),         # Slide title
                ('slide_ids.html_content', 'ilike', search_term), # Slide HTML body
            ]
            # Combine domain + OR-list
            domain = expression.AND([domain, expression.OR(or_list)])

            # Use sudo read-only search
            Channel = request.env['slide.channel'].sudo()
            channels = Channel.search(domain)

            # Overwrite the two places the template uses them:
            values.update({
                'channels':     channels,
                'search_count': len(channels),
            })
        return values
