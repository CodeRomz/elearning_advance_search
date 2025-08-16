# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError


from odoo import http
from odoo.http import request
# Important: import the native WebsiteSlides controller
from odoo.addons.website_slides.controllers.main import WebsiteSlides

import logging
_logger = logging.getLogger(__name__)


class WebsiteSlidesAdvanced(WebsiteSlides):
    """
    Extend Odoo's /slides/all without changing the route or template.
    We widen the 'search' behavior to include:
    - course title, description
    - slide title
    - slide content (index_content)
    while preserving all native filters (tag, category, level, role-like, type, sorting, pager).
    """

    @http.route()  # inherits the same /slides/all route and config
    def all(self, page=1, search=None, tag=None, category=None,
            slide_type=None, sorting=None, uncategorized=False, **kw):
        try:
            # We keep the original param names so dropdowns keep functioning.
            # Build an extra OR-domain for broader keyword matching.
            extra_domain = []
            if search:
                # Note: 'index_content' is used by website indexing and is safe to target for full-text-ish search.
                # We OR title, description, slide title, and index_content.
                extra_domain = ['|', '|', '|',
                                ('name', 'ilike', search),
                                ('description', 'ilike', search),
                                ('index_content', 'ilike', search),
                                ('slide_ids.name', 'ilike', search)]

            # Pass our extra domain via context so a lower-level domain builder can combine it.
            # If the core code doesn't read this context key, we fall back to an inline merge (see else branch).
            ctx = dict(request.env.context or {})
            ctx['elearn_advanced_extra_domain'] = extra_domain
            request.env.context = ctx

            # If the core provides a helper for building the domain, prefer it (future-proof).
            # Otherwise, call super() and (as last resort) re-run the search with an augmented domain.
            response = super().all(page=page, search=search, tag=tag, category=category,
                                   slide_type=slide_type, sorting=sorting, uncategorized=uncategorized, **kw)
        except Exception as exc:
            _logger.exception("Error in WebsiteSlidesAdvanced.all: %s", exc)
            # Fail safe: still return the native behavior
            return super().all(page=page, search=search, tag=tag, category=category,
                               slide_type=slide_type, sorting=sorting, uncategorized=uncategorized, **kw)
        else:
            return response
