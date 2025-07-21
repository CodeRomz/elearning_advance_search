/** @odoo-module **/

import { SlideChannelList } from '@website_slides/js/slides_course';
import { patch } from '@web/core/utils/patch';

patch(SlideChannelList.prototype, 'slides_course_search_extension', {
    /**
     * Patch willStart to inject additional search domain
     */
    async willStart() {
        await this._super(...arguments);
        const search = (this.search || "").trim();
        if (search) {
            // Extend the domain with course name, slide name, and description
            this.domain = [
                "|", "|",
                ["name", "ilike", search],                 // Course Title
                ["description", "ilike", search],          // Course Description
                ["slide_ids.name", "ilike", search],       // Slide Title
            ];
        }
    },
});
