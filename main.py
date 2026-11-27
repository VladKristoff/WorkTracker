import tkinter as tk

from app import AppWorkTracker
from view.pages.builder_page import ExcelBuilderPage
from view.pages.charts_page import VisualizationPage
from view.pages.controls_page import ControlPage
from view.pages.overview_page import OverviewPage
from view.pages.start_page import StartPage
from view.pages.student_page import StudentPage
from view.pages.students_page import StudentsPage

PAGES = {
    "main_menu": StartPage,
    "overview_page": OverviewPage,
    "students_page": StudentsPage,
    "student_page": StudentPage,
    "control_page": ControlPage,
    "visualization_page": VisualizationPage,
    "excel_builder_page": ExcelBuilderPage,
}

if __name__ == "__main__":
    root = tk.Tk()
    app = AppWorkTracker(root)
    for name, page in PAGES.items():
        app.register_page(name, page)
    app.show_window("main_menu")
    root.mainloop()
