import logging
import os
from pathlib import Path

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)


class StaticLiveServerWithArtifactsOnErrorTestCase(StaticLiveServerTestCase):
    """
    TestCase that automatically captures test artifacts when tests fail.

    Provides automatic Playwright browser lifecycle management and captures:
    - Full page screenshot (.png)
    - Original page source HTML (.html)
    - Current DOM state HTML (.html)
    - Browser console logs (.txt)
    - Network request/response logs (.txt)

    Note: This class sets DJANGO_ALLOW_ASYNC_UNSAFE="true" to allow
    Playwright's sync API to work within Django's async-unsafe context.
    This is necessary because Playwright's sync API runs in an event loop,
    which Django normally prevents in certain contexts.

    Usage:
        class TestDashboard(StaticLiveServerWithArtifactsOnErrorTestCase):
            def test_dashboard_displays_portfolios_and_values(self):
                self.page.goto(self.live_server_url)
                # ... rest of test ...
    """

    @classmethod
    def setUpClass(cls):
        """Initialize Playwright at the class level to avoid async issues."""
        # Set environment variable to allow async operations in Django
        # This is needed because Playwright's sync API runs in an event loop
        os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true"

        super().setUpClass()

        # Initialize Playwright at class level
        cls._playwright = sync_playwright().start()
        cls._browser = cls._playwright.chromium.launch(headless=True)

    @classmethod
    def tearDownClass(cls):
        """Cleanup Playwright resources at class level."""
        cls._browser.close()
        cls._playwright.stop()
        super().tearDownClass()

    def setUp(self):
        """Set up page and event handlers for each test."""
        super().setUp()

        # Create a new page for each test
        self.page = self._browser.new_page()

        # Setup event handlers automatically
        self._console_logs = []
        self._network_logs = []

        self.page.on("console", self._handle_console)
        self.page.on("request", self._handle_request)
        self.page.on("response", self._handle_response)

        # Disable animations and transitions for more reliable tests
        self.page.add_init_script(
            """
            const style = document.createElement('style');
            style.innerHTML = `
                *, *::before, *::after {
                    animation-duration: 0s !important;
                    animation-delay: 0s !important;
                    transition-duration: 0s !important;
                    transition-delay: 0s !important;
                }
            `;
            document.head.appendChild(style);
        """
        )

        logger.info("Page and event handlers initialized")

    def _handle_console(self, msg):
        """Handle console messages."""
        self._console_logs.append(f"[{msg.type}] {msg.text}")

    def _handle_request(self, request):
        """Handle network requests."""
        self._network_logs.append(f"REQUEST: {request.method} {request.url}")

    def _handle_response(self, response):
        """Handle network responses."""
        self._network_logs.append(f"RESPONSE: {response.status} {response.url}")

    def tearDown(self):
        """Capture artifacts if test failed and cleanup."""
        # Check if test failed by inspecting the test result
        test_failed = False

        # For Django TestCase with pytest
        if hasattr(self, "_outcome"):
            # This works with pytest-django
            result = self._outcome.result
            if hasattr(result, "_excinfo"):
                # Check if there's exception info
                test_failed = result._excinfo is not None
            elif hasattr(result, "longrepr"):
                # If longrepr exists, the test failed
                test_failed = result.longrepr is not None
            elif hasattr(result, "outcome"):
                # Alternative way to check
                test_failed = result.outcome == "failed"

        # Fallback: check if any test method raised an exception
        if not test_failed and hasattr(self, "_testMethodName"):
            test_method = getattr(self, self._testMethodName)
            if hasattr(test_method, "__func__"):
                test_failed = getattr(test_method.__func__, "_test_failed", False)

        # Capture artifacts if test failed
        if test_failed:
            self._capture_artifacts()

        # Cleanup page for this test
        try:
            self.page.close()
        except Exception as e:
            logger.warning(f"Error during page cleanup: {e}")

        super().tearDown()

    def _capture_artifacts(self):
        """Capture test artifacts when a test fails."""
        try:
            # Create test_artifacts directory
            artifacts_dir = Path("test_artifacts")
            artifacts_dir.mkdir(exist_ok=True)

            # Generate base filename
            test_method = self._testMethodName
            module = self.__class__.__module__.replace(".", "_")
            class_name = self.__class__.__name__
            base_filename = f"{module}_{class_name}_{test_method}"

            # Capture and save screenshot
            try:
                screenshot_path = artifacts_dir / f"{base_filename}.png"
                self.page.screenshot(path=str(screenshot_path), full_page=True)
                logger.info(f"Saved screenshot to {screenshot_path}")
            except Exception as e:
                logger.warning(f"Failed to capture screenshot: {e}")

            # Capture and save current DOM
            try:
                dom_path = artifacts_dir / f"{base_filename}_dom.html"
                dom_content = self.page.content()
                dom_path.write_text(dom_content, encoding="utf-8")
                logger.info(f"Saved DOM to {dom_path}")
            except Exception as e:
                logger.warning(f"Failed to capture DOM: {e}")

            # Capture and save original page source
            try:
                source_path = artifacts_dir / f"{base_filename}_source.html"
                original_source = self.page.evaluate(
                    "() => document.documentElement.outerHTML"
                )
                source_path.write_text(original_source, encoding="utf-8")
                logger.info(f"Saved page source to {source_path}")
            except Exception as e:
                logger.warning(f"Failed to capture page source: {e}")

            # Save console logs if any were captured
            if self._console_logs:
                try:
                    console_path = artifacts_dir / f"{base_filename}_console.txt"
                    console_path.write_text(
                        "\n".join(self._console_logs), encoding="utf-8"
                    )
                    logger.info(f"Saved console logs to {console_path}")
                except Exception as e:
                    logger.warning(f"Failed to save console logs: {e}")

            # Save network logs if any were captured
            if self._network_logs:
                try:
                    network_path = artifacts_dir / f"{base_filename}_network.txt"
                    network_path.write_text(
                        "\n".join(self._network_logs), encoding="utf-8"
                    )
                    logger.info(f"Saved network logs to {network_path}")
                except Exception as e:
                    logger.warning(f"Failed to save network logs: {e}")

        except Exception as e:
            logger.error(f"Error capturing test artifacts: {e}")
