import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable

from PyPDF2 import PdfReader
from dotenv import load_dotenv
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from iframe_to_pdf import download_pdf_from_shopee_preview
from pdf_merge import pdf_merge
from pdf_to_text import pdf_to_text


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
BROWSERS_DIR = APP_DIR / "pw-browsers"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS_DIR)
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"

load_dotenv()

PLAYWRIGHT_NAV_TIMEOUT_MS = 30000
PLAYWRIGHT_SELECTOR_TIMEOUT_MS = 30000
json_path = APP_DIR / "runtime" / "state" / "tage_shopee_state.json"


tage_countrylist = {
    "Taiwan Xiapi": "https://seller.shopee.kr/portal/sale/mass/ship?cnsc_shop_id=1010596085&mass_shipment_tab=201&filter.shipping_method=38064&filter.order_item_filter_type=item0&filter.order_process_status=1&filter.sort.sort_type=2&filter.sort.ascending=true&filter.pre_order=2&filter.shipping_urgency_filter.current_time=1775521325&filter.shipping_urgency_filter.shipping_urgency=1",
    "Malaysia": "https://seller.shopee.kr/portal/sale/mass/ship?cnsc_shop_id=1010596074&mass_shipment_tab=201&filter.shipping_method=28050&filter.order_item_filter_type=item0&filter.order_process_status=1&filter.sort.sort_type=2&filter.sort.ascending=true&filter.pre_order=2&filter.shipping_urgency_filter.current_time=1775521370&filter.shipping_urgency_filter.shipping_urgency=1",
}


def resolve_json_path() -> Path:
    if json_path.exists():
        return json_path
    raise FileNotFoundError(
        "tage_shopee_state.json 파일이 없습니다. 먼저 'TAGE Shopee 로그인'을 실행하세요."
    )


def get_parcel_count(page) -> int:
    text = page.locator(
        "div.fix-card-container div.fix-top-content-left div.parcel-count"
    ).inner_text().strip()
    return int(text.split()[0])


def make_kst() -> tuple[str, str]:
    now = datetime.now()
    return now.strftime("%Y_%m_%d"), now.strftime("%H%M%S")


def make_link_url(url: str) -> str:
    cnsc_shop_id = url.split("cnsc_shop_id=")[-1]
    base = "/".join(url.split("/")[:7])
    return f"{base}/link?type=1&cnsc_shop_id={cnsc_shop_id}"


def pdf_merge_split(country, n_path):
    return pdf_merge(n_path, country, 1200)


def _emit_progress(progress_callback: Callable | None, **payload) -> None:
    if progress_callback is not None:
        progress_callback(payload)


def _count_pdf_pages(pdf_path: str | Path) -> int:
    try:
        return len(PdfReader(str(pdf_path)).pages)
    except Exception:
        return 0


def _read_progress_counts(page) -> tuple[int, int]:
    current, total = page.evaluate(
        """
        () => {
            const el = document.querySelector('.footer .des');
            if (!el) return [0, 0];

            const text = el.innerText || "";
            const matches = text.match(/\\d+\\s+of\\s+\\d+/g);
            if (!matches || matches.length < 1) return [0, 0];

            const last = matches[matches.length - 1].trim();
            const m = last.match(/(\\d+)\\s+of\\s+(\\d+)/);
            return m ? [Number(m[1]), Number(m[2])] : [0, 0];
        }
        """
    )
    return int(current or 0), int(total or 0)


def shipping_channel_cnt(page, country: str):
    page.goto(tage_countrylist[country], timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
    page.wait_for_timeout(5000)

    shipping_channel = page.locator(
        "div.shipping-channel-filter div.mass-ship-filter-item div.content div.radio-button-wrapper"
    )
    group = shipping_channel.locator("div.eds-radio-group")
    labels = group.locator("label.eds-radio-button")
    label_cnt = labels.count()
    page.wait_for_timeout(1000)
    return labels, label_cnt


def create_pickup_and_download_pdf(
    page,
    country: str,
    output_dir: Path,
    progress_callback: Callable | None = None,
) -> dict:
    labels, label_cnt = shipping_channel_cnt(page, country)
    country_stats = {
        "country": country,
        "shopee_total_pages": 0,
        "downloaded_pages": 0,
        "merged_downloaded_pages": 0,
        "downloaded_files": 0,
    }

    for i in range(label_cnt):
        label_button = labels.nth(i)
        label_name = label_button.locator("span").first.inner_text().strip().split()[:2]
        channel_name = " ".join(label_name)
        zero_up = label_button.locator("span.meta").inner_text().strip()
        per_count = int(zero_up.strip("()"))
        if per_count < 1:
            continue

        label_button.click()
        page.wait_for_timeout(1000)

        while True:
            parcel_count = get_parcel_count(page)
            print(f"{country}/{channel_name} 현재 처리할 송장 수: {parcel_count}")
            _emit_progress(
                progress_callback,
                event="parcel_count",
                channel=channel_name,
                parcel_count=parcel_count,
                **country_stats,
            )
            if parcel_count == 0:
                print(f"{country}/{channel_name} 처리할 송장 없음, 이동")
                break

            page_button = page.locator(
                "div.mass-ship-pagination div.pagination-wrapper div.page-size-dropdown-container button[type='button']"
            )
            page_button.click()
            page.wait_for_timeout(1500)
            page.locator(
                "div.eds-popper-container ul.eds-dropdown-menu li.eds-dropdown-item:has-text('200')"
            ).click()
            page.wait_for_timeout(1500)

            page.locator(
                "div.mass-ship-list-container div.mass-ship-list div.fix-card-top label.eds-checkbox"
            ).click()
            page.wait_for_timeout(2000)

            try:
                maybe_later = (
                    page.locator("div.sidebar-panel div.panel-item-container div.eds-popover")
                    .nth(2)
                    .locator(
                        "div.eds-popover__ref div.FULMadiY5u div.KPWcqSw69P div.vxkYQ8dbQ8"
                    )
                )
                maybe_later.wait_for(state="visible", timeout=3000)
                maybe_later.click()
            except PlaywrightTimeoutError:
                pass

            page.locator("div.mass-action-panel div.main div.button-wrapper").click()
            page.wait_for_timeout(2000)

            page.locator("div.ship-process").wait_for(state="visible", timeout=60000)
            dialog = page.locator("div.ship-process div.content")
            dialog.wait_for(state="visible", timeout=60000)
            progress_text = dialog.locator("div.footer div.des")
            progress_text.wait_for(state="visible", timeout=60000)
            print(progress_text.inner_text().strip())

            page.wait_for_timeout(30000)
            page.wait_for_function(
                """
                () => {
                    const el = document.querySelector('.footer .des');
                    if (!el) return false;

                    const text = el.innerText || "";
                    const matches = text.match(/\\d+\\s+of\\s+\\d+/g);
                    if (!matches || matches.length < 1) return false;

                    const last = matches[matches.length - 1].trim();
                    const m = last.match(/(\\d+)\\s+of\\s+(\\d+)/);
                    if (!m) return false;

                    const current = Number(m[1]);
                    const total = Number(m[2]);
                    if (total === 0 || current === 0) return false;
                    return current >= 195 || current === total;
                }
                """,
                timeout=30000,
            )

            current, total = _read_progress_counts(page)
            print(f"최종 진행 상태: {current} of {total}")

            country_stats["shopee_total_pages"] += total
            country_stats["downloaded_pages"] += current
            _emit_progress(
                progress_callback,
                event="batch_ready",
                channel=channel_name,
                parcel_count=parcel_count,
                batch_current=current,
                batch_total=total,
                **country_stats,
            )

            if current == 0 and total > 0:
                print(f"fail({current} of {total}) 넘어감")
                page.locator("div.collapse:has-text('Collapse')").click()
                break

            if current >= 195:
                page.wait_for_timeout(5000)

            generate_btn = dialog.locator("button:has-text('Generate')").first
            generate_btn.wait_for(state="visible", timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
            generate_btn.click()
            page.wait_for_timeout(3000)

            dropdown = page.locator("div.eds-popper-container").last
            dropdown.wait_for(state="attached", timeout=10000)
            item = dropdown.locator("ul > li").nth(1)
            item.wait_for(state="visible", timeout=10000)

            with page.expect_popup(timeout=5000) as popup_info:
                item.click()
            pop_up = popup_info.value
            pop_up.wait_for_load_state(
                "domcontentloaded", timeout=PLAYWRIGHT_NAV_TIMEOUT_MS
            )

            kst, kst_hs = make_kst()
            output_dir.mkdir(parents=True, exist_ok=True)
            saved = download_pdf_from_shopee_preview(
                pop_up,
                save_path=str(output_dir / f"TAGE_{country}_{kst}_{kst_hs}.pdf"),
            )
            print(f"{country} PDF 저장 완료: {saved}")

            downloaded_pdf_pages = _count_pdf_pages(saved)
            country_stats["merged_downloaded_pages"] += downloaded_pdf_pages
            country_stats["downloaded_files"] += 1
            _emit_progress(
                progress_callback,
                event="pdf_downloaded",
                channel=channel_name,
                parcel_count=parcel_count,
                downloaded_pdf_pages=downloaded_pdf_pages,
                saved_path=saved,
                **country_stats,
            )

            pop_up.close()
            page.wait_for_timeout(4000)
            page.reload(
                wait_until="domcontentloaded", timeout=PLAYWRIGHT_NAV_TIMEOUT_MS
            )
            page.wait_for_timeout(5000)

    return country_stats


def run(country_input: list[str], progress_callback: Callable | None = None) -> dict:
    kst, _ = make_kst()
    state_path = resolve_json_path()
    output_dir = APP_DIR / f"TAGE_{kst}"
    totals = {
        "shopee_total_pages": 0,
        "downloaded_pages": 0,
        "merged_downloaded_pages": 0,
        "downloaded_files": 0,
    }
    _emit_progress(progress_callback, event="run_started", countries=country_input, **totals)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=str(state_path)        
            )
        page = context.new_page()
        page.goto(
            "https://seller.shopee.kr/?cnsc_shop_id=1010596074",
            wait_until="domcontentloaded",
            timeout=PLAYWRIGHT_SELECTOR_TIMEOUT_MS,
        )

        try:
            for country in country_input:
                country_stats = create_pickup_and_download_pdf(
                    page,
                    country,
                    output_dir,
                    progress_callback=progress_callback,
                )
                totals["shopee_total_pages"] += country_stats["shopee_total_pages"]
                totals["downloaded_pages"] += country_stats["downloaded_pages"]
                totals["merged_downloaded_pages"] += country_stats["merged_downloaded_pages"]
                totals["downloaded_files"] += country_stats["downloaded_files"]
                _emit_progress(
                    progress_callback,
                    event="country_done",
                    country=country,
                    **totals,
                )
                pdf_merge(str(output_dir), country, 1200)
                pdf_to_text(
                    str(output_dir),
                    country,
                    str(output_dir / f"TAGE_{country}_{kst}.xlsx"),
                )
        finally:
            context.close()
            browser.close()

    _emit_progress(progress_callback, event="run_finished", countries=country_input, **totals)
    return totals


if __name__ == "__main__":
    run(sys.argv[1:])
