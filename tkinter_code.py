# -*- coding: utf-8 -*-
import os, sys
from pathlib import Path

def _app_dir() -> Path:
    # exe로 실행 중이면 exe가 있는 폴더, 아니면 현재 파일 폴더
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent

APP_DIR = _app_dir()

# ✅ 배포 폴더 안의 "pw-browserst"를 브라우저 저장소로 강제
BROWSERS_DIR = APP_DIR / "pw-browsers"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS_DIR)

# (선택) 실행 중에 다운로드 시도하지 말라고(오프라인 환경에서 유용)
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
from dataclasses import dataclass
from dotenv import load_dotenv
import os
import inspect
# 인증 토큰
from fwee_auth_login_once import run_login_once as fwee_login
from numbuzin_auth_login_once import run_login_once as num_login
# ----------------------------------------------
# FM 라벨
from FM_fwee_crawling import run as fwee_run, FWEE_COUNTRYLIST
from FM_numbuzin_crawling import run as num_run, NUM_COUNTRYLIST
# ---------------------------------------------
# 송장번호
from numbuzin_crawling import run as numbuzin_run, numbuzin_country
from fwee_crawling import run as fw_run, fwee_countrylist
load_dotenv()

LOGIN_ID = os.getenv("TKINT_ID") or "admin"
LOGIN_PW = os.getenv("TKINT_PW") or "admin123"

# 데이터만 저장하는 클래스를 쉽게 만드는 것
@dataclass
class AppState:
    # 로그인 결과(json 파일명) 보관용 (크롤링에 쓰지 않더라도 “로그인 됨” 표시 가능)
    fwee_state_json: str | None = None
    numbuzin_state_json: str | None = None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # 첫 로그인 화면
        self.title("Shopee 송장번호 자동화 프로그램")
        self.geometry("1100x720")
        self.minsize(1000, 650)

        self.state = AppState()
        self.logq = queue.Queue()
        self.current_menu = tk.StringVar(value="홈")

        self._build_login_ui()
        self.after(100, self._drain_logq)

    # ------------------ 공통: 로그 ------------------
    def log(self, msg: str):
        self.logq.put(msg if msg.endswith("\n") else msg + "\n")
    
    # 로그를 화면에 계속 뿌려주는 반복 함수
    def _drain_logq(self):
        try:
            while True:
                msg = self.logq.get_nowait()
                if hasattr(self, "log_text"):
                    self.log_text.insert("end", msg)
                    self.log_text.see("end")
        except queue.Empty:
            pass
        self.after(100, self._drain_logq)

    # 하단 로그 박스
    def _build_log_box(self, parent):
        box = ttk.LabelFrame(parent, text="실행 로그", padding=10)
        box.pack(fill="both", expand=True, pady=10)

        self.log_text = tk.Text(box, height=18, wrap="word")
        self.log_text.pack(fill="both", expand=True)

        btns = ttk.Frame(parent)
        btns.pack(fill="x")
        ttk.Button(btns, text="로그 지우기", command=lambda: self.log_text.delete("1.0", "end")).pack(side="left")

    # ------------------ 로그인 UI ------------------
    def _clear_root(self):
        for w in self.winfo_children():
            w.destroy()

    def _build_login_ui(self):
        self._clear_root()
        wrapper = ttk.Frame(self, padding=30)
        wrapper.pack(fill="both", expand=True)

        ttk.Label(wrapper, text="로그인", font=("Segoe UI", 18, "bold")).pack(pady=(0, 20))

        form = ttk.Frame(wrapper)
        form.pack()

        ttk.Label(form, text="아이디").grid(row=0, column=0, sticky="e", padx=8, pady=8)
        self.id_entry = ttk.Entry(form, width=30)
        self.id_entry.grid(row=0, column=1, padx=8, pady=8)

        ttk.Label(form, text="비밀번호").grid(row=1, column=0, sticky="e", padx=8, pady=8)
        self.pw_entry = ttk.Entry(form, width=30, show="*")
        self.pw_entry.grid(row=1, column=1, padx=8, pady=8)

        ttk.Button(wrapper, text="로그인", command=self._handle_login).pack(pady=18)
        self.id_entry.focus_set()

    def _handle_login(self):
        uid = self.id_entry.get().strip()
        pw = self.pw_entry.get().strip()
        if uid == LOGIN_ID and pw == LOGIN_PW:
            messagebox.showinfo("성공", "로그인 성공!")
            self._build_main_ui()
        else:
            messagebox.showerror("실패", "아이디 또는 비밀번호가 올바르지 않습니다.")

    # ------------------ 메인 UI ------------------
    def _build_main_ui(self):
        self._clear_root()
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        # 좌측 메뉴
        nav = ttk.Frame(root, padding=12)
        nav.pack(side="left", fill="y")

        ttk.Label(nav, text="Menu", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))

        menus = ["홈", "FWEE Shopee 로그인", "Numbuzin Shopee 로그인", "Fwee 송장번호 크롤링", "Numbuzin 송장번호 크롤링", "FM Fwee 크롤링", "FM Numbuzin 크롤링"]
        for m in menus:
            ttk.Radiobutton(
                nav, text=m, variable=self.current_menu, value=m, command=self._render_content
            ).pack(anchor="w", pady=4)

        ttk.Separator(nav).pack(fill="x", pady=12)

        ttk.Button(nav, text="로그아웃", command=self._logout).pack(fill="x", pady=(0, 6))
        ttk.Button(nav, text="로그인정보 초기화", command=self._clear_login_info).pack(fill="x")

        # 우측 콘텐츠
        self.content = ttk.Frame(root, padding=16)
        self.content.pack(side="left", fill="both", expand=True)

        self._render_content()

    def _logout(self):
        self._clear_login_info()
        messagebox.showinfo("안내", "로그아웃 되었습니다.")
        self._build_login_ui()

    def _clear_login_info(self):
        self.state.fwee_state_json = None
        self.state.numbuzin_state_json = None
        self.log("🧹 저장된 로그인(json) 정보 초기화 완료")

    # ------------------ 페이지 렌더 ------------------
    def _render_content(self):
        for w in self.content.winfo_children():
            w.destroy()

        menu = self.current_menu.get()

        ttk.Label(self.content, text=menu, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Separator(self.content).pack(fill="x", pady=10)

        if menu == "홈":
            ttk.Label(self.content, text="좌측 메뉴에서 작업을 선택하세요.").pack(anchor="w")
            self._build_log_box(self.content)
            return

        if menu == "FWEE Shopee 로그인":
            self._page_auth_and_crawl(
                brand="Fwee",
                login_func=fwee_login,
                run_func=fwee_run,                 # ✅ run(selected_countries) only
                country_list=FWEE_COUNTRYLIST,
                get_json=lambda: self.state.fwee_state_json,
                set_json=lambda p: setattr(self.state, "fwee_state_json", p),
            )
            return

        if menu == "Numbuzin Shopee 로그인":
            self._page_auth_and_crawl(
                brand="Numbuzin",
                login_func=num_login,
                run_func=num_run,                  # ✅ run(selected_countries) only
                country_list=NUM_COUNTRYLIST,
                get_json=lambda: self.state.numbuzin_state_json,
                set_json=lambda p: setattr(self.state, "numbuzin_state_json", p),
            )
            return
        
        if menu == "Fwee 송장번호 크롤링":
            self._page_simple_crawl("Fwee 송장번호",fw_run,fwee_countrylist)

        if menu == "Numbuzin 송장번호 크롤링":
            self._page_simple_crawl("Numbuzin 송장번호", numbuzin_run, numbuzin_country)
            return
            
        if menu == "FM Fwee 크롤링":
            self._page_simple_crawl("FM Fwee", fwee_run, FWEE_COUNTRYLIST)
            return

        if menu == "FM Numbuzin 크롤링":
            self._page_simple_crawl("FM Numbuzin", num_run, NUM_COUNTRYLIST)
            return

    # ------------------ 유틸: country_list가 dict/ list 둘 다 지원 ------------------
    @staticmethod
    def _country_keys(country_list):
        if isinstance(country_list, dict):
            return list(country_list.keys())
        return list(country_list)

    # ------------------ 유틸: login_func가 code 인자를 받으면 넣고, 아니면 그냥 실행 ------------------
    def _call_login(self, login_func, code: str | None):
        code = (code or "").strip()

        sig = inspect.signature(login_func)
        params = sig.parameters

        # 1) code라는 이름의 인자가 있으면: keyword로 넣기
        if "code" in params:
            return login_func(code=code)

        # 2) *args/**kwargs 만 있는 경우: code 넣지 말고 그냥 호출
        only_var = all(
            p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for p in params.values()
        )
        if len(params) == 0 or only_var:
            return login_func()

        # 3) positional-only / positional-or-keyword가 1개만 있으면: 그 1개에 code 넣기
        normal_params = [
            p for p in params.values()
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        ]
        if len(normal_params) == 1:
            return login_func(code)

        # 4) 그 외(파라미터 여러 개): code를 억지로 넣지 않고 그냥 호출
        return login_func()

    # ------------------ 페이지: 로그인(json 생성) + 크롤(run은 country만) ------------------
    def _page_auth_and_crawl(self, brand, login_func, run_func, country_list, get_json, set_json):
        guide = ttk.LabelFrame(self.content, text="사용 방법", padding=10)
        guide.pack(fill="x")
        for t in [
            "1. '로그인 시작' 클릭 → 브라우저에서 인증코드 입력 화면까지 진행",
            "2. 인증코드가 오면 입력 후 '인증코드 제출' 클릭",
            "3. 로그인 완료되면 json(storage_state) 파일명이 저장됩니다.",
        ]:
            ttk.Label(guide, text=t).pack(anchor="w")

        # 로그인 상태 표시
        status = ttk.LabelFrame(self.content, text="현재 로그인 상태", padding=10)
        status.pack(fill="x", pady=10)
        state_label = ttk.Label(status, text=f"storage_state: {get_json() or '없음'}")
        state_label.pack(anchor="w")

        # 인증코드 입력부
        auth = ttk.LabelFrame(self.content, text="인증코드", padding=10)
        auth.pack(fill="x", pady=10)

        code_var = tk.StringVar()
        ttk.Entry(auth, textvariable=code_var, width=40).pack(side="left")

        hint = ttk.Label(auth, text="로그인 시작 후, 인증코드가 오면 입력하고 제출하세요.")
        hint.pack(side="left", padx=10)

        # ✅ row를 먼저 만든다
        row = ttk.Frame(self.content)
        row.pack(fill="x", pady=10)

        login_btn = ttk.Button(row, text="로그인 시작")
        login_btn.pack(side="left")

        submit_btn = ttk.Button(row, text="인증코드 제출")
        submit_btn.pack(side="left", padx=8)
        submit_btn.config(state="disabled")
        
        # ✅ 스레드 대기용 Event/holder
        code_event = threading.Event()
        code_holder = {"code": ""}

        def get_code_blocking() -> str:
            """Playwright 로그인 스레드에서 호출됨. 사용자가 제출할 때까지 대기."""
            self.after(0, lambda: hint.config(text="✅ 인증코드를 입력하고 '인증코드 제출'을 누르세요."))
            code_event.clear()
            code_event.wait()
            return code_holder["code"]

        def on_submit_code():
            code = code_var.get().strip()
            if not code:
                messagebox.showwarning("안내", "인증코드를 입력하세요.")
                return
            code_holder["code"] = code
            code_event.set()
            self.log(f"🔐 [{brand}] 인증코드 제출됨")

        submit_btn.config(command=on_submit_code)

        def on_login():
            def job():
                try:
                    self.log(f"✅ [{brand}] 로그인 시작... (인증코드 대기형)")
                    self.after(0, lambda: (login_btn.config(state="disabled"),
                                        submit_btn.config(state="normal"),
                                        hint.config(text="브라우저에서 인증코드 입력 화면까지 진행 중...")))

                    # ✅ 핵심: login_func에게 get_code_blocking 콜백을 넘김
                    json_path = login_func(get_code_blocking)

                    if not json_path:
                        raise RuntimeError("login_func가 json 파일명을 반환하지 않았습니다.")

                    set_json(str(json_path))
                    self.log(f"✅ [{brand}] 로그인 완료: storage_state = {json_path}")

                    def ui_done():
                        state_label.config(text=f"storage_state: {get_json() or '없음'}")
                        messagebox.showinfo("완료", f"{brand} 로그인 완료!\n\nstorage_state:\n{json_path}")
                        hint.config(text="로그인 완료. 나라 선택 후 크롤링을 시작하세요.")
                        login_btn.config(state="normal")
                        submit_btn.config(state="disabled")

                    self.after(0, ui_done)

                except Exception as e:
                    self.log(f"❌ [{brand}] 로그인 실패: {e}")

                    def ui_err():
                        messagebox.showerror("오류", f"{brand} 로그인 실패:\n{e}")
                        hint.config(text="로그인 실패. 다시 '로그인 시작'을 눌러주세요.")
                        login_btn.config(state="normal")
                        submit_btn.config(state="disabled")

                    self.after(0, ui_err)

            threading.Thread(target=job, daemon=True).start()

        login_btn.config(command=on_login)

        self._build_log_box(self.content)

    # ------------------ 페이지: FM 크롤 (run은 country만) ------------------
    def _page_simple_crawl(self, brand, run_func, country_list):
        guide = ttk.LabelFrame(self.content, text="사용 방법", padding=10)
        guide.pack(fill="x")
        ttk.Label(guide, text="1. 나라 선택 후 '크롤링 시작' 클릭").pack(anchor="w")

        cbox = ttk.LabelFrame(self.content, text="나라 선택", padding=10)
        cbox.pack(fill="x", pady=10)

        country_vars = {}
        for c in self._country_keys(country_list):
            v = tk.BooleanVar(value=False)
            country_vars[c] = v
            ttk.Checkbutton(cbox, text=c, variable=v).pack(anchor="w")

        def on_crawl():
            selected = [c for c, v in country_vars.items() if v.get()]
            if not selected:
                messagebox.showwarning("안내", "나라를 1개 이상 선택하세요.")
                return

            def job():
                try:
                    self.log(f"🚀 [{brand}] 크롤링 시작: {', '.join(selected)}")
                    run_func(selected)  # ✅ run은 country만 받음
                    self.log(f"✅ [{brand}] 크롤링 완료")
                    messagebox.showinfo("완료", f"{brand} 크롤링이 완료되었습니다.")
                except Exception as e:
                    self.log(f"❌ [{brand}] 크롤링 실패: {e}")
                    messagebox.showerror("오류", f"{brand} 크롤링 실패:\n{e}")

            threading.Thread(target=job, daemon=True).start()

        ttk.Button(self.content, text="크롤링 시작", command=on_crawl).pack(anchor="w")
        self._build_log_box(self.content)


if __name__ == "__main__":
    App().mainloop()