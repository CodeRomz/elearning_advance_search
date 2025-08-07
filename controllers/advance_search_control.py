from odoo import http, tools
from odoo.http import request
from odoo.osv import expression  # for combining domains safely


class WebsiteSlidesAdvanceSearch(http.Controller):
    @http.route(['/slides/search'], type='http', auth='public', website=True)
    def slides_search(self, search=None, tag_ids=None, slide_category=None, role=None, **kwargs):
        # Ensure we search published records and respect multi-website access
        domain_channels = [('website_published', '=', True)]
        domain_slides = [('website_published', '=', True)]
        if hasattr(request.env['slide.channel'], 'website_id'):
            # Filter courses/slides for current website if the field exists
            domain_channels.append(('website_id', 'in', [False, request.website.id]))
            domain_slides.append(('channel_id.website_id', 'in', [False, request.website.id]))

        # Keyword search: apply if a search query is provided (match in name or description or content)
        if search:
            search_term = search.strip()
            # Domain for courses: title or description contains search term (case-insensitive)
            domain_search_courses = ['|',
                                     ('name', 'ilike', search_term),
                                     ('description', 'ilike', search_term)]
            # Domain for slides: title or (if applicable) text content contains search term
            domain_search_slides = ['|',
                                    ('name', 'ilike', search_term),
                                    ('description', 'ilike', search_term)]
            # Some slide types have an HTML content field – include it if present
            if 'html_content' in request.env['slide.slide']._fields:
                domain_search_slides = ['|'] + domain_search_slides + [('html_content', 'ilike', search_term)]
            # Combine the keyword domain with base domains
            domain_channels = expression.AND([domain_channels, domain_search_courses])
            domain_slides = expression.AND([domain_slides, domain_search_slides])

        # Filter by Tag(s) if tag_ids param is provided
        if tag_ids:
            # Support multiple tag IDs (comma-separated or list)
            if isinstance(tag_ids, str):
                tag_ids_list = [tid for tid in tag_ids.replace(';', ',').split(',') if tid]
            else:
                # e.g. QueryURL may supply tag_ids as list of strings/ids
                tag_ids_list = tag_ids if isinstance(tag_ids, (list, tuple)) else [tag_ids]
            # Convert to int and ignore invalid entries
            tag_ids_list = [int(t) for t in tag_ids_list if str(t).isdigit()]
            for tag_id in set(tag_ids_list):
                domain_channels.append(('tag_ids', 'in', tag_id))
                domain_slides.append(('channel_id.tag_ids', 'in', tag_id))

        # Filter by Course Category if slide_category param is provided (e.g. category slug or ID)
        if slide_category:
            category_ids = []
            if isinstance(slide_category, str) and not slide_category.isdigit():
                # Search category by slug (preferred) or name
                cat = request.env['slide.channel.category'].sudo().search(
                    ['|', ('slug', '=', slide_category), ('name', 'ilike', slide_category)], limit=1)
                if cat:
                    category_ids.append(cat.id)
            else:
                # Numeric category ID string or list of IDs
                vals = slide_category if isinstance(slide_category, (list, tuple)) else [slide_category]
                for val in vals:
                    try:
                        category_ids.append(int(val))
                    except ValueError:
                        continue
            for cat_id in set(category_ids):
                domain_channels.append(('category_id', '=', cat_id))
                domain_slides.append(('channel_id.category_id', '=', cat_id))

        # Filter by Level/Role if role param is provided (e.g. difficulty or audience tag)
        if role:
            role_ids = []
            if isinstance(role, str) and not role.isdigit():
                # Assume `role` could be a slug/name of a special tag (e.g. audience role or difficulty level)
                role_tag = request.env['slide.channel.tag'].sudo().search(
                    ['|', ('slug', '=', role), ('name', 'ilike', role)], limit=1)
                if role_tag:
                    role_ids.append(role_tag.id)
                else:
                    # If not a tag, it might be a difficulty keyword (Basic/Intermediate/Advanced)
                    val = role.strip().lower()
                    # Map common difficulty terms to selection values if applicable
                    diff_map = {'basic': 'Basic', 'beginner': 'Basic',
                                'intermediate': 'Intermediate', 'advanced': 'Advanced'}
                    if val in diff_map:
                        # If course difficulty is a selection field (e.g. `difficulty` or `level`)
                        # apply it. (Assuming field name `difficulty` for illustration)
                        if 'difficulty' in request.env['slide.channel']._fields:
                            domain_channels.append(('difficulty', '=', diff_map[val]))
                            domain_slides.append(('channel_id.difficulty', '=', diff_map[val]))
                        # If difficulty is implemented as tags instead, we will handle via tag_ids below.
            else:
                # Numeric role (tag) ID or list provided
                vals = role if isinstance(role, (list, tuple)) else [role]
                for val in vals:
                    try:
                        role_ids.append(int(val))
                    except ValueError:
                        continue
            # If roles correspond to tag IDs (e.g. audience role tags or difficulty tags), apply them
            for rid in set(role_ids):
                domain_channels.append(('tag_ids', 'in', rid))
                domain_slides.append(('channel_id.tag_ids', 'in', rid))

        # (Optional) Filter "My Courses" if the user wants only courses they are enrolled in (Odoo’s default “My” filter)
        if request.params.get('my'):
            partner = request.env.user.partner_id
            domain_channels.append(('channel_partner_ids.partner_id', '=', partner.id))
            domain_slides.append(('channel_id.channel_partner_ids.partner_id', '=', partner.id))

        # Execute searches with sudo (bypassing access rules, but filtering by published ensures public-only content)
        Channel = request.env['slide.channel'].sudo()
        Slide = request.env['slide.slide'].sudo()
        courses = Channel.search(domain_channels)  # courses matching criteria
        slides = Slide.search(domain_slides)  # slides matching criteria
        # Combine results: include courses that have matching slides even if the course itself didn’t directly match
        course_ids = set(courses.ids)
        for slide in slides:
            if slide.channel_id.website_published:  # safety check for published course
                course_ids.add(slide.channel_id.id)
        all_courses = Channel.browse(course_ids)

        # Prepare rendering context – reuse Odoo’s core template for course results
        values = {
            'search': search or "",  # original search term (to display in search bar)
            'channels': all_courses,  # recordset of course (slide.channel) to display
            'search_count': len(all_courses),  # total results count for messaging/pager
            'tag_ids': tag_ids,  # preserve current filters in the context
            'slide_category': slide_category,
            'role': role,
            # 'my': request.params.get('my')  -> the template may read this to highlight "My Courses" filter
        }
        return request.render('website_slides.course_search_results', values)
