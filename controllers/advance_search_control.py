# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.osv import expression


MAX_SEARCH_LEN = 200  # guardrail for pathological queries


class WebsiteSlidesExtended(WebsiteSlides):
    @http.route([
        '/slides/all',
        '/slides/all/tag/<string:slug_tags>',
    ], type='http', auth="public", website=True, sitemap=True)
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False,
                           page=1, sorting=None, **post):
        # delegate to native controller
        return super().slides_channel_all(
            slide_category=slide_category,
            slug_tags=slug_tags,
            my=my,
            page=page,
            sorting=sorting,
            **post
        )

    def _website_scope_domain(self):
        """Multi-website friendly scope (optional but recommended)."""
        Website = request.env['website']
        Channel = request.env['slide.channel']
        if 'website_id' in Channel._fields:  # CE/EE compatible safeguard
            wid = request.website.id if request.website else False
            # website-specific OR global (False) content
            return ['|', ('website_id', '=', False), ('website_id', '=', wid)]
        return []

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

        # --- bail out if no search term ---
        raw = (post.get('search') or '').strip()
        if not raw:
            return values
        search_term = raw[:MAX_SEARCH_LEN]  # soft cap

        # --- build base filters shared by channels and slides ---
        base_filters = [('website_published', '=', True)]
        ws_scope = self._website_scope_domain()
        if ws_scope:
            base_filters.extend(ws_scope)

        if slug_tags:
            tags = self._channel_search_tags_slug(slug_tags)
            if tags:
                base_filters.append(('tag_ids', 'in', tags.ids))

        if slide_category:
            base_filters.append(('slide_category', '=', slide_category))

        if my:
            # Keep native “My courses” semantics
            base_filters.append(('member_ids.user_id', '=', request.env.user.id))

        # --- COURSE (channel) results
        or_domains = expression.OR([
            [('name', 'ilike', search_term)],
            [('description', 'ilike', search_term)],
            [('tag_ids.name', 'ilike', search_term)],
            [('slide_ids.name', 'ilike', search_term)],
            [('slide_ids.html_content', 'ilike', search_term)],
        ])
        channel_domain = expression.AND([list(base_filters), or_domains])

        Channel = request.env['slide.channel'].sudo()
        per_page = getattr(self, '_slides_per_page', 12)
        try:
            page_int = max(int(page), 1)
        except Exception:
            page_int = 1

        order_by = self._channel_order_by_criterion.get(sorting) or 'name asc'
        total = Channel.search_count(channel_domain)
        channels = Channel.search(
            channel_domain,
            limit=per_page,
            offset=(page_int - 1) * per_page,
            order=order_by,
        )

        pager = request.website.pager(
            url=request.httprequest.path,     # preserve /tag/<slug> path
            total=total,
            page=page_int,
            step=per_page,
            url_args={**post, 'search': search_term},
        )

        # push course results
        values.update({
            'channels': channels,
            'search_term': search_term,
            'search_count': total,
            'pager': pager,
        })

        # --- SLIDE results (compact block)
        Slide = request.env['slide.slide'].sudo()

        # restrict slides to channels matching the same *filters* (not the keyword),
        # then apply keyword at slide level → catches relevant content even if
        # channel title/desc didn't match
        allowed_channel_ids = Channel.search(list(base_filters)).ids or []

        slide_or = expression.OR([
            [('name', 'ilike', search_term)],
            [('html_content', 'ilike', search_term)],
        ])
        slide_domain = expression.AND([
            [('website_published', '=', True)],
            ws_scope or [],
            [('channel_id', 'in', allowed_channel_ids)] if allowed_channel_ids else [('id', '=', 0)],
            slide_or,
        ])

        advanced_slides = Slide.search(
            slide_domain,
            limit=12,
            order='date_published desc, id desc' if 'date_published' in Slide._fields else 'create_date desc, id desc',
        )
        advanced_slides_count = Slide.search_count(slide_domain)

        values.update({
            'advanced_slides': advanced_slides,
            'advanced_slides_count': advanced_slides_count,
        })
        return values
