import os, sys
from pathlib import Path

def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

APP_DIR = _app_dir()

BROWSERS_DIR = APP_DIR / "pw-browsers"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS_DIR)

from playwright.sync_api import sync_playwright, TimeoutError as PlayWrightTimeoutError
import time
import pandas as pd
from dotenv import load_dotenv
from iframe_to_pdf import download_pdf_from_shopee_preview
from pdf_merge import pdf_merge
from datetime import datetime
#해당 코드 써줘야 env가져올 수 있음
import sys

load_dotenv()

PLAYWRIGHT_NAV_TIMEOUT_MS = int("30000")
PLAYWRIGHT_SELECTOR_TIMEOUT_MS = int("30000")

# json 파일 경로
json_path = APP_DIR / "runtime" / "states" / "fwee_shopee_state.json"

def get_parcel_count(page):
    text = page.locator("div.fix-card-container div.fix-top-content-left div.parcel-count").inner_text().strip()
    return int(text.split()[0])

def make_kst() -> str:
    return datetime.now().strftime("%Y_%m_%d"), datetime.now().strftime("%H%M%S")

fwee_countrylist = {
    "Singapore":"https://seller.shopee.kr/portal/sale/mass/ship?cnsc_shop_id=1147332494&mass_shipment_tab=201&filter.shipping_method=18063&filter.order_item_filter_type=item0&filter.order_process_status=1&filter.sort.sort_type=2&filter.sort.ascending=true&filter.pre_order=2&filter.shipping_urgency_filter.current_time=1770266071&filter.shipping_urgency_filter.shipping_urgency=1",
    "Taiwan Xiapi":"https://seller.shopee.kr/portal/sale/mass/ship?cnsc_shop_id=1152063847&mass_shipment_tab=201&filter.shipping_method=38064&filter.order_item_filter_type=item0&filter.order_process_status=1&filter.sort.sort_type=2&filter.sort.ascending=true&filter.pre_order=2&filter.shipping_urgency_filter.current_time=1770266088&filter.shipping_urgency_filter.shipping_urgency=1",
    "Thailand":"https://seller.shopee.kr/portal/sale/mass/ship?cnsc_shop_id=1152063845&mass_shipment_tab=201&filter.shipping_method=78016&filter.order_item_filter_type=item0&filter.order_process_status=1&filter.sort.sort_type=2&filter.sort.ascending=true&filter.pre_order=2&filter.shipping_urgency_filter.current_time=1770266100&filter.shipping_urgency_filter.shipping_urgency=1",
    "Malaysia":"https://seller.shopee.kr/portal/sale/mass/ship?cnsc_shop_id=1152063834&mass_shipment_tab=201&filter.shipping_method=28062&filter.order_item_filter_type=item0&filter.order_process_status=1&filter.sort.sort_type=2&filter.sort.ascending=true&filter.pre_order=2&filter.shipping_urgency_filter.current_time=1770266119&filter.shipping_urgency_filter.shipping_urgency=1",
    "Vietnam":"https://seller.shopee.kr/portal/sale/mass/ship?cnsc_shop_id=1152063841&mass_shipment_tab=201&filter.shipping_method=58016&filter.order_item_filter_type=item0&filter.order_process_status=1&filter.sort.sort_type=2&filter.sort.ascending=true&filter.pre_order=2&filter.shipping_urgency_filter.current_time=1770266159&filter.shipping_urgency_filter.shipping_urgency=1",
    "Philippines":"https://seller.shopee.kr/portal/sale/mass/ship?cnsc_shop_id=1152063836&mass_shipment_tab=201&filter.shipping_method=48023&filter.order_item_filter_type=item0&filter.order_process_status=1&filter.sort.sort_type=2&filter.sort.ascending=true&filter.pre_order=2&filter.shipping_urgency_filter.current_time=1770266188&filter.shipping_urgency_filter.shipping_urgency=1"
}

def create_pickup_and_download_pdf(page, country:str) -> str:
    """
    * 한 국가당 shipping_channel 을 도는 함수

    1) Mass Arrange Dropoff 클릭
    2) 송장번호가 업로드될 때까지 10초 대기
    3) 만약 밑 문구가 0 of 1 -> 실패로 간주 후, Collapse 클릭
    4) 180개 이상일 때 5초 더 추가 대기
    """
    labels, label_cnt = shipping_channel_cnt(page, country)

    for i in range(label_cnt):
        label_button = labels.nth(i)
        label_name = label_button.locator("span").first.inner_text().strip().split()[:2]
        channel_name = " ".join(label_name)
        zero_up = label_button.locator("span.meta").inner_text().strip()
        per_count = int(zero_up.strip("()"))
        if per_count >= 1:
            label_button.click()
            page.wait_for_timeout(1000)
            while True:
                parcel_count = get_parcel_count(page)
                print(f"{country}/{channel_name} 현재 처리할 송장 수: {parcel_count}")
                if parcel_count == 0:
                    print(f"{country}/{channel_name} 처리할 송장 없음, 이동")
                    break
                else:
                    # 50/page 버튼 누르기
                    page_button = page.locator("div.mass-ship-pagination div.pagination-wrapper div.page-size-dropdown-container button[type='button']")
                    page_button.click()
                    page.wait_for_timeout(1500)

                    # 드롭다운 생성 및 버튼 누르기
                    page_button = page.locator("div.eds-popper-container ul.eds-dropdown-menu li.eds-dropdown-item:has-text('200')").click()
                    page.wait_for_timeout(1500)

                    # 전체 상품 체크박스 누르기
                    page.locator("div.mass-ship-list-container div.mass-ship-list div.fix-card-top label.eds-checkbox").click()
                    page.wait_for_timeout(2000)

                    # Maybe later를 클릭해야하는 팝업이 뜸
                    try:
                        new_popup = page.locator("div.sidebar-panel div.panel-item-container div.eds-popover").nth(2).locator("div.eds-popover__ref div.FULMadiY5u div.KPWcqSw69P div.vxkYQ8dbQ8")
                        new_popup.wait_for(state="visible", timeout=3000)
                        # print(new_popup.inner_text())
                        new_popup.click()
                    except PlayWrightTimeoutError:
                        pass # 없음 패쓰

                    #Dropoff 가져오는지
                    page.locator("div.mass-action-panel div.main div.button-wrapper").click()
                    page.wait_for_timeout(2000)

                    # Arrange Shipment Progress 창에서 test
                    page.locator("div.ship-process").wait_for(state="visible",timeout=60000)
                    
                    # 10초 대기 주기
                    page.wait_for_timeout(10000)
                    another_win = page.locator("div.ship-process div.content")
                    another_win.wait_for(state="visible",timeout=60000)

                    progress_text = another_win.locator("div.footer div.des")
                    progress_text.wait_for(state="visible",timeout=60000)
                    print(progress_text.inner_text().strip())
                    page.wait_for_timeout(2000)

                    # 7 of 8 , 7 of 8이 같아야 함
                    page.wait_for_function(
                        """
                        () => {
                            const el = document.querySelector('.footer .des');
                            if (!el) return false;

                            const text = el.innerText || "";
                            const matches = text.match(/\\d+\\s+of\\s+\\d+/g);
                            if (!matches || matches.length < 2) return false;

                            const first = matches[0].trim();
                            const last  = matches[matches.length - 1].trim();

                            const m1 = first.match(/(\\d+)\\s+of\\s+(\\d+)/);
                            const m2 = last.match(/(\\d+)\\s+of\\s+(\\d+)/);
                            if (!m1 || !m2) return false;

                            const a = Number(m1[1]), b = Number(m1[2]);
                            const c = Number(m2[1]), d = Number(m2[2]);

                            // ✅ 첫/마지막이 같고, "0 of 0" 또는 "0 of N" 같은 초기 상태는 제외
                            if (a === 0 && b === 0) return false;
                            if (c === 0 && d === 0) return false;
                            if (a === 0) return false; // 필요 없으면 지워

                            return (a === c) && (b === d);
                        }
                        """,
                        timeout=60000
                    )

                    # 만약 첫번째 숫자가 0이면 바로 break
                    # 가끔 fail이 돼서 0 of 1 이럴 때 있음
                    current, total = page.evaluate("""
                    () => {
                    const el = document.querySelector('.footer .des');
                    if (!el) return [null, null];
                    const m = (el.innerText || "").match(/(\\d+)\\s+of\\s+(\\d+)/);
                    return m ? [Number(m[1]), Number(m[2])] : [null, null];
                    }
                    """)

                    if current == 0 and (total or 0) > 0:
                        print(f"fail({current} of {total}) → 넘어감")
                        page.locator("div.collapse:has-text('Collapse')").click()
                        break

                    # 안에 숫자 출력 코드
                    progress = page.evaluate("""
                    () => {
                        const el = document.querySelector('.footer .des');
                        if (!el) return null;

                        const text = el.innerText;
                        const matches = text.match(/\\d+\\s+of\\s+\\d+/g);

                        return matches ? matches[0] : null;
                    }
                    """)

                    print("출력 개수: ", progress)
                    last_number = int(progress.split("of")[1].strip())
                    if last_number >= 180:
                        page.wait_for_timeout(5000)
                        
                    # generate 버튼 누르기
                    generate_btn =another_win.locator("button:has-text('Generate')").first
                    generate_btn.wait_for(state="visible", timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
                    generate_btn.click()
                    print(f"{country} Generate 클릭했음")
                    page.wait_for_timeout(3000)

                    # 팝오버 안의 2번째 li 클릭
                    # attach는 DOM에 있기만 하면 됨
                    dropdown = page.locator("div.eds-popper-container").last
                    dropdown.wait_for(state="attached", timeout=10000)

                    # 2번째 항목 클릭
                    item = dropdown.locator("ul > li").nth(1)
                    item.wait_for(state="visible", timeout=10000)
                    
                    with page.expect_popup(timeout=5000) as p:
                        item.click()
                    pop_up = p.value
                    pop_up.wait_for_load_state("domcontentloaded",timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
                    print(f"{country} 팝업 떴음")

                    KST, KST_HS = make_kst()

                    PATH_DIR = Path(f"FWEE_{KST}")
                    PATH_DIR.mkdir(parents=True, exist_ok=True)

                    saved = download_pdf_from_shopee_preview(pop_up, save_path=f"FWEE_{KST}/FWEE_{country}_{KST}_{KST_HS}.pdf")
                    print(f"{country} PDF 저장 완료: {saved}")
                    pop_up.close()
                    page.wait_for_timeout(4000)

                    # 팝업 닫고 새로고침
                    page.reload(wait_until="domcontentloaded",timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
                    page.wait_for_timeout(5000)
 
        
def shipping_channel_cnt(page,country:str):
    try:
        page.goto(fwee_countrylist[country],timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
        print(f"{country} 열었음")
        page.wait_for_timeout(5000)

        shipping_channel = page.locator("div.shipping-channel-filter div.mass-ship-filter-item div.content div.radio-button-wrapper")
        
        group = shipping_channel.locator("div.eds-radio-group")
        labels = group.locator("label.eds-radio-button")
        label_cnt = labels.count()
        page.wait_for_timeout(1000)
        
    except TimeoutError as e:
        print(e)

    return labels, label_cnt

def run(country_input: list[str]) -> None:
    """
    외부에서 호출하기 좋은 entrypoint 함수
    - Tkinter 버튼에서 run([...]) 호출하면 됨
    """
    # 함수를 실행할 때마다 초,분을 설정해야 겹치는 파일 생성 안됨
    KST, KST_HS = make_kst()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(storage_state=json_path,
                                      viewport={"width": 1980, "height": 1080})
        page = context.new_page()

        page.goto("https://seller.shopee.kr/?cnsc_shop_id=1147332494",wait_until="domcontentloaded",timeout=PLAYWRIGHT_SELECTOR_TIMEOUT_MS)

        print("로그인 완료")

        try:
            for country in country_input:
                create_pickup_and_download_pdf(page, country)
                pdf_merge(f"{APP_DIR}/FWEE_{KST}",country,"FWEE",1200)
        finally:
            context.close()
            browser.close()

if __name__ == "__main__":
    country_input = sys.argv[1:]
    run(country_input)


