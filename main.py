from opsmate.libs.context.browser import Visit, Browser
import time

with Browser():
    print(Visit(url="https://google.com", new_page=True)())
