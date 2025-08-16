# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.osv import expression

# Tunables
MAX_SEARCH_LEN = 200                # guardrail for pathological queries
SLIDES_PREVIEW_LIMIT = 12           # how many slide hits to show
SLIDES_OVERFETCH_MULTIPLIER = 3     # over-fetch before dedup to keep list full


class WebsiteSlidesExtended(WebsiteSlides):

    @http.route([
        '/slides/all',
        '/slides/all/tag/<string:slug_tags>',
    ], type='http', auth="public", website=True, sitemap=True)
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False,
                           page=1, sorting=None, **post):
        """Delegate to the core route for redirects & default behavior."""
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
        else:
            pass
        finally:
            pass

    def _website_scope_domain(self):
        try:
            Channel = request.env['slide.channel']
            if 'website_id' in Channel._fields and request.website:
                wid = request.website.id
                # allow global (=False) or current website
                return ['|', ('website_id', '=', False), ('website_id', '=', wid)]
            return []
        except Exception as exc:
            _logger.exception("AdvanceSearch: website scope failed: %s", exc)
            return []

    def slides_channel_all_values(self, slide_category=None, slug_tags=None, my=False,
                                  page=1, sorting=None, **post):
        try:
            values = super().slides_channel_all_values(
                slide_category=slide_category,
                slug_tags=slug_tags,
                my=my,
                page=page,
                sorting=sorting,
                **post
            )

            search_raw = (post.get('search') or '').strip()
            if not search_raw:
                return values
            search_term = search_raw[:MAX_SEARCH_LEN]

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
                base_filters.append(('member_ids.user_id', '=', request.env.user.id))

            channel_or = expression.OR([
                [('name', 'ilike', search_term)],               # course title
                [('description', 'ilike', search_term)],        # course description
                [('tag_ids.name', 'ilike', search_term)],       # course tag names
                [('slide_ids.name', 'ilike', search_term)],     # slide titles
                [('slide_ids.html_content', 'ilike', search_term)],  # slide HTML/body
            ])
            channel_domain = expression.AND([list(base_filters), channel_or])

            Channel = request.env['slide.channel'].sudo()
            try:
                page_int = max(int(page), 1)
            except Exception:
                page_int = 1
            per_page = getattr(self, '_slides_per_page', 12)
            order_by = self._channel_order_by_criterion.get(sorting) or 'name asc'

            total = Channel.search_count(channel_domain)
            channels = Channel.search(
                channel_domain,
                limit=per_page,
                offset=(page_int - 1) * per_page,
                order=order_by,
            )
            pager = request.website.pager(
                url=request.httprequest.path,
                total=total,
                page=page_int,
                step=per_page,
                url_args={**post, 'search': search_term},
            )

            values.update({
                'channels': channels,
                'search_term': search_term,
                'search_count': total,
                'pager': pager,
            })

            Slide = request.env['slide.slide'].sudo()

            allowed_channel_ids = Channel.search(list(base_filters)).ids or []

            slide_or = expression.OR([
                [('name', 'ilike', search_term)],           # slide title
                [('html_content', 'ilike', search_term)],   # slide HTML/body
            ])
            slide_domain = expression.AND([
                [('website_published', '=', True)],
                ws_scope or [],
                [('channel_id', 'in', allowed_channel_ids)] if allowed_channel_ids else [('id', '=', 0)],
                slide_or,
            ])

            display_limit = SLIDES_PREVIEW_LIMIT
            fetch_limit = display_limit * SLIDES_OVERFETCH_MULTIPLIER
            order_expr = (
                'date_published desc, id desc'
                if 'date_published' in Slide._fields else
                'create_date desc, id desc'
            )
            fetched_slides = Slide.search(
                slide_domain,
                limit=fetch_limit,
                order=order_expr,
            )

            seen_ids = set()
            unique_ids = []
            for rec in fetched_slides:
                if rec.id in seen_ids:
                    continue
                seen_ids.add(rec.id)
                unique_ids.append(rec.id)

            advanced_slides = Slide.browse(unique_ids[:display_limit])
            advanced_slides_count = Slide.search_count(slide_domain)

            values.update({
                'advanced_slides': advanced_slides,
                'advanced_slides_count': advanced_slides_count,
            })
            return values

        except Exception as exc:
            _logger.exception("AdvanceSearch: error in slides_channel_all_values: %s", exc)
            raise
        else:
            pass
        finally:
            pass
