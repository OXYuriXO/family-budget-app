import os
os.environ["KIVY_HOME"] = "/tmp/kivyhome"
import sys
sys.path.insert(0, os.path.dirname(__file__))

from kivy.clock import Clock
from kivy.core.window import Window
from main import BudgetApp

app = BudgetApp()

steps = []


def step_screenshot(name):
    def _f(dt):
        Window.screenshot(name=f"/home/claude/family_budget_app/shot_{name}.png")
    return _f


def do_open_add(dt):
    dash = app.root
    dash.open_add_expense()


def do_fill_and_save(dt):
    # find the open popup's content
    from kivy.uix.popup import Popup
    popup = None
    for child in Window.children:
        if isinstance(child, Popup):
            popup = child
            break
    assert popup is not None, "popup not found"
    content = popup.content.expense_content
    # simulate pressing keys 1,2,5,0 -> amount 1250
    for k in ["1", "2", "5", "0"]:
        content._on_key(k)
    # pick a category
    chip = content.cats_grid.children[-1]
    content._select_category(chip, chip.text)
    content._save()


def do_open_incomes(dt):
    dash = app.root
    dash.open_incomes()


def do_fill_incomes(dt):
    from kivy.uix.popup import Popup
    popup = None
    for child in Window.children:
        if isinstance(child, Popup):
            popup = child
            break
    assert popup is not None, "incomes popup not found"
    content = popup.content
    content.husband_input.text = "60000"
    content.wife_input.text = "45000"
    content._save()


def do_export(dt):
    dash = app.root
    dash.export_xlsx()


def do_check(dt):
    dash = app.root
    print("SUMMARY:", dash.storage.summary())
    print("EXPENSES:", [dict(r) for r in dash.storage.list_expenses()])
    app.stop()


Clock.schedule_once(step_screenshot("dashboard_empty"), 0.5)
Clock.schedule_once(do_open_add, 1)
Clock.schedule_once(step_screenshot("add_popup"), 1.5)
Clock.schedule_once(do_fill_and_save, 2)
Clock.schedule_once(step_screenshot("dashboard_after"), 2.5)
Clock.schedule_once(do_open_incomes, 3)
Clock.schedule_once(step_screenshot("incomes_popup"), 3.5)
Clock.schedule_once(do_fill_incomes, 4)
Clock.schedule_once(step_screenshot("dashboard_incomes"), 4.5)
Clock.schedule_once(do_export, 5)
Clock.schedule_once(step_screenshot("export_popup"), 5.5)
Clock.schedule_once(do_check, 6)

app.run()
