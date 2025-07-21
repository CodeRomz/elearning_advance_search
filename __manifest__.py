# Directory: slides_course_search_extension/__manifest__.py

{
    "name": "Slides Course Search Extension",
    "version": "1.1.0",
    "category": "Website",
    "summary": "Extend OWL-based search in /slides with full content & tag matching",
    "description": """
        This module enhances the Odoo 17 Community eLearning (/slides) page by adding
        OWL-compliant search functionality for:
        - Course titles, descriptions, and tags
        - Slide titles and descriptions
        It renders matched results using extended OWL components and a JSON RPC controller.
    """,
    "author": "CodeRomz",
    "license": "LGPL-3",
    "depends": [
        "website_slides",
    ],
    # "assets": {
    #     "website.assets_frontend": [
    #         "/slides_course_search_extension/static/src/js/slide_channel_list_extended.js",
    #     ],
    # },
    "auto_install": False,
    "installable": True,
    "application": False,
}
