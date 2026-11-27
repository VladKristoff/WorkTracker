"""Загрузка Excel-файла из любого места программы (парсинг идёт в отдельном потоке)."""
import queue
import threading
from tkinter import ttk, messagebox, filedialog

from database.repository import database_has_data
from utils.parser import UniversityParser, ParseError
from utils.settings import save_setting


class FileLoader:
    def __init__(self, app):
        self.app = app
        self.results = queue.Queue()
        self.overlay = None

    @property
    def busy(self):
        return self.overlay is not None

    def open(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(title="Выберите файл",
                                          filetypes=[("Excel файлы", "*.xlsx")])
        if not path:
            return
        if database_has_data() and not messagebox.askyesno(
                "Заменить данные?",
                "В программе уже есть загруженные данные.\n"
                "Они будут заменены данными из нового файла. Продолжить?"):
            return
        self._show_overlay()
        threading.Thread(target=self._worker, args=(path,), daemon=True).start()
        self.app.root.after(100, self._poll, path)

    def _show_overlay(self):
        # Экран загрузки закрывает окно целиком: пока база заменяется, нажимать нечего
        self.overlay = ttk.Frame(self.app.root)
        self.overlay.place(x=0, y=0, relwidth=1, relheight=1)
        box = ttk.Frame(self.overlay)
        box.place(relx=0.5, rely=0.5, anchor="center")
        ttk.Label(box, text="Обработка файла…", style="Lead.TLabel").pack(pady=(0, 12))
        progress = ttk.Progressbar(box, mode="indeterminate", length=320)
        progress.pack()
        progress.start(12)
        self.overlay.focus_set()

    def _worker(self, path):
        try:
            parser = UniversityParser(excel_file=path, verbose=False)
            self.results.put(("ok", parser.parse()))
        except ParseError as e:
            self.results.put(("error", str(e)))
        except Exception as e:
            self.results.put(("error", f"Непредвиденная ошибка: {e}"))

    def _poll(self, path):
        try:
            status, payload = self.results.get_nowait()
        except queue.Empty:
            self.app.root.after(100, self._poll, path)
            return
        self.overlay.destroy()
        self.overlay = None
        if status == "error":
            messagebox.showerror("Не удалось загрузить файл", payload)
            return
        warnings = payload.get("warnings", [])
        save_setting("last_file", path)
        save_setting("last_warnings", warnings)  # показываются на странице «Обзор»
        self.app.file_loaded(path, warnings)
