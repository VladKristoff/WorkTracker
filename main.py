import tkinter as tk

from app import AppWorkTracker
from view.main_menu import MainMenu
from view.excel_builder_page import ExcelBuilderPage
from view.analytics.students_page import StudentsPage
from view.analytics.visualization_page import VisualizationPage
from view.analytics.control_page import ControlPage

if __name__ == "__main__":
    root = tk.Tk()
    app = AppWorkTracker(root)

    app.register_page("main_menu", MainMenu)
    app.register_page("excel_builder_page", ExcelBuilderPage)
    app.register_page("students_page", StudentsPage)
    app.register_page("visualization_page", VisualizationPage)
    app.register_page("control_page", ControlPage)

    app.show_window("main_menu")

    root.mainloop()