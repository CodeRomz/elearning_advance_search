# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)


class Slide(models.Model):
    _inherit = "slide.slide"

    # Speeds up ILIKE on big HTML by precomputing a light plaintext blob
    search_blob = fields.Text(
        string="Search Blob",
        compute="_compute_search_blob",
        store=True,
        index=True,
    )

    @api.depends("name", "description", "html_content")
    def _compute_search_blob(self):
        for s in self:
            try:
                # Plain text from HTML, then collapse whitespace
                html_txt = tools.html2plaintext(s.html_content or "")
                parts = [s.name or "", s.description or "", html_txt or ""]
                text = " ".join(filter(None, parts))
                s.search_blob = " ".join(text.split())
            except Exception as exc:
                _logger.exception("search_blob compute failed for slide %s: %s", s.id, exc)
                s.search_blob = (s.name or "") + " " + (s.description or "")
