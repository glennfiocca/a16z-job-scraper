import asyncio

from playwright.async_api import async_playwright


async def run():
  async with async_playwright() as p:
    # Launch the browser
    browser = await p.chromium.launch()
    page = await browser.new_page()

    # Navigate to the playwright homepage
    await page.goto('https://playwright.dev/')

    # Print the home page website's title
    print('Playwright home page title: "%s"' % await page.title())

    # Navigate to the documentation page
    await page.get_by_role('link', name='Get started').click()

    # Print the documentation page website's title
    print('Documentation page title: "%s"' % await page.title())

    # Take a screenshot
    await page.screenshot(path='screenshot.png')
    print('Screenshot captured and saved as screenshot.png')

    # Close the browser
    await browser.close()


asyncio.run(run())
