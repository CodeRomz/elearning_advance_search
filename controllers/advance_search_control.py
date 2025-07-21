from odoo import http, _
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides

class AdvancedSlideSearch(WebsiteSlides):

    @http.route(['/slides/all'], type='http', auth='public', website=True, sitemap=True)
    def slides_all(self, tag=None, level=None, role=None, search=None, **kwargs):
        SlideChannel = request.env['slide.channel'].sudo()
        Slide = request.env['slide.slide'].sudo()

        domain = [('is_published', '=', True)]

        if tag:
            domain += [('tag_ids.name', '=', tag)]
        if level:
            domain += [('level', '=', level)]
        if role:
            domain += [('role', '=', role)]

        if search:
            search_domain = [
                '|', '|', '|',
                ('name', 'ilike', search),                 # Channel title
                ('description', 'ilike', search),          # Channel description
                ('slide_ids.name', 'ilike', search),       # Slide title
                ('slide_ids.description', 'ilike', search) # Slide body
            ]
            domain = ['&'] + domain + search_domain

        channels = SlideChannel.search(domain)

        # Reuse private helper to preserve tag filters
        tag_groups = self._get_tag_groups(channels)

        return request.render("website_slides.courses_all", {
            'channels': channels,
            'tag': tag,
            'level': level,
            'role': role,
            'search': search,
            'tag_groups': tag_groups,
        })
