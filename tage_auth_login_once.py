import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
STATE_DIR = APP_DIR / "runtime" / "state"
STATE_PATH = STATE_DIR / "tage_shopee_state.json"


def _load_env() -> None:
    env_path = APP_DIR / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    else:
        load_dotenv()


def run_login_once(get_code):
    _load_env()

    tage_id = os.getenv("TAGE_ID")
    tage_pw = os.getenv("TAGE_PW")
    if not tage_id or not tage_pw:
        raise ValueError("Missing TAGE_ID or TAGE_PW env var")

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(
            "https://seller.shopee.kr/account/signin",
            wait_until="domcontentloaded",
            timeout=30000,
        )

        page.locator(
            'input.eds-input__input[placeholder="Email/Phone/Username"]'
        ).wait_for(timeout=30000)
        page.locator(
            'input.eds-input__input[placeholder="Email/Phone/Username"]'
        ).type(tage_id, delay=120)
        page.locator('input.eds-input__input[placeholder="Password"]').type(
            tage_pw, delay=120
        )

        page.locator("button.submit-btn:has-text('Log In')").click()
        page.locator("button.eds-button--normal:has-text('Send to Email')").click()
        page.wait_for_selector("input[placeholder='Please input']", timeout=60000)

        code = (get_code() or "").strip()
        if not code:
            raise ValueError("인증코드 입력이 비어 있습니다.")

        page.locator("input[placeholder='Please input']").type(code, delay=120)
        page.locator("button.eds-button--normal:has-text('Confirm')").click()
        page.wait_for_selector("div.todo-list-container", timeout=30000)
        page.wait_for_timeout(5000)

        context.storage_state(path=str(STATE_PATH))
        browser.close()

    return str(STATE_PATH)


if __name__ == "__main__":
    run_login_once(lambda: input("인증코드 입력: ").strip())
