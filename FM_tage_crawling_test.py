import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from FM_iframe_to_pdf import download_pdf


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
BROWSERS_DIR = APP_DIR / "pw-browsers"
STATE_PATH = APP_DIR / "tage_shopee_state.json"

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS_DIR)
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"

load_dotenv(APP_DIR / ".env" if (APP_DIR / ".env").exists() else None)

PLAYWRIGHT_NAV_TIMEOUT_MS = 30000
PLAYWRIGHT_SELECTOR_TIMEOUT_MS = 30000

TAGE_COUNTRYLIST = {
    "Taiwan Xiapi": "https://seller.shopee.kr/portal/sale/order/pre-declare/generate?cnsc_shop_id=1010596085",
    "Malaysia": "https://seller.shopee.kr/portal/sale/order/pre-declare/generate?cnsc_shop_id=1010596074",
}


def _change_to_link_url(url: str) -> str:
    origin_url = url.split("/")[7]
    cnsc_shop = origin_url.split("?")[1]
    own_number = cnsc_shop.split("=")[1]
    return "/".join(url.split("/")[:7]) + "/link?type=1&cnsc_shop_id=" + own_number


def _resolve_state_path() -> Path:
    if STATE_PATH.exists():
        return STATE_PATH
    raise FileNotFoundError(
        f"테스트용 state 파일이 없습니다: {STATE_PATH}"
    )


def run(country_input: list[str]) -> None:
    if not country_input:
        return

    state_path = _resolve_state_path()
    kst = datetime.now().strftime("%Y_%m_%d")
    output_dir = APP_DIR / f"TAGE_FM_TEST_{kst}"
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=str(state_path))
        page = context.new_page()
        page.goto(
            "https://seller.shopee.kr/?cnsc_shop_id=1010596074",
            wait_until="domcontentloaded",
            timeout=PLAYWRIGHT_NAV_TIMEOUT_MS,
        )

        try:
            for country in country_input:
                page.goto(
                    TAGE_COUNTRYLIST[country],
                    timeout=PLAYWRIGHT_NAV_TIMEOUT_MS,
                )
                print(f"{country} 진입")
                page.wait_for_timeout(5000)

                page.locator(
                    "input.eds-input__input[placeholder='Input number']"
                ).type("1", delay=110)

                page.locator("div.first-mile-generate > button").click()
                page.locator(
                    "div.first-mile-generate div.eds-modal__box i.eds-modal__close"
                ).click()

                pickup_code_row = page.locator(
                    "div.eds-scrollbar__content > table > tbody > tr"
                ).nth(0)
                pickup_code = pickup_code_row.locator("td").nth(3).inner_text()
                print(pickup_code)

                with page.expect_popup(timeout=10000) as popup_info:
                    pickup_code_row.locator("td").last.locator(
                        "div.eds-table__cell button"
                    ).click()

                popup = popup_info.value
                popup.wait_for_load_state(
                    "domcontentloaded", timeout=PLAYWRIGHT_NAV_TIMEOUT_MS
                )
                saved = download_pdf(
                    popup,
                    save_path=str(output_dir / f"TAGE_FM_{country}_{kst}.pdf"),
                )
                print(f"{country} 저장 완료: {saved}")
                popup.close()

                page.goto(
                    _change_to_link_url(TAGE_COUNTRYLIST[country]),
                    wait_until="load",
                    timeout=PLAYWRIGHT_NAV_TIMEOUT_MS,
                )
                page.wait_for_timeout(3000)

                while True:
                    try:
                        page.locator(
                            "div.eds-table__body-container div.eds-scrollbar__content tbody tr"
                        ).first.locator("td").nth(6).inner_text(timeout=5000).strip()
                    except PlaywrightTimeoutError:
                        break

                    select_all = page.locator(
                        "div.eds-table-scrollX-left div.eds-table__main-header tr th"
                    ).nth(0).locator("label.eds-checkbox > span")
                    select_all.wait_for(state="attached")
                    select_all.click()

                    page.locator("div.inline-fixed div.eds-popover__ref button").click()
                    page.locator(
                        "div.inline-fixed div.parcel div.eds-popover__popper--light div.footer div.btns button"
                    ).nth(1).click()

                    method = page.locator(
                        "div.eds-modal__box div.eds-modal__content div.eds-modal__body form div.eds-form-item__control"
                    ).first
                    method.click()
                    page.locator(
                        "div.eds-scrollbar__content div.eds-select__options div"
                    ).last.click()

                    page.locator(
                        "div.eds-modal__box div.eds-modal__body div.eds-form-item div.eds-input__inner input[type='text']"
                    ).first.type(pickup_code, delay=140)
                    page.locator(
                        "div.eds-modal__content div.eds-modal__footer div.footer button"
                    ).nth(1).click()
                    page.wait_for_timeout(3000)

                    page.locator(
                        "div.eds-modal__box div.eds-modal__body div.upload-result div.footer button"
                    ).last.click()
                    page.reload(wait_until="load", timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    selected_countries = sys.argv[1:] or list(TAGE_COUNTRYLIST.keys())
    run(selected_countries)
