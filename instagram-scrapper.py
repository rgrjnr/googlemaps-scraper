# Generated by Selenium IDE
import pytest
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities


class TestNavigatetoprofile:
    def init(self):
        self.driver = webdriver.Firefox(
            executable_path=r"/Users/rogerjunior/geckodriver"
        )
        self.driver.implicitly_wait(1)
        self.vars = {}

        with open("./instagram-cookies.json", "r") as f:
            instagram_cookies = "".join(f.readlines())
            instagram_cookies = json.loads(instagram_cookies)

        self.driver.get("https://www.instagram.com/")

        for cookie in instagram_cookies:
            self.driver.add_cookie({"name": cookie, "value": instagram_cookies[cookie]})

        self.driver.get("https://www.instagram.com/")

        not_now_btn = self.find((By.CSS_SELECTOR, "._a9-z>._a9--._a9_1"))
        not_now_btn.click()

    def find(self, selector):
        self.wait = WebDriverWait(self.driver, timeout=10)
        return self.wait.until(
            expected_conditions.visibility_of_element_located(selector)
        )

    def teardown_method(self):
        self.driver.quit()

    def navigate_to_profile(self, profile):
        element = self.find(
            (By.CSS_SELECTOR, "div:nth-child(2) > .x4k7w5x .x1i10hfl > .x9f619")
        )
        element.click()
        actions = ActionChains(self.driver)
        actions.move_to_element(element).perform()
        element = self.driver.find_element(By.CSS_SELECTOR, "body")
        actions = ActionChains(self.driver)
        # actions.move_to_element(element, 0, 0).perform()
        # Search value
        self.driver.find_element(By.CSS_SELECTOR, ".x1lugfcp").send_keys(profile)
        # Click on first Result
        self.find(
            By.CSS_SELECTOR,
            ".x1i10hfl:nth-child(1) > .x9f619 > .x9f619 > .x9f619 > .x9f619 > .x9f619 > .x9f619 > .x1lliihq > .x1lliihq",
        ).click()

    def open_feed(self):
        # Open first post image

        element = self.find(
            By.CSS_SELECTOR,
            ".\\_ac7v:nth-child(1) > .\\_aabd:nth-child(1) .\\_aagw",
        )

        element.click()

        actions = ActionChains(self.driver)
        actions.move_to_element(element).perform()
        element = self.driver.find_element(By.CSS_SELECTOR, "body")
        actions = ActionChains(self.driver)
        # actions.move_to_element(element, 0, 0).perform()

    def get_post_data(self):
        description = self.driver.find_element(By.CSS_SELECTOR, ".\\_a9z6")
        print(description.text)
        # Próximo post
        self.driver.find_element(By.CSS_SELECTOR, ".x175jnsf").click()

        # Descrição css=.\_a9z6


test = TestNavigatetoprofile()
test.init()
test.navigate_to_profile(profile="constructionlisbon")


test.open_feed()
test.get_post_data()
test.get_post_data()
test.get_post_data()
