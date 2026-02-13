import logging

from nicegui import ui

from ....viewmodels.project.page_state_view_model import PageStateViewModel

logger = logging.getLogger(__name__)


class ImageTabs:
    """Left side image tabs showing progressively processed page imagery."""

    def __init__(self, page_state_viewmodel: PageStateViewModel):
        self._tab_ids = ["Original", "Paragraphs", "Lines", "Words", "Mismatches"]
        logger.debug("Initializing ImageTabs with tab IDs: %s", self._tab_ids)
        self.images: dict[str, ui.image] = {}
        self.page_state_viewmodel = page_state_viewmodel
        # Register callback for direct image updates (bypasses data binding)
        self.page_state_viewmodel.set_image_update_callback(self._on_images_updated)
        logger.debug("ImageTabs initialization complete with callback registered")

    def build(self):
        logger.debug("Building ImageTabs UI components")
        # Root column uses Quasar full-height/width utility classes.
        with ui.column().classes("full-width full-height") as col:
            with ui.tabs().props("dense no-caps shrink") as tabs:
                for name in self._tab_ids:
                    ui.tab(name).props("ripple")
            # Tab panels fill available space; each panel centers its image.
            with ui.tab_panels(tabs, value="Original").classes(
                "full-width full-height"
            ):
                for name in self._tab_ids:
                    with ui.tab_panel(name).classes("column full-width full-height"):
                        with ui.column().classes(
                            "items-center justify-center full-width full-height"
                        ):
                            img = (
                                ui.image()
                                .props(
                                    "fit=contain"
                                )  # rely on intrinsic container sizing
                                .classes("full-width full-height")
                            )
                            # Store image reference (no binding - using callback instead)
                            self.images[name] = img
        self.container = col
        logger.debug(
            "ImageTabs UI build complete with %d image components", len(self.images)
        )
        return col

    def _on_images_updated(self, image_dict: dict[str, str]):
        """Callback invoked when viewmodel has new images ready.

        Updates all image sources directly in one operation to avoid
        multiple websocket updates that could cause disconnection.

        Args:
            image_dict: Dictionary mapping property names to image data URLs
        """
        logger.debug("_on_images_updated called with %d images", len(image_dict))

        prop_to_tab_map = {
            "original_image_source": "Original",
            "paragraphs_image_source": "Paragraphs",
            "lines_image_source": "Lines",
            "words_image_source": "Words",
            "mismatches_image_source": "Mismatches",
        }

        # Deduplicate identical images to minimize websocket traffic
        # For blank pages, all overlay images are often identical
        unique_images = {}
        image_to_tabs = {}

        for prop_name, image_data in image_dict.items():
            tab_name = prop_to_tab_map.get(prop_name)
            if tab_name and tab_name in self.images:
                if image_data not in image_to_tabs:
                    image_to_tabs[image_data] = []
                    unique_images[image_data] = tab_name
                image_to_tabs[image_data].append(tab_name)

        logger.info(
            "Dedup: %d unique images for %d tabs",
            len(unique_images),
            len(image_dict),
        )

        # Track which images actually changed
        updates_made = 0

        # Update images - for duplicates, set all tabs to the same source
        for image_data, tabs in image_to_tabs.items():
            for tab_name in tabs:
                img_element = self.images[tab_name]
                # Update using property assignment
                img_element.source = image_data
                updates_made += 1
                logger.debug(
                    "Updated %s image (length: %d, shared with %d tabs)",
                    tab_name,
                    len(image_data) if image_data else 0,
                    len(tabs),
                )

        logger.debug("Image update complete: %d images updated", updates_made)

    def _bind_image_source(self, img: ui.image, tab_name: str):
        """DEPRECATED: Data binding removed to prevent websocket issues."""
        prop_map = {
            "Original": "original_image_source",
            "Paragraphs": "paragraphs_image_source",
            "Lines": "lines_image_source",
            "Words": "words_image_source",
            "Mismatches": "mismatches_image_source",
        }

        prop_name = prop_map.get(tab_name)
        if prop_name:
            logger.warning(
                "_bind_image_source called but binding is deprecated; using callback instead"
            )
        else:
            logger.warning(f"No property mapping found for tab: {tab_name}")

    def update_images(self):
        """Manually refresh images from viewmodel (for backward compatibility).

        Note: This is now automatic via callback, but kept for compatibility.
        """
        logger.debug("update_images called - images update automatically via callback")
