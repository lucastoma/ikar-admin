from playwright.sync_api import sync_playwright

def run(playwright):
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()

    # Go to the Connect page
    page.goto("http://127.0.0.1:8602/ikaros")
    page.screenshot(path="jules-scratch/verification/01_connect_page.png")

    # Go to the Terminal page
    page.get_by_role("link", name="Terminal").click()
    page.wait_for_selector("#terminal-container")
    page.screenshot(path="jules-scratch/verification/02_terminal_page.png")

    # Go to the Logs page
    page.get_by_role("link", name="Logs").click()
    page.wait_for_selector("#log-source")
    page.screenshot(path="jules-scratch/verification/03_logs_page.png")

    browser.close()

with sync_playwright() as playwright:
    run(playwright)