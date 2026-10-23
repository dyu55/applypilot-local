"""Exercise the actual local web UI with a fictional, temporary profile."""

import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

from playwright.sync_api import sync_playwright


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="applypilot-browser-") as root:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "applypilot.cli",
                "--data-dir",
                root,
                "serve",
                "--no-browser",
                "--port",
                str(port),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            url = f"http://127.0.0.1:{port}"
            for _attempt in range(100):
                try:
                    with urllib.request.urlopen(url + "/health", timeout=1):
                        break
                except OSError:
                    if process.poll() is not None:
                        raise RuntimeError(
                            "The local server exited before becoming ready."
                        ) from None
                    time.sleep(0.1)
            else:
                raise RuntimeError("The local server did not become ready.")
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page(viewport={"width": 1440, "height": 1000})
                errors = []
                page.on("pageerror", lambda error: errors.append(str(error)))
                page.goto(url)
                page.get_by_role("button", name="Explore the demo").click()
                page.get_by_role("heading", name="Welcome back, Alex.").wait_for()
                page.get_by_role("link", name="Opportunities", exact=False).first.click()
                page.get_by_placeholder("Search roles, companies, or locations...").fill("Forma")
                page.get_by_role("row").filter(has_text="Forma Studio").click()
                page.get_by_role("button", name="Prepare materials").click()
                page.get_by_text("Materials ready for your review", exact=True).wait_for()
                with page.expect_download() as info:
                    page.get_by_role("button", name="Download PDF").click()
                assert info.value.suggested_filename == "resume.pdf"
                page.get_by_label("Application status").select_option("Submitted")
                page.get_by_role("button", name="Save status").click()
                page.get_by_role("status").filter(has_text="confirmation").wait_for()
                page.get_by_label("Confirmation reference or note").fill("Fictional test receipt")
                page.get_by_role("button", name="Save status").click()
                page.get_by_text("Status and evidence recorded.", exact=True).wait_for()
                assert not errors, errors
                page.get_by_role("button", name="Close dialog").click()
                page.get_by_role("link", name="Settings", exact=False).first.click()
                page.get_by_label("Your name", exact=True).fill("Fictional Updated Name")
                page.get_by_role("button", name="Save preferences").click()
                page.get_by_text("Preferences saved.", exact=False).wait_for()
                page.reload()
                assert (
                    page.get_by_label("Your name", exact=True).input_value()
                    == "Fictional Updated Name"
                )
                page.set_viewport_size({"width": 390, "height": 844})
                page.get_by_role("link", name="Overview", exact=False).first.click()
                assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                browser.close()
        finally:
            process.terminate()
            try:
                process.communicate(timeout=8)
            except subprocess.TimeoutExpired:
                process.kill()
                process.communicate()
    print(f"Browser smoke passed on {os.name}: onboarding, PDF, confirmation, settings, mobile.")


if __name__ == "__main__":
    main()
