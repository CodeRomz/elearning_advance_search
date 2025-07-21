/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SlideChannelList } from "@website_slides/js/slides_channel_list";

class SlideChannelListExtended extends SlideChannelList {
    async willStart() {
        await super.willStart();

        const searchTerm = this.env.searchParams.search || "";
        if (searchTerm) {
            const result = await this.rpc("/slides/extended_search", { search: searchTerm });
            this.extraSlides = result.slides;
            this.hasSearchResults = result.slides.length > 0;
        } else {
            this.extraSlides = [];
            this.hasSearchResults = false;
        }
    }
}

SlideChannelListExtended.template = "website_slides.SlideChannelList";
registry.category("slides").add("SlideChannelListExtended", SlideChannelListExtended);
