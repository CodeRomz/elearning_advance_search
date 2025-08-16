# Directory: slides_course_search_extension/__manifest__.py

{
    "name": "Slides Course Search Extension",

    "summary": "Extend OWL-based search in /slides with full content & tag matching",
    "description": """
        This module enhances the Odoo 17 Community eLearning (/slides) page by adding
        OWL-compliant search functionality for:
        - Course titles, descriptions, and tags
        - Slide titles and descriptions
        It renders matched results using extended OWL components and a JSON RPC controller.
    """,

    'author': 'CodeRomz',
    'website': "https://github.com/CodeRomz",
    'license': 'LGPL-3',
    'version': '17.0.1.0.0',

    "category": "Website",
    "depends": ["website_slides"],

    "data": [
        "views/advance_search_templates.xml",
        "views/courses_all_bodyclass.xml",
    ],

    "assets": {
        "web.assets_frontend": [
            "elearning_advance_search/static/src/css/elearning_search_offset.css",
        ],
    },

    "auto_install": False,
    "installable": True,
    "application": False,

}
