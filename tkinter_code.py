# -*- coding: utf-8 -*-
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import scrolledtext
import os
import subprocess
import sys
import threading
from pathlib import Path
from datetime import datetime
import tkinter.font as tkFont

APP_DIR = Path(__file__).parent

style = ttk.Style()
FONT_FAMILY = "Segoe UI"
FONTS = {
    "title": (FONT_FAMILY, 18, "bold"),
    "header": (FONT_FAMILY, 14, "bold"),
    "section": (FONT_FAMILY, 12, "bold"),
    "body": (FONT_FAMILY, 10),
    "nav": (FONT_FAMILY, 10, "bold"),
    "mono": ("Consolas", 9),
}

COLORS = {
    "bg": "#99B0DA",
    "panel": "#F5F5F5",
    "nav_bg": "#B2E7E9",
    "accent": "#2F3A4A",
    "accent_soft": "#3791F8",
    "log_bg": "#CCD1D6",
    "log_fg": "#DADDE2",
}

MENU_ITEMS = [
    ("홈", "home"),
    ("Fwee 송장번호 크롤링", "fwee"),
    ("Numbuzin 송장번호 크롤링", "numbuzin"),
    ("FM Fwee 크롤링", "fm_fwee"),
    ("FM Numbuzin 크롤링", "fm_numbuzin"),
]

SESSION_LABELS = {
    "fwee": "Fwee",
    "numbuzin": "Numbuzin",
}

OPTIONS_FULL = ["Singapore", "Malaysia", "Thailand", "Philippines", "Vietnam", "Taiwan Xiapi"]
OPTIONS_NUMBUZIN = ["Singapore", "Malaysia", "Philippines", "Vietnam", "Taiwan Xiapi"]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Shopee 송장번호 자동화 프로그램")
        self.geometry("980x720")
        self.minsize(900, 640)

        self.logged_in = False
        self.session_procs = {}
        self.session_status = {}
        self.output_dir = tk.StringVar(value=str(APP_DIR))

        self._setup_style()
        self._build_login()

    def _setup_style(self):
        self.configure(bg=COLORS["bg"])
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"], relief="solid", borderwidth=1)
        style.configure("Nav.TFrame", background=COLORS["nav_bg"])
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["accent"], font=FONTS["title"])
        style.configure("Header.TLabel", background=COLORS["bg"], foreground=COLORS["accent"], font=FONTS["header"])
        style.configure("Section.TLabel", background=COLORS["panel"], foreground=COLORS["accent"], font=FONTS["section"])
        style.configure("Body.TLabel", background=COLORS["panel"], foreground=COLORS["accent_soft"], font=FONTS["body"])
        style.configure("Muted.TLabel", background=COLORS["panel"], foreground=COLORS["accent_soft"], font=FONTS["body"])
        style.configure("TButton", font=FONTS["body"], padding=(8, 4))
        style.configure("TLabelframe", background=COLORS["panel"], foreground=COLORS["accent"], borderwidth=1)
        style.configure("TLabelframe.Label", background=COLORS["panel"], foreground=COLORS["accent"], font=FONTS["section"])

    def _clear(self):
        for widget in self.winfo_children():
            widget.destroy()

    def _build_login(self):
        self._clear()

        root = ttk.Frame(self, style="App.TFrame", padding=24)
        root.pack(fill="both", expand=True)

        ttk.Label(root, text="Shopee 송장번호 자동화 프로그램", style="Title.TLabel").pack(anchor="w")
        ttk.Label(root, text="세션 관리와 송장 크롤링을 한 화면에서", style="Header.TLabel").pack(anchor="w", pady=(4, 18))

        card = ttk.Frame(root, style="Panel.TFrame", padding=24)
        card.pack(anchor="center", pady=10)

        ttk.Label(card, text="로그인", style="Section.TLabel").grid(row=0, column=0, columnspan=2, pady=(0, 12))

        ttk.Label(card, text="아이디", style="Body.TLabel").grid(row=1, column=0, sticky="e", padx=(0, 8), pady=6)
        ttk.Label(card, text="비밀번호", style="Body.TLabel").grid(row=2, column=0, sticky="e", padx=(0, 8), pady=6)

        self.id_var = tk.StringVar()
        self.pw_var = tk.StringVar()

        id_entry = ttk.Entry(card, textvariable=self.id_var, width=28)
        pw_entry = ttk.Entry(card, textvariable=self.pw_var, width=28, show="*")
        id_entry.grid(row=1, column=1, pady=6)
        pw_entry.grid(row=2, column=1, pady=6)

        login_btn = ttk.Button(card, text="로그인", command=self._login)
        login_btn.grid(row=3, column=0, columnspan=2, pady=(12, 0))

        id_entry.focus()

    def _login(self):
        if self.id_var.get() == "admin" and self.pw_var.get() == "admin123":
            self.logged_in = True
            self._build_main()
        else:
            messagebox.showerror("로그인 실패", "아이디 또는 비밀번호가 올바르지 않습니다.")

    def _logout(self):
        self.logged_in = False
        self._build_login()

    def _build_main(self):
        self._clear()

        top = ttk.Frame(self, style="App.TFrame", padding=(16, 14, 16, 8))
        top.pack(fill="x")

        ttk.Label(top, text="Shopee 송장번호 자동화 프로그램", style="Header.TLabel").pack(side="left")
        ttk.Button(top, text="로그아웃", command=self._logout).pack(side="right")

        mid = ttk.Frame(self, style="App.TFrame", padding=(16, 6, 16, 0))
        mid.pack(fill="both", expand=True)

        nav = ttk.Frame(mid, style="Nav.TFrame", padding=8)
        nav.pack(side="left", fill="y")

        content_wrap = ttk.Frame(mid, style="App.TFrame")
        content_wrap.pack(side="left", fill="both", expand=True, padx=(12, 0))

        settings = ttk.Frame(content_wrap, style="Panel.TFrame", padding=12)
        settings.pack(fill="x")
        self._build_path_selector(settings)

        pages = ttk.Frame(content_wrap, style="App.TFrame")
        pages.pack(fill="both", expand=True, pady=(12, 0))

        self.menu_list = tk.Listbox(
            nav,
            exportselection=False,
            height=len(MENU_ITEMS),
            width=24,
            bg=COLORS["nav_bg"],
            fg=COLORS["accent"],
            selectbackground=COLORS["accent"],
            selectforeground="#FFFFFF",
            font=FONTS["nav"],
            highlightthickness=0,
            bd=0,
        )
        for label, _ in MENU_ITEMS:
            self.menu_list.insert(tk.END, label)
        self.menu_list.pack(fill="y")
        self.menu_list.bind("<<ListboxSelect>>", self._on_menu_select)

        self.frames = {}
        for _, key in MENU_ITEMS:
            frame = ttk.Frame(pages, style="App.TFrame")
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)
            self.frames[key] = frame

        self._build_home(self.frames["home"])
        self._build_fwee(self.frames["fwee"])
        self._build_numbuzin(self.frames["numbuzin"])
        self._build_fm_fwee(self.frames["fm_fwee"])
        self._build_fm_numbuzin(self.frames["fm_numbuzin"])

        self.menu_list.selection_set(0)
        self._show_frame("home")

        log_wrap = ttk.Frame(self, style="App.TFrame", padding=(16, 8, 16, 16))
        log_wrap.pack(fill="x")

        log_panel = ttk.Frame(log_wrap, style="Panel.TFrame", padding=10)
        log_panel.pack(fill="x")

        header = ttk.Frame(log_panel, style="Panel.TFrame")
        header.pack(fill="x")
        ttk.Label(header, text="실행 로그", style="Section.TLabel").pack(side="left")
        ttk.Button(header, text="로그 지우기", command=self._clear_log).pack(side="right")

        self.log_text = scrolledtext.ScrolledText(
            log_panel,
            height=8,
            wrap="word",
            font=FONTS["mono"],
            bg=COLORS["log_bg"],
            fg=COLORS["log_fg"],
            insertbackground=COLORS["accent"],
            relief="flat",
        )
        self.log_text.pack(fill="x", pady=(8, 0))
        self.log_text.configure(state="disabled")

        self._append_log("앱이 시작되었습니다.")

    def _on_menu_select(self, _event):
        selection = self.menu_list.curselection()
        if not selection:
            return
        _, key = MENU_ITEMS[selection[0]]
        self._show_frame(key)

    def _show_frame(self, key):
        frame = self.frames.get(key)
        if frame:
            frame.tkraise()

    def _build_home(self, parent):
        card = ttk.Frame(parent, style="Panel.TFrame", padding=18)
        card.pack(fill="both", expand=False)
        ttk.Label(card, text="홈", style="Section.TLabel").pack(anchor="w")
        ttk.Label(card, text="Shopee 송장번호 자동화 프로그램에 오신 것을 환영합니다.", style="Body.TLabel").pack(anchor="w", pady=(6, 0))

    def _build_path_selector(self, parent):
        ttk.Label(parent, text="저장 경로", style="Section.TLabel").pack(anchor="w")

        row = ttk.Frame(parent, style="Panel.TFrame")
        row.pack(fill="x", pady=(6, 0))

        entry = ttk.Entry(row, textvariable=self.output_dir, width=70)
        entry.pack(side="left", fill="x", expand=True)

        ttk.Button(row, text="폴더 선택", command=self._choose_output_dir).pack(side="left", padx=(8, 0))

        note = ttk.Label(parent, text="선택한 경로는 OUTPUT_DIR 환경변수로 전달됩니다.", style="Muted.TLabel")
        note.pack(anchor="w", pady=(6, 0))

    def _choose_output_dir(self):
        initial = self.output_dir.get() or str(APP_DIR)
        path = filedialog.askdirectory(title="저장 폴더 선택", initialdir=initial)
        if path:
            self.output_dir.set(path)
            self._log(f"저장 경로 변경: {path}")

    def _build_auth_section(self, parent, session_key, script_name):
        auth = ttk.LabelFrame(parent, text="로그인 세션", padding=12)
        auth.pack(fill="x", pady=(12, 10))

        ttk.Label(auth, text="'로그인 세션' 버튼 클릭 -> 인증코드 입력 -> 반드시 '확인' 버튼 클릭", style="Body.TLabel").pack(anchor="w", pady=(0, 4))
        ttk.Label(auth, text="30초 정도 대기 후 진행하세요.", style="Body.TLabel").pack(anchor="w", pady=(0, 10))

        status_var = tk.StringVar(value="대기 중")
        self.session_status[session_key] = status_var
        ttk.Label(auth, textvariable=status_var, style="Muted.TLabel").pack(anchor="w", pady=(0, 8))

        btn_frame = ttk.Frame(auth, style="Panel.TFrame")
        btn_frame.pack(fill="x", pady=(0, 8))

        ttk.Button(
            btn_frame,
            text=f"{SESSION_LABELS.get(session_key, session_key)} 로그인 세션 시작",
            command=lambda: self._start_session(session_key, script_name),
        ).pack(side="left")

        code_frame = ttk.Frame(auth, style="Panel.TFrame")
        code_frame.pack(fill="x")

        ttk.Label(code_frame, text="인증코드", style="Body.TLabel").pack(side="left")
        code_var = tk.StringVar()
        code_entry = ttk.Entry(code_frame, textvariable=code_var, width=24)
        code_entry.pack(side="left", padx=(8, 8))
        ttk.Button(
            code_frame,
            text="확인",
            command=lambda: self._submit_code(session_key, code_var.get()),
        ).pack(side="left")

    def _build_country_section(self, parent, options, script_name, label):
        box = ttk.LabelFrame(parent, text="나라 선택", padding=12)
        box.pack(fill="x", pady=(6, 0))

        ttk.Label(box, text="나라를 선택하세요:", style="Body.TLabel").pack(anchor="w", pady=(0, 6))
        listbox = tk.Listbox(
            box,
            selectmode=tk.MULTIPLE,
            height=min(8, len(options)),
            bg="#FFFFFF",
            fg=COLORS["accent"],
            selectbackground=COLORS["accent"],
            selectforeground="#FFFFFF",
            relief="solid",
            bd=1,
        )
        for option in options:
            listbox.insert(tk.END, option)
        listbox.pack(fill="x", pady=(0, 8))

        ttk.Button(box, text="크롤링 시작", command=lambda: self._run_crawling(script_name, listbox, label)).pack()

    def _build_fwee(self, parent):
        ttk.Label(parent, text="Fwee 송장번호 크롤링", style="Header.TLabel").pack(anchor="w")
        self._build_auth_section(parent, "fwee", "fwee_auth_login_once.py")
        self._build_country_section(parent, OPTIONS_FULL, "fwee_crawling.py", "Fwee 크롤링")

    def _build_numbuzin(self, parent):
        ttk.Label(parent, text="Numbuzin 송장번호 크롤링", style="Header.TLabel").pack(anchor="w")
        self._build_auth_section(parent, "numbuzin", "numbuzin_auth_login_once.py")
        self._build_country_section(parent, OPTIONS_NUMBUZIN, "numbuzin_crawling.py", "Numbuzin 크롤링")

    def _build_fm_fwee(self, parent):
        ttk.Label(parent, text="FM Fwee 크롤링", style="Header.TLabel").pack(anchor="w")
        self._build_country_section(parent, OPTIONS_FULL, "FM_fwee_crawling.py", "FM Fwee 크롤링")

    def _build_fm_numbuzin(self, parent):
        ttk.Label(parent, text="FM Numbuzin 크롤링", style="Header.TLabel").pack(anchor="w")
        self._build_country_section(parent, OPTIONS_FULL, "FM_numbuzin_crawling.py", "FM Numbuzin 크롤링")

    def _set_session_status(self, session_key, text):
        var = self.session_status.get(session_key)
        if var:
            var.set(text)

    def _start_session(self, session_key, script_name):
        script_path = APP_DIR / script_name
        proc = self.session_procs.get(session_key)
        if proc and proc.poll() is None:
            messagebox.showwarning("세션 실행 중", "이미 실행 중인 세션이 있습니다.")
            return

        try:
            env = os.environ.copy()
            if self.output_dir.get():
                env["OUTPUT_DIR"] = self.output_dir.get()
            proc = subprocess.Popen(
                [sys.executable, str(script_path)],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=script_path.parent,
                env=env,
            )
            self.session_procs[session_key] = proc
            self._set_session_status(session_key, "실행 중")
            self._log(f"{SESSION_LABELS.get(session_key, session_key)} 세션 시작됨.")
            threading.Thread(
                target=self._stream_process_output,
                args=(proc, f"{SESSION_LABELS.get(session_key, session_key)} 세션", session_key),
                daemon=True,
            ).start()
            messagebox.showinfo("세션 시작됨", "세션 시작됨. 인증코드 입력 후 확인하세요.")
        except Exception as exc:
            messagebox.showerror("실행 실패", str(exc))

    def _submit_code(self, session_key, code):
        proc = self.session_procs.get(session_key)
        if not proc or proc.poll() is not None:
            messagebox.showerror("오류", "실행 중인 세션이 없습니다.")
            return
        if not code.strip():
            messagebox.showwarning("경고", "인증코드를 입력하세요.")
            return

        try:
            proc.stdin.write(code.strip() + "\n")
            proc.stdin.flush()
            self._log(f"{SESSION_LABELS.get(session_key, session_key)} 인증코드 전송")
            messagebox.showinfo("인증 완료", "인증 완료")
        except Exception as exc:
            messagebox.showerror("오류", str(exc))

    def _run_crawling(self, script_name, listbox, label):
        selected = [listbox.get(i) for i in listbox.curselection()]
        if not selected:
            messagebox.showwarning("선택 필요", "나라를 선택하세요.")
            return

        script_path = APP_DIR / script_name

        def worker():
            self._log(f"{label} 시작: {', '.join(selected)}")
            try:
                env = os.environ.copy()
                if self.output_dir.get():
                    env["OUTPUT_DIR"] = self.output_dir.get()
                proc = subprocess.Popen(
                    [sys.executable, str(script_path), *selected],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=script_path.parent,
                    env=env,
                )
                for line in proc.stdout:
                    self._log(line.rstrip(), prefix=label)
                code = proc.wait()
                if code == 0:
                    self.after(0, lambda: messagebox.showinfo("완료", "크롤링이 완료되었습니다."))
                else:
                    self.after(0, lambda: messagebox.showerror("오류", f"크롤링이 실패했습니다. 코드: {code}"))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("오류", str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _stream_process_output(self, proc, label, session_key=None):
        for line in proc.stdout:
            self._log(line.rstrip(), prefix=label)
        if session_key:
            self.after(0, lambda: self._set_session_status(session_key, "종료됨"))
            self._log(f"{SESSION_LABELS.get(session_key, session_key)} 세션 종료")

    def _append_log(self, message, prefix=None):
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix_text = f"[{prefix}] " if prefix else ""
        line = f"{timestamp} {prefix_text}{message}\n"
        self.log_text.configure(state="normal")
        self.log_text.insert("end", line)
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _log(self, message, prefix=None):
        self.after(0, lambda: self._append_log(message, prefix))

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


if __name__ == "__main__":
    app = App()
    app.mainloop()
