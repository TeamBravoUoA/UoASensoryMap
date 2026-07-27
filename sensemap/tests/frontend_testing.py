
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException

from sensemap.models import Location, Space

MARKER = "[data-testid='location-marker']"
DETAIL_PANEL = "[data-testid='location-detail-panel']"
FILTER_QUIET = "[data-testid='filter-quiet']"
FILTER_CATEGORY = "[data-testid='filter-category']"
SEARCH_BOX = "[data-testid='search-box']"
FEEDBACK_BOX = "[data-testid='feedback-comment']"
FEEDBACK_SUBMIT = "[data-testid='feedback-submit']"
FEEDBACK_SUCCESS = "[data-testid='feedback-success']"
FEEDBACK_ERROR = "[data-testid='feedback-error']"


def make_location(**kwargs):
    defaults = {
        "name": "Test Place",
        "category": "library",
        "campus": "old_aberdeen",
        "latitude": 57.16,
        "longitude": -2.10,
    }
    defaults.update(kwargs)
    return Location.objects.create(**defaults)


class SensemapFrontendTestCase(StaticLiveServerTestCase):
    """Base class: spins up a headless Chrome browser against the live test server."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        options = Options()
        options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--window-size=1280,900")
        cls.browser = webdriver.Chrome(options=options)
        cls.browser.implicitly_wait(2)

    @classmethod
    def tearDownClass(cls):
        cls.browser.quit()
        super().tearDownClass()

    def open_home_page(self):
        self.browser.get(self.live_server_url)
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, MARKER))
        )

    def markers(self):
        return self.browser.find_elements(By.CSS_SELECTOR, MARKER)

    def marker_names(self):
        return [m.get_attribute("data-location-name") for m in self.markers()]

    def wait_for_marker_count(self, count, timeout=10):
        WebDriverWait(self.browser, timeout).until(
            lambda d: len(d.find_elements(By.CSS_SELECTOR, MARKER)) == count
        )


class LocationMapRenderingTests(SensemapFrontendTestCase):
    def setUp(self):
        self.library = make_location(name="The Library", category="library")
        Space.objects.create(
            location=self.library, name="Silent Floor", space_type="quiet",
            is_quiet_zone=True,
        )
        self.hub = make_location(name="The Hub", category="social_building")
        Space.objects.create(location=self.hub, name="Food Court", space_type="social")

    def test_all_seeded_locations_appear_as_markers(self):
        """
        Given 2 locations exist
        When I open the Sensemap home page
        Then I should see 2 location markers on the map
        """
        self.open_home_page()
        self.wait_for_marker_count(2)

    def test_clicking_marker_opens_detail_panel(self):
        """
        Given the Sensemap home page is open
        When I click the marker labelled "The Library"
        Then the detail panel should show its name and category
        """
        self.open_home_page()
        target = next(m for m in self.markers() if m.get_attribute("data-location-name") == "The Library")
        target.click()
        panel = WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, DETAIL_PANEL))
        )
        self.assertIn("The Library", panel.text)
        self.assertIn("Library", panel.text)


class LocationFilteringTests(SensemapFrontendTestCase):
    def setUp(self):
        self.library = make_location(name="The Library", category="library")
        Space.objects.create(
            location=self.library, name="Silent Floor", space_type="quiet",
            is_quiet_zone=True,
        )
        self.hub = make_location(name="The Hub", category="social_building")
        Space.objects.create(location=self.hub, name="Food Court", space_type="social")

    def test_quiet_only_filter_hides_non_quiet_markers(self):
        """
        Given locations with mixed quiet/non-quiet spaces exist
        When I enable the "Quiet only" filter
        Then only the quiet location's marker should remain visible
        """
        self.open_home_page()
        self.browser.find_element(By.CSS_SELECTOR, FILTER_QUIET).click()
        self.wait_for_marker_count(1)
        self.assertEqual(self.marker_names(), ["The Library"])

    def test_category_filter_narrows_markers(self):
        """
        Given locations of different categories exist
        When I filter by category "social_building"
        Then only markers of that category should remain visible
        """
        self.open_home_page()
        select = self.browser.find_element(By.CSS_SELECTOR, FILTER_CATEGORY)
        select.find_element(By.CSS_SELECTOR, "option[value='social_building']").click()
        self.wait_for_marker_count(1)
        self.assertEqual(self.marker_names(), ["The Hub"])

    def test_combined_filters_matching_nothing_show_empty_state(self):
        """
        Given locations exist
        When I combine filters that match no location
        Then a "no results" message should be shown, not a blank map
        """
        self.open_home_page()
        select = self.browser.find_element(By.CSS_SELECTOR, FILTER_CATEGORY)
        select.find_element(By.CSS_SELECTOR, "option[value='social_building']").click()
        self.browser.find_element(By.CSS_SELECTOR, FILTER_QUIET).click()
        self.wait_for_marker_count(0)
        body_text = self.browser.find_element(By.TAG_NAME, "body").text
        self.assertIn("No locations match your filters", body_text)

    def test_search_narrows_markers_as_user_types(self):
        """
        Given locations exist
        When I type "hub" into the search box
        Then only matching markers should remain visible
        """
        self.open_home_page()
        box = self.browser.find_element(By.CSS_SELECTOR, SEARCH_BOX)
        box.send_keys("hub")
        self.wait_for_marker_count(1)
        self.assertEqual(self.marker_names(), ["The Hub"])


class FeedbackFormTests(SensemapFrontendTestCase):
    def setUp(self):
        self.loc = make_location(name="The Library")

    def open_detail_panel(self):
        self.open_home_page()
        target = next(m for m in self.markers() if m.get_attribute("data-location-name") == "The Library")
        target.click()
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, DETAIL_PANEL))
        )

    def test_valid_feedback_shows_success_confirmation(self):
        """
        Given the detail panel for a location is open
        When I submit valid feedback
        Then I should see a success confirmation
        """
        self.open_detail_panel()
        self.browser.find_element(By.CSS_SELECTOR, FEEDBACK_BOX).send_keys(
            "Very quiet on the third floor today"
        )
        self.browser.find_element(By.CSS_SELECTOR, FEEDBACK_SUBMIT).click()
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, FEEDBACK_SUCCESS))
        )

    def test_empty_comment_shows_validation_error(self):
        """
        Given the detail panel for a location is open
        When I submit the feedback form without entering a comment
        Then I should see a validation error, not a silent failure
        """
        self.open_detail_panel()
        self.browser.find_element(By.CSS_SELECTOR, FEEDBACK_SUBMIT).click()
        WebDriverWait(self.browser, 10).until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, FEEDBACK_ERROR))
        )

    def test_script_tag_feedback_does_not_execute_or_render_as_html(self):
        """
        Given the detail panel for a location is open
        When I submit feedback containing a <script> payload
        Then no JavaScript alert should fire and no live <script> element
        should be injected into the page
        """
        self.open_detail_panel()
        self.browser.find_element(By.CSS_SELECTOR, FEEDBACK_BOX).send_keys(
            "<script>alert('xss')</script>"
        )
        self.browser.find_element(By.CSS_SELECTOR, FEEDBACK_SUBMIT).click()

        try:
            WebDriverWait(self.browser, 3).until(EC.alert_is_present())
            self.fail("An unexpected JavaScript alert fired — possible XSS")
        except TimeoutException:
            pass  # no alert appeared, which is the desired outcome
        except UnexpectedAlertPresentException:
            self.fail("An unexpected JavaScript alert fired — possible XSS")

        scripts = self.browser.find_elements(By.TAG_NAME, "script")
        injected = [s for s in scripts if "alert('xss')" in (s.get_attribute("innerHTML") or "")]
        self.assertFalse(injected, "payload was injected as a live <script> element")

    def test_submit_button_disabled_during_submission(self):
        """
        Given the detail panel for a location is open
        When I submit valid feedback
        Then the submit button should be disabled while the request is in flight
        """
        self.open_detail_panel()
        self.browser.find_element(By.CSS_SELECTOR, FEEDBACK_BOX).send_keys("Nice reading room")
        button = self.browser.find_element(By.CSS_SELECTOR, FEEDBACK_SUBMIT)
        button.click()
        self.assertTrue(
            button.get_attribute("disabled") is not None
            or "disabled" in (button.get_attribute("class") or "")
        )