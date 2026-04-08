# -*- coding: utf-8 -*-
import inspect
import os
import queue
import sys
import threading
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox, ttk

from dotenv import load_dotenv


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_dir()
BROWSERS_DIR = APP_DIR / "pw-browsers"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(BROWSERS_DIR)
os.environ["PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD"] = "1"

from FM_tage_crawling import TAGE_COUNTRYLIST, run as fm_tage_run
from tage_crawling import run as tage_run
from tage_crawling import tage_countrylist

load_dotenv()

LOGIN_ID = os.getenv("TKINT_ID")
LOGIN_PW = os.getenv("TKINT_PW")


@dataclass
class AppState:
    tage_state_json: str | None = None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shopee 송장번호 자동화 프로그램")
        self.geometry("1100x720")
        self.minsize(1000, 650)

        self.state = AppState()
        self.logq = queue.Queue()
        self.current_menu = tk.StringVar(value="홈")

        self._build_login_ui()
        self.after(100, self._drain_logq)

    def log(self, msg: str):
        self.logq.put(msg if msg.endswith("\n") else msg + "\n")

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

    def _build_log_box(self, parent):
        box = ttk.LabelFrame(parent, text="실행 로그", padding=10)
        box.pack(fill="both", expand=True, pady=10)

        self.log_text = tk.Text(box, height=18, wrap="word")
        self.log_text.pack(fill="both", expand=True)

        btns = ttk.Frame(parent)
        btns.pack(fill="x")
        ttk.Button(
            btns,
            text="로그 지우기",
            command=lambda: self.log_text.delete("1.0", "end"),
        ).pack(side="left")

    def _clear_root(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _build_login_ui(self):
        self._clear_root()
        wrapper = ttk.Frame(self, padding=30)
        wrapper.pack(fill="both", expand=True)

        ttk.Label(wrapper, text="로그인", font=("Segoe UI", 18, "bold")).pack(
            pady=(0, 20)
        )

        form = ttk.Frame(wrapper)
        form.pack()

        ttk.Label(form, text="아이디").grid(row=0, column=0, sticky="e", padx=8, pady=8)
        self.id_entry = ttk.Entry(form, width=30)
        self.id_entry.grid(row=0, column=1, padx=8, pady=8)

        ttk.Label(form, text="비밀번호").grid(
            row=1, column=0, sticky="e", padx=8, pady=8
        )
        self.pw_entry = ttk.Entry(form, width=30, show="*")
        self.pw_entry.grid(row=1, column=1, padx=8, pady=8)

        ttk.Button(wrapper, text="로그인", command=self._handle_login).pack(pady=18)
        self.id_entry.focus_set()

    def _handle_login(self):
        uid = self.id_entry.get().strip()
        pw = self.pw_entry.get().strip()
        if uid == LOGIN_ID and pw == LOGIN_PW:
            messagebox.showinfo("성공", "로그인 성공")
            self._build_main_ui()
            return
        messagebox.showerror("실패", "아이디 또는 비밀번호가 올바르지 않습니다.")

    def _build_main_ui(self):
        self._clear_root()
        root = ttk.Frame(self)
        root.pack(fill="both", expand=True)

        nav = ttk.Frame(root, padding=12)
        nav.pack(side="left", fill="y")

        ttk.Label(nav, text="Menu", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(0, 10)
        )

        menus = [
            "홈",
            "TAGE Shopee 로그인",
            "TAGE 송장번호 크롤링",
            "FM TAGE 크롤링",
        ]
        for menu in menus:
            ttk.Radiobutton(
                nav,
                text=menu,
                variable=self.current_menu,
                value=menu,
                command=self._render_content,
            ).pack(anchor="w", pady=4)

        ttk.Separator(nav).pack(fill="x", pady=12)
        ttk.Button(nav, text="로그아웃", command=self._logout).pack(fill="x", pady=(0, 6))
        ttk.Button(nav, text="로그인 정보 초기화", command=self._clear_login_info).pack(
            fill="x"
        )

        self.content = ttk.Frame(root, padding=16)
        self.content.pack(side="left", fill="both", expand=True)
        self._render_content()

    def _logout(self):
        self._clear_login_info()
        messagebox.showinfo("안내", "로그아웃했습니다.")
        self._build_login_ui()

    def _clear_login_info(self):
        self.state.tage_state_json = None
        self.log("[TAGE] 저장된 로그인 json 정보를 초기화했습니다.")

    def _render_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

        menu = self.current_menu.get()
        ttk.Label(self.content, text=menu, font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Separator(self.content).pack(fill="x", pady=10)

        if menu == "홈":
            ttk.Label(
                self.content, text="왼쪽 메뉴에서 작업을 선택하세요."
            ).pack(anchor="w")
            self._build_log_box(self.content)
            return

        if menu == "TAGE Shopee 로그인":
            from tage_auth_login_once import run_login_once as tage_login

            self._page_auth_and_crawl(
                brand="TAGE",
                login_func=tage_login,
                get_json=lambda: self.state.tage_state_json,
                set_json=lambda p: setattr(self.state, "tage_state_json", p),
            )
            return

        if menu == "TAGE 송장번호 크롤링":
            self._page_simple_crawl("TAGE 송장번호", tage_run, tage_countrylist)
            return

        if menu == "FM TAGE 크롤링":
            self._page_simple_crawl("FM TAGE", fm_tage_run, TAGE_COUNTRYLIST)
            return

    @staticmethod
    def _country_keys(country_list):
        if isinstance(country_list, dict):
            return list(country_list.keys())
        return list(country_list)

    def _page_auth_and_crawl(self, brand, login_func, get_json, set_json):
        guide = ttk.LabelFrame(self.content, text="사용 방법", padding=10)
        guide.pack(fill="x")
        for text in [
            "1. '로그인 시작'을 누르면 브라우저가 열립니다.",
            "2. 인증 코드가 뜨면 입력 후 '인증코드 제출'을 누르세요.",
            "3. 완료되면 storage_state json 경로가 저장됩니다.",
        ]:
            ttk.Label(guide, text=text).pack(anchor="w")

        status = ttk.LabelFrame(self.content, text="현재 로그인 상태", padding=10)
        status.pack(fill="x", pady=10)
        state_label = ttk.Label(status, text=f"storage_state: {get_json() or '없음'}")
        state_label.pack(anchor="w")

        auth = ttk.LabelFrame(self.content, text="인증코드", padding=10)
        auth.pack(fill="x", pady=10)

        code_var = tk.StringVar()
        ttk.Entry(auth, textvariable=code_var, width=40).pack(side="left")
        hint = ttk.Label(auth, text="브라우저에서 인증코드가 보이면 입력 후 제출하세요.")
        hint.pack(side="left", padx=10)

        row = ttk.Frame(self.content)
        row.pack(fill="x", pady=10)

        login_btn = ttk.Button(row, text="로그인 시작")
        login_btn.pack(side="left")

        submit_btn = ttk.Button(row, text="인증코드 제출", state="disabled")
        submit_btn.pack(side="left", padx=8)

        code_event = threading.Event()
        code_holder = {"code": ""}

        def get_code_blocking() -> str:
            self.after(
                0,
                lambda: hint.config(
                    text="인증코드를 입력하고 '인증코드 제출'을 눌러주세요."
                ),
            )
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
            self.log(f"[{brand}] 인증코드 제출 완료")

        submit_btn.config(command=on_submit_code)

        def on_login():
            def job():
                try:
                    self.log(f"[{brand}] 로그인 시작")
                    self.after(
                        0,
                        lambda: (
                            login_btn.config(state="disabled"),
                            submit_btn.config(state="normal"),
                            hint.config(text="브라우저에서 인증 절차를 진행하세요."),
                        ),
                    )

                    json_path = login_func(get_code_blocking)
                    if not json_path:
                        raise RuntimeError("login_func가 json 파일 경로를 반환하지 않았습니다.")

                    set_json(str(json_path))
                    self.log(f"[{brand}] 로그인 완료: {json_path}")

                    def ui_done():
                        state_label.config(text=f"storage_state: {get_json() or '없음'}")
                        messagebox.showinfo(
                            "완료",
                            f"{brand} 로그인 완료\n\nstorage_state:\n{json_path}",
                        )
                        hint.config(text="로그인 완료. 이제 크롤링을 실행하세요.")
                        login_btn.config(state="normal")
                        submit_btn.config(state="disabled")

                    self.after(0, ui_done)
                except Exception as exc:
                    self.log(f"[{brand}] 로그인 실패: {exc}")

                    def ui_error():
                        messagebox.showerror("오류", f"{brand} 로그인 실패:\n{exc}")
                        hint.config(text="로그인에 실패했습니다. 다시 시도하세요.")
                        login_btn.config(state="normal")
                        submit_btn.config(state="disabled")

                    self.after(0, ui_error)

            threading.Thread(target=job, daemon=True).start()

        login_btn.config(command=on_login)
        self._build_log_box(self.content)

    def _page_simple_crawl(self, brand, run_func, country_list):
        guide = ttk.LabelFrame(self.content, text="사용 방법", padding=10)
        guide.pack(fill="x")
        ttk.Label(guide, text="1. 국가를 선택한 뒤 '크롤링 시작'을 누르세요.").pack(
            anchor="w"
        )

        cbox = ttk.LabelFrame(self.content, text="국가 선택", padding=10)
        cbox.pack(fill="x", pady=10)

        country_vars = {}
        for country in self._country_keys(country_list):
            var = tk.BooleanVar(value=False)
            country_vars[country] = var
            ttk.Checkbutton(cbox, text=country, variable=var).pack(anchor="w")

        supports_progress = "progress_callback" in inspect.signature(run_func).parameters
        status_vars = None

        if supports_progress:
            status_box = ttk.LabelFrame(self.content, text="PDF 진행 현황", padding=10)
            status_box.pack(fill="x", pady=10)

            status_vars = {
                "parcel_count": tk.StringVar(value="Shopee 페이지 PDF 수: 0"),
                "downloaded_pages": tk.StringVar(value="실제 다운로드 수: 0"),
                "merged_downloaded_pages": tk.StringVar(value="합산 총 다운로드 장수: 0"),
            }

            ttk.Label(status_box, textvariable=status_vars["parcel_count"]).pack(
                anchor="w"
            )
            ttk.Label(status_box, textvariable=status_vars["downloaded_pages"]).pack(
                anchor="w", pady=(4, 0)
            )
            ttk.Label(
                status_box, textvariable=status_vars["merged_downloaded_pages"]
            ).pack(anchor="w", pady=(4, 0))

        crawl_btn = ttk.Button(self.content, text="크롤링 시작")
        crawl_btn.pack(anchor="w")

        def update_progress(payload):
            if status_vars is None:
                return

            def apply_payload():
                shopee_page_count = payload.get(
                    "parcel_count", payload.get("shopee_total_pages", 0)
                )
                downloaded_pages = payload.get("downloaded_pages", 0)
                merged_downloaded_pages = payload.get("merged_downloaded_pages", 0)

                status_vars["parcel_count"].set(
                    f"Shopee 페이지 PDF 수: {shopee_page_count}"
                )
                status_vars["downloaded_pages"].set(
                    f"실제 다운로드 수: {downloaded_pages}"
                )
                status_vars["merged_downloaded_pages"].set(
                    f"합산 총 다운로드 장수: {merged_downloaded_pages}"
                )

            self.after(0, apply_payload)

        def on_crawl():
            selected = [country for country, var in country_vars.items() if var.get()]
            if not selected:
                messagebox.showwarning("안내", "국가를 1개 이상 선택하세요.")
                return

            crawl_btn.config(state="disabled")
            if status_vars is not None:
                status_vars["parcel_count"].set("Shopee 페이지 PDF 수: 0")
                status_vars["downloaded_pages"].set("실제 다운로드 수: 0")
                status_vars["merged_downloaded_pages"].set("합산 총 다운로드 장수: 0")

            def job():
                try:
                    self.log(f"[{brand}] 크롤링 시작: {', '.join(selected)}")
                    if supports_progress:
                        result = run_func(selected, progress_callback=update_progress)
                        if isinstance(result, dict):
                            update_progress(result)
                    else:
                        run_func(selected)
                    self.log(f"[{brand}] 크롤링 완료")
                    self.after(
                        0,
                        lambda: messagebox.showinfo(
                            "완료", f"{brand} 크롤링이 완료되었습니다."
                        ),
                    )
                except Exception as exc:
                    self.log(f"[{brand}] 크롤링 실패: {exc}")
                    self.after(
                        0,
                        lambda: messagebox.showerror(
                            "오류", f"{brand} 크롤링 실패:\n{exc}"
                        ),
                    )
                finally:
                    self.after(0, lambda: crawl_btn.config(state="normal"))

            threading.Thread(target=job, daemon=True).start()

        crawl_btn.config(command=on_crawl)
        self._build_log_box(self.content)


if __name__ == "__main__":
    App().mainloop()
