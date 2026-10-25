import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from PIL import Image, ImageTk

from config import ICON_PATH
from database.repository import database_has_data
from utils.parser import UniversityParser, ParseError
from utils.settings import load_settings, save_setting


class MainMenu:
    def __init__(self, main_frame, app):
        self.main_frame = main_frame
        self.app = app
        self.result_queue = queue.Queue()
        self.is_loading = False

        self.create_widgets()

    def create_widgets(self):
        canvas = tk.Canvas(self.main_frame, bg="white", height=100, width=100, bd=0,
                           highlightthickness=0)
        canvas.pack(pady=(120, 0))
        try:
            pil_img = Image.open(ICON_PATH).resize((100, 100), Image.Resampling.LANCZOS)
            self.logo_img = ImageTk.PhotoImage(pil_img)
            canvas.create_image(0, 0, anchor=tk.NW, image=self.logo_img)
        except (OSError, FileNotFoundError):
            pass  # без логотипа меню остаётся рабочим

        ttk.Label(self.main_frame, text="Work Tracking", style="BigLabel.TLabel").pack(side="top")

        buttons = ttk.Frame(self.main_frame)
        buttons.pack(pady=70)

        self.upload_btn = ttk.Button(buttons, text="Загрузить файл", cursor="hand2",
                                     command=self.open_analytics_page, style="BlueButton.TButton")
        self.upload_btn.pack()

        # Если данные уже загружались, даём продолжить без повторной загрузки xlsx
        last_file = load_settings().get("last_file")
        if last_file and database_has_data():
            self.continue_btn = ttk.Button(buttons, text="Продолжить с последними данными",
                                           cursor="hand2", style="Secondary.TButton",
                                           command=lambda: self.app.show_window("students_page", last_file))
            self.continue_btn.pack(pady=(15, 0))
            ttk.Label(buttons, text=os.path.basename(last_file),
                      style="Hint.TLabel").pack(pady=(4, 0))

        self.progress = ttk.Progressbar(self.main_frame, mode="indeterminate", length=320)
        self.status_label = ttk.Label(self.main_frame, text="", style="Hint.TLabel")

        ttk.Label(self.main_frame, style="Hint.TLabel",
                  text="Для начала работы загрузите файл с данными успеваемости. "
                       "Поддерживаемый формат: .xlsx").pack(side="bottom", pady=15)

    # ------------------------------------------------------------------

    def open_analytics_page(self):
        if self.is_loading:
            return
        file_path = filedialog.askopenfilename(title="Выберите файл",
                                               filetypes=[("Excel файлы", "*.xlsx")])
        if not file_path:
            return

        if database_has_data() and not messagebox.askyesno(
                "Заменить данные?",
                "В программе уже есть загруженные данные.\n"
                "Они будут заменены данными из нового файла. Продолжить?"):
            return

        self.set_loading(True)
        # Парсинг в отдельном потоке, чтобы окно не зависало на больших файлах
        threading.Thread(target=self._parse_worker, args=(file_path,), daemon=True).start()
        self.main_frame.after(100, self._poll_result, file_path)

    def _parse_worker(self, file_path):
        try:
            parser = UniversityParser(excel_file=file_path, verbose=False)
            self.result_queue.put(("ok", parser.parse()))
        except ParseError as e:
            self.result_queue.put(("error", str(e)))
        except Exception as e:
            self.result_queue.put(("error", f"Непредвиденная ошибка: {e}"))

    def _poll_result(self, file_path):
        try:
            status, payload = self.result_queue.get_nowait()
        except queue.Empty:
            if self.main_frame.winfo_exists():
                self.main_frame.after(100, self._poll_result, file_path)
            return

        self.set_loading(False)
        if status == "error":
            messagebox.showerror("Не удалось загрузить файл", payload)
            return

        save_setting("last_file", file_path)
        warnings = payload.get("warnings", [])
        if warnings:
            shown = "\n• ".join(warnings[:8])
            extra = f"\n… и ещё {len(warnings) - 8}" if len(warnings) > 8 else ""
            messagebox.showwarning(
                "Файл загружен с замечаниями",
                f"Студентов: {payload['students']}, работ: {payload['activities']}.\n\n"
                f"Что стоит проверить в файле:\n• {shown}{extra}")
        self.app.show_window("students_page", file_path)

    def set_loading(self, loading: bool):
        self.is_loading = loading
        if loading:
            self.upload_btn.config(state=tk.DISABLED)
            self.status_label.config(text="Обработка файла…")
            self.status_label.pack()
            self.progress.pack(pady=5)
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.pack_forget()
            self.status_label.pack_forget()
            self.upload_btn.config(state=tk.NORMAL)
