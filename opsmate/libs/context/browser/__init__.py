from opsmate.libs.core.types import Context, ContextSpec, Metadata, Executable
from pydantic import Field
from playwright.sync_api import sync_playwright, Playwright, Browser
from typing import Optional, List
from collections import deque


class BrowserContext:
    _context_managed: deque[Browser] = deque()

    @classmethod
    def push(cls, browser: Browser):
        cls._context_managed.appendleft(browser)

    @classmethod
    def pop(cls):
        return cls._context_managed.popleft()

    @classmethod
    def current(cls):
        if len(cls._context_managed) == 0:
            raise Exception("No browser context found")
        return cls._context_managed[0]


class Browser:
    def __enter__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        BrowserContext.push(self.browser)
        return self.browser

    def __exit__(self, exc_type, exc_value, traceback):
        self.browser.close()
        self.playwright.stop()
        BrowserContext.pop()


class Visit(Executable):
    url: str = Field(title="url")
    new_page: bool = Field(title="new_page", default=True)
    tab_id: Optional[str] = Field(title="tab_id", default=None)

    def __call__(self):
        browser = BrowserContext.current()
        if self.new_page:
            page = browser.new_page()
        else:
            page = browser.pages[self.tab_id]

        page.goto(self.url)
        page.wait_for_load_state("domcontentloaded")

        return page.content()
