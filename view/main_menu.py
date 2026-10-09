from tkinter import *
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

class MainMenu:
    def __init__(self, main_frame, app):
        self.main_frame = main_frame
        self.app = app

        self.create_widgets()

    def create_widgets(self):
        canvas = Canvas(self.main_frame, bg='white', height=100, width=100, bd=0, highlightthickness=0)
        canvas.pack(pady=(150, 0))

        pil_img = Image.open('images/app_ico.png')

        resized_img = pil_img.resize((100, 100), Image.Resampling.LANCZOS)

        self.logo_img = ImageTk.PhotoImage(resized_img)

        canvas.create_image(0, 0, anchor=NW, image=self.logo_img)

        ttk.Label(self.main_frame, text="Work Tracking", style="BigLabel.TLabel").pack(side="top")

        upload_btn = ttk.Button(self.main_frame,
                                text="Загрузить файл",
                                cursor='hand2',
                                command=self.open_analytics_page,
                                style="BlueButton.TButton")
        upload_btn.pack(pady=100)

        Label(self.main_frame, background="white", text="Для начала работы загрузите файл с данными успеваемости. Поддерживаемый формат: .xlsx").pack(side="bottom")

    def open_analytics_page(self):
        file_path = filedialog.askopenfilename(title="Выберите файл")
        if file_path:
            self.app.show_window("groups_page", file_path)



