# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import (
    UserError, ValidationError, RedirectWarning, AccessDenied,
    AccessError, CacheMiss, MissingError
)
import logging
_logger = logging.getLogger(__name__)

from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.osv import expression


class WebsiteSlidesExtended(WebsiteSlides):
    """
    Extend eLearning search on /slides/all while preserving native filters,
    templates, and the separate /slides landing page behavior.
    """

    # ⚠️ IMPORTANT: Do NOT bind '/slides' here, we leave that to Odoo's native route.
    @http.route([
        '/slides/all',
        '/slides/all/tag/<string:slug_tags>',
    ], type='http', auth="public", website=True, sitemap=True)
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False,
                           page=1, sorting=None, **post):
        """
        Delegate to the core route for redirects & default behavior.
        We only hook our logic in slides_channel_all_values().
        """
        try:
            return super().slides_channel_all(
                slide_category=slide_category,
                slug_tags=slug_tags,
                my=my,
                page=page,
                sorting=sorting,
                **post
            )
        except Exception as exc:
            _logger.exception("AdvanceSearch: error in slides_channel_all: %s", exc)
            raise
        finally:
            # Structure placeholder to match user's style guide
            pass

    def slides_channel_all_values(self, slide_category=None, slug_tags=None, my=False,
                                  page=1, sorting=None, **post):
        """
        Inject advanced keyword search (course + slides) without breaking
        native filters, counts, tag UI, or templates.
        """
        try:
            # 1) Get native values first (keeps tag_groups, search_tags, sortings, etc.)
            values = super().slides_channel_all_values(
                slide_category=slide_category,
                slug_tags=slug_tags,
                my=my,
                page=page,
                sorting=sorting,
                **post
            )

            # 2) If no keyword, keep native behavior untouched
            search_term = (post.get('search') or '').strip()
            if not search_term:
                return values

            # 3) Base domain: published + applied native filters (tag/category/my)
            base_domain = [('website_published', '=', True)]

            if slug_tags:
                tag_rs = self._channel_search_tags_slug(slug_tags)
                if tag_rs:
                    base_domain.append(('tag_ids', 'in', tag_rs.ids))

            if slide_category:
                base_domain.append(('slide_category', '=', slide_category))

            if my:
                base_domain.append(('member_ids.user_id', '=', request.env.user.id))

            # 4) OR across course & slide content — all tuples (no list/tuple concat)
            or_domains = [
                [('name', 'ilike', search_term)],                  # course title
                [('description', 'ilike', search_term)],           # course description
                [('tag_ids.name', 'ilike', search_term)],          # tag names
                [('slide_ids.name', 'ilike', search_term)],        # slide titles
                [('slide_ids.html_content', 'ilike', search_term)] # slide HTML/body
            ]
            search_domain = expression.OR(or_domains)

            # 5) Combine with existing filters
            full_domain = expression.AND([base_domain, search_domain])

            # 6) Pagination & sorting
            Channel = request.env['slide.channel'].sudo()
            total = Channel.search_count(full_domain)
            per_page = getattr(self, '_slides_per_page', 12)

            try:
                page_int = max(int(page), 1)
            except Exception:
                page_int = 1

            # Keep the current path (/slides/all or /slides/all/tag/<slug>) for pager
            url_path = request.httprequest.path
            url_args = dict(post)
            url_args['search'] = search_term

            pager = request.website.pager(
                url=url_path,
                total=total,
                page=page_int,
                step=per_page,
                url_args=url_args,
            )

            order_by = self._channel_order_by_criterion.get(sorting) or 'name asc'
            channels = Channel.search(
                full_domain,
                limit=per_page,
                offset=(page_int - 1) * per_page,
                order=order_by,
            )

            # 7) Only override result bits; leave native filter context intact
            values.update({
                'channels': channels,
                'search_term': search_term,
                'search_count': total,
                'pager': pager,
            })
            return values

        except Exception as exc:
            _logger.exception("AdvanceSearch: error in slides_channel_all_values: %s", exc)
            raise
        finally:
            # placeholder for future cleanup
            pass
