from tkinter import *
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk

class GroupsPage:
    def __init__(self, main_frame, app, filepath):
        self.main_frame = main_frame
        self.app = app
        self.filepath = filepath

        self.create_widgets()

    def create_widgets(self):
        Label(self.main_frame, text=f"{self.filepath}").pack(side="bottom")