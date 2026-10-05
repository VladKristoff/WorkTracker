from tkinter import *
from tkinter import ttk, messagebox
from PIL import Image, ImageTk

class MainMenu:
    def __init__(self, main_frame, app):
        self.main_frame = main_frame
        self.app = app

        self.create_widgets()

    def create_widgets(self):
        canvas = Canvas(self.main_frame, bg='white', height=200, width=200, bd=0, highlightthickness=0)
        canvas.pack(pady=50)

        pil_img = Image.open('images/clue.png')

        resized_img = pil_img.resize((200, 200), Image.Resampling.LANCZOS)

        self.logo_img = ImageTk.PhotoImage(resized_img)

        logo = canvas.create_image(0, 0, anchor=NW, image=self.logo_img)

        ttk.Label(self.main_frame, text="Work Tracer", style="BigBlueLabel.TLabel").pack(side="top")

