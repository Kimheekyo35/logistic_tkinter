from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeError
from pathlib import Path
import time
import os
from dotenv import load_dotenv
from datetime import datetime
import sys
from FM_iframe_to_pdf import download_pdf

load_dotenv()

PLAYWRIGHT_NAV_TIMEOUT_MS = int("30000")
PLAYWRIGHT_SELECTOR_TIMEOUT_MS = int("30000")

tage_countrylist = {
    "Singapore" : "https://seller.shopee.kr/portal/sale/order/pre-declare/generate?cnsc_shop_id=1147332494",
    "Taiwan Xiapi" : "https://seller.shopee.kr/portal/sale/order/pre-declare/generate?cnsc_shop_id=1152063847",
    "Malaysia" : "https://seller.shopee.kr/portal/sale/order/pre-declare/generate?cnsc_shop_id=1152063834",
    "Philippines": "https://seller.shopee.kr/portal/sale/order/pre-declare/generate?cnsc_shop_id=1152063836",
    "Vietnam": "https://seller.shopee.kr/portal/sale/order/pre-declare/generate?cnsc_shop_id=1152063841"
}

dt = datetime.now()
KST = dt.strftime("%Y_%m_%d")
KST_hs = dt.strftime("%H%M%S")

country_input = sys.argv[1:]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state="tage_shopee_state.json")
    page = context.new_page()
    page.goto("https://seller.shopee.kr/?cnsc_shop_id=1152063836",wait_until="domcontentloaded",timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)

    try:
        for country in country_input:
            page.goto(tage_countrylist[country],timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
            print(f"{country} 열었음")
            page.wait_for_timeout(5000)

            number = str(1)
            # Daily quantity에 1입력
            page.locator("input.eds-input__input[placeholder='Input number']").type(number,delay=110)

            # Submit 버튼 누르기
            submit = page.locator("div.first-mile-generate > button").click()
            
            # 팝업 x표 누르기
            success_popup = page.locator("div.first-mile-generate div.eds-modal__box i.eds-modal__close").click()

            # pickup_code 가져오기
            pickup_code_rt = page.locator("div.eds-scrollbar__content > table > tbody > tr").nth(0)
            pickup_code = pickup_code_rt.locator("td").nth(3).inner_text()
            print(pickup_code)

            # download 버튼 누르기
            download = pickup_code_rt.locator("td").last
            with page.expect_popup(timeout=10000) as popup_info:
                download.locator("div.eds-table__cell button").click()
            # pdf download하기
            pop_up = popup_info.value
            pop_up.wait_for_load_state("domcontentloaded",timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
            saved = download_pdf(pop_up,save_path=f"FWEE_FM_{KST}/FWEE_FM_{country}_{KST}.pdf") 
            print(f"{country} 저장 완료: {saved}")
            pop_up.close()

            # url 변경
            def change(url):
                origin_url = url.split("/")[7]
                cnsc_shop = origin_url.split("?")[1]
                own_number = cnsc_shop.split("=")[1]
                change_url = "/".join(url.split("/")[:7])+"/link?type=1&cnsc_shop_id="+own_number
                return change_url

            change_url = change(tage_countrylist[country])
            page.goto(change_url,wait_until="load",timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)
            page.wait_for_timeout(3000)

            while True:
                # empty = page.locator("div.eds-table__empty div.eds-default-page__content:has-text('No Orders Found')")
                # if empty.is_visible():
                #     print("데이터 없음")
                #     break
                try:
                    date = page.locator("div.eds-table__body-container div.eds-scrollbar__content tbody tr").first.locator("td").nth(6).inner_text(timeout=5000).strip()
                    date = date.split()[0].split("/")[-1]
                except PlaywrightTimeError:
                    print("행 찾을 수 없음 -> 종료")
                    break

                # select All 버튼 클릭
                select_all =  page.locator("div.eds-table-scrollX-left div.eds-table__main-header tr th").nth(0).locator("label.eds-checkbox > span")
                select_all.wait_for(state="attached")
                select_all.click()

                # 퓌는 베트남 오류가 있어서 예외 처리
                if country == "Vietnam" and date == "2025":
                    print(f"{country} Skip")
                    break

                # Bind 어쩌고 버튼 클릭 
                bind_button = page.locator("div.inline-fixed div.eds-popover__ref button").click()
                sub_button = page.locator("div.inline-fixed div.parcel div.eds-popover__popper--light div.footer div.btns button").nth(1).click()
                
                # Shipping Method 설정
                method = page.locator("div.eds-modal__box div.eds-modal__content div.eds-modal__body form div.eds-form-item__control").first
                method.click()
                page.locator("div.eds-scrollbar__content div.eds-select__options div").last.click()
                
                # Bind Parcel 팝업 뜨기
                Bind_parcel = page.locator("div.eds-modal__box div.eds-modal__body div.eds-form-item div.eds-input__inner input[type='text']").first.type(pickup_code,delay=140)
                
                #confirm 버튼 클릭
                page.locator("div.eds-modal__content div.eds-modal__footer div.footer button").nth(1).click()
                page.wait_for_timeout(3000)

                #processing 팝업 버튼 클릭
                page.locator("div.eds-modal__box div.eds-modal__body div.upload-result div.footer button").last.click()

                page.reload(wait_until="load",timeout=PLAYWRIGHT_NAV_TIMEOUT_MS)

    except Exception as e:
        print(e) 
