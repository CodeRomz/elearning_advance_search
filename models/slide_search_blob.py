# -*- coding: utf-8 -*-
from odoo import models, fields, api, tools, _
from odoo.exceptions import UserError, ValidationError, RedirectWarning, AccessDenied, AccessError, CacheMiss, MissingError
import logging
_logger = logging.getLogger(__name__)


class Slide(models.Model):
    _inherit = "slide.slide"

    # Precomputed plaintext for faster ILIKE on big HTML (optional; can be disabled)
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
                html_txt = tools.html2plaintext(s.html_content or "")
                parts = [s.name or "", s.description or "", html_txt or ""]
                text = " ".join(filter(None, parts))
                s.search_blob = " ".join(text.split())  # collapse whitespace
            except Exception as exc:
                _logger.exception("search_blob compute failed for slide %s: %s", s.id, exc)
                s.search_blob = (s.name or "") + " " + (s.description or "")
