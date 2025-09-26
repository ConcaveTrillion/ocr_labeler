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
        logger.debug("ImageTabs initialization complete")

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
                            # Bind image source to viewmodel property
                            self._bind_image_source(img, name)
                            self.images[name] = img
        self.container = col
        logger.debug(
            "ImageTabs UI build complete with %d image components", len(self.images)
        )
        return col

    def _bind_image_source(self, img: ui.image, tab_name: str):
        """Bind the image source to the corresponding viewmodel property."""
        prop_map = {
            "Original": "original_image_source",
            "Paragraphs": "paragraphs_image_source",
            "Lines": "lines_image_source",
            "Words": "words_image_source",
            "Mismatches": "mismatches_image_source",
        }

        prop_name = prop_map.get(tab_name)
        if prop_name:
            # Bind the image source to the viewmodel property
            img.bind_source(self.page_state_viewmodel, prop_name)
            logger.debug(f"Bound {tab_name} image to viewmodel.{prop_name}")
        else:
            logger.warning(f"No property mapping found for tab: {tab_name}")

    def update_images(self, state):
        """Legacy method - images are now bound to viewmodel properties."""
        logger.warning(
            "update_images called but images are now data-bound to viewmodel"
        )
        # This method is kept for backward compatibility but should not be used
        # Images update automatically through data binding
