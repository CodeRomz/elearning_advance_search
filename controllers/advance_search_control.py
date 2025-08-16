# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)

from odoo import http
from odoo.http import request
from odoo.addons.website_slides.controllers.main import WebsiteSlides
from odoo.osv import expression


class WebsiteSlidesExtended(WebsiteSlides):
    """
    Extend /slides/all:
    - Keep native filters (tags/category/my), sorting, and pager.
    - Add course+slide keyword search (title/desc/tags + slide title/content).
    - Provide compact slide results with explicit de-duplication.
    - Leave /slides (landing) completely native.
    """

    @http.route([
        "/slides/all",
        "/slides/all/tag/<string:slug_tags>",
    ], type="http", auth="public", website=True, sitemap=True, readonly=True)
    def slides_channel_all(self, slide_category=None, slug_tags=None, my=False,
                           page=1, sorting=None, **post):
        """
        Delegate handling (redirects, base values) to core; we extend values().
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
        else:
            # no-op — reserved for future instrumentation
            pass
        finally:
            # keep style: explicit finally for user preference
            pass

    # -------------------------
    # Helpers (modular & 18-ready)
    # -------------------------
    def _conf_int(self, key, default):
        """Fetch int system parameter safely."""
        try:
            val = request.env["ir.config_parameter"].sudo().get_param(key, default)
            return int(val)
        except Exception:
            return int(default)

    def _conf_bool(self, key, default):
        """Fetch boolean system parameter safely."""
        try:
            val = request.env["ir.config_parameter"].sudo().get_param(key, str(default))
            return str(val).lower() in ("1", "true", "yes", "y")
        except Exception:
            return bool(default)

    def _website_scope_domain(self):
        """Multi-website scope: allow global (False) or current website."""
        try:
            Channel = request.env["slide.channel"]
            if request.website and "website_id" in Channel._fields:
                wid = request.website.id
                return ["|", ("website_id", "=", False), ("website_id", "=", wid)]
            return []
        except Exception as exc:
            _logger.exception("AdvanceSearch: website scope failed: %s", exc)
            return []

    def _base_filters(self, slide_category, slug_tags, my):
        """Build the base filter list shared across course and slide queries."""
        base = [("website_published", "=", True)]
        ws_scope = self._website_scope_domain()
        if ws_scope:
            base.extend(ws_scope)

        # tags via slug path
        if slug_tags:
            tags = self._channel_search_tags_slug(slug_tags)
            if tags:
                base.append(("tag_ids", "in", tags.ids))

        # content type (course having at least one slide of that category)
        if slide_category:
            base.append(("slide_category", "=", slide_category))

        # my courses (membership)
        if my:
            base.append(("member_ids.user_id", "=", request.env.user.id))

        return base

    def _channel_search_or(self, term):
        """OR domain spanning course fields and related slides."""
        return expression.OR([
            [("name", "ilike", term)],                    # course title
            [("description", "ilike", term)],             # course description
            [("tag_ids.name", "ilike", term)],            # tag names
            [("slide_ids.name", "ilike", term)],          # slide titles
            [("slide_ids.html_content", "ilike", term)],  # slide HTML/body
        ])

    def _slide_search_or(self, term, use_blob):
        """OR domain for slide search (title + content or precomputed blob)."""
        if use_blob and "search_blob" in request.env["slide.slide"]._fields:
            return expression.OR([
                [("name", "ilike", term)],
                [("search_blob", "ilike", term)],
            ])
        return expression.OR([
            [("name", "ilike", term)],
            [("html_content", "ilike", term)],
        ])

    # -------------------------
    # Values extension
    # -------------------------
    def slides_channel_all_values(self, slide_category=None, slug_tags=None, my=False,
                                  page=1, sorting=None, **post):
        """
        Inject advanced keyword search while preserving native context.
        """
        try:
            # 1) Native values first
            values = super().slides_channel_all_values(
                slide_category=slide_category,
                slug_tags=slug_tags,
                my=my,
                page=page,
                sorting=sorting,
                **post
            )

            # 2) Keyword (soft cap length)
            raw = (post.get("search") or "").strip()
            if not raw:
                return values
            max_len = self._conf_int("elearning_advanced_search.max_search_len", 200)
            term = raw[:max_len]

            # 3) Base filters shared by both queries
            base_filters = self._base_filters(slide_category, slug_tags, my)

            # -------------------------
            # 4) COURSE (channel) results
            # -------------------------
            Channel = request.env["slide.channel"].sudo()
            or_chan = self._channel_search_or(term)
            chan_domain = expression.AND([list(base_filters), or_chan])

            # Pagination & sorting
            try:
                page_int = max(int(page), 1)
            except Exception:
                page_int = 1
            per_page = getattr(self, "_slides_per_page", 12)
            order_by = self._channel_order_by_criterion.get(sorting) or "name asc"

            total = Channel.search_count(chan_domain)
            channels = Channel.search(
                chan_domain,
                limit=per_page,
                offset=(page_int - 1) * per_page,
                order=order_by,
            )
            pager = request.website.pager(
                url=request.httprequest.path,  # keep /slides/all or /slides/all/tag/<slug>
                total=total,
                page=page_int,
                step=per_page,
                url_args={**post, "search": term},
            )

            # Push course results (do NOT touch native filter context keys)
            values.update({
                "channels": channels,
                "search_term": term,
                "search_count": total,
                "pager": pager,
            })

            # -------------------------
            # 5) SLIDE results (compact block with dedup)
            # -------------------------
            Slide = request.env["slide.slide"].sudo()

            # same filter scope: allowed channels (no keyword)
            allowed_ids = Channel.search(list(base_filters)).ids or []

            use_blob = self._conf_bool("elearning_advanced_search.use_search_blob", True)
            or_slide = self._slide_search_or(term, use_blob)

            slide_domain = expression.AND([
                [("website_published", "=", True)],
                self._website_scope_domain() or [],
                [("channel_id", "in", allowed_ids)] if allowed_ids else [("id", "=", 0)],
                or_slide,
            ])

            # Tunables
            limit_preview = self._conf_int("elearning_advanced_search.slides_preview_limit", 12)
            overfetch = self._conf_int("elearning_advanced_search.slides_overfetch_multiplier", 3)
            fetch_limit = max(limit_preview, limit_preview * overfetch)

            order_expr = ("date_published desc, id desc"
                          if "date_published" in Slide._fields else
                          "create_date desc, id desc")

            fetched = Slide.search(slide_domain, limit=fetch_limit, order=order_expr)

            # explicit de-dup by ID while preserving order
            seen, unique_ids = set(), []
            for rec in fetched:
                if rec.id in seen:
                    continue
                seen.add(rec.id)
                unique_ids.append(rec.id)

            advanced_slides = Slide.browse(unique_ids[:limit_preview])

            show_count = self._conf_bool("elearning_advanced_search.show_slide_count", True)
            advanced_slides_count = Slide.search_count(slide_domain) if show_count else len(advanced_slides)

            values.update({
                "advanced_slides": advanced_slides,
                "advanced_slides_count": advanced_slides_count,
            })
            return values

        except Exception as exc:
            _logger.exception("AdvanceSearch: error in slides_channel_all_values: %s", exc)
            raise
        else:
            # reserved for metrics
            pass
        finally:
            # consistent style for user guidelines
            pass
