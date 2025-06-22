# Copyright 2025 Google LLC
## Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import warnings
from functools import lru_cache
from typing import Optional

from PIL import Image
import selenium
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementNotInteractableException,
    ElementClickInterceptedException,
)

from google.adk.agents.llm_agent import Agent
from google.adk.tools.load_artifacts_tool import load_artifacts_tool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from ...shared_libraries import constants
from . import prompt

warnings.filterwarnings("ignore", category=UserWarning)


@lru_cache()
def get_driver():
    if constants.DISABLE_WEB_DRIVER:
        raise RuntimeError("Web driver is disabled in constants.")
    
    options = Options()
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--verbose")
    options.add_argument("user-data-dir=/tmp/selenium")
    
    return selenium.webdriver.Chrome(options=options)


def go_to_url(url: str) -> str:
    print(Navigating to URL: {url}")
    get_driver().get(url.strip())
    return f"Navigated to URL: {url}"


async def take_screenshot(tool_context: ToolContext) -> dict:
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"screenshot_{timestamp}.png"
    print(f" Taking screenshot: {filename}")

    driver = get_driver()
    driver.save_screenshot(filename)
    with Image.open(filename) as image:
        await tool_context.save_artifact(
            filename,
            types.Part.from_bytes(data=image.tobytes(), mime_type="image/png"),
        )
    return {"status": "ok", "filename": filename}


def _safe_find(by: By, value: str):
    try:
        return get_driver().find_element(by, value)
    except NoSuchElementException:
        return None


def find_element_with_text(text: str) -> str:
    print(f" Searching for element with text: '{text}'")
    element = _safe_find(By.XPATH, f"//*[text()='{text}']")
    return "Element found." if element else "Element not found."


def click_element_with_text(text: str) -> str:
    print(f"Attempting to click element with text: '{text}'")
    try:
        element = get_driver().find_element(By.XPATH, f"//*[text()='{text}']")
        element.click()
        return f"Clicked element with text: {text}"
    except (NoSuchElementException, ElementNotInteractableException, ElementClickInterceptedException) as e:
        return f"Click failed: {type(e).__name__}"


def enter_text_into_element(text_to_enter: str, element_id: str) -> str:
    print(f" Entering text into ID '{element_id}'")
    try:
        input_element = get_driver().find_element(By.ID, element_id)
        input_element.send_keys(text_to_enter)
        return f"Entered text into element with ID: {element_id}"
    except (NoSuchElementException, ElementNotInteractableException) as e:
        return f"Text entry failed: {type(e).__name__}"


def scroll_down_screen() -> str:
    print(" Scrolling down")
    get_driver().execute_script("window.scrollBy(0, 500)")
    return "Scrolled down."


def click_at_coordinates(x: int, y: int) -> str:
    print(f"Clicking at coordinates: ({x},{y})")
    driver = get_driver()
    driver.execute_script(f"window.scrollTo({x}, {y});")
    driver.find_element(By.TAG_NAME, "body").click()
    return "Clicked at coordinates."


def get_page_source() -> str:
    print("Retrieving page source")
    return get_driver().page_source[:1_000_000]


def analyze_webpage_and_determine_action(
    page_source: str, user_task: str, tool_context: ToolContext
) -> str:
    print("Analyzing webpage and user task...")

    analysis_prompt = f"""
You are an expert web page analyzer tasked with controlling a web browser to achieve a user’s goal.
User's Task: {user_task}

Current HTML Source:
```html
{page_source}
