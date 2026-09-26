"""
Бюджет семьи — простое Android-приложение на Python/Kivy.
Аналог таблицы "Расходы_семьи.xlsx":
  Доход мужа / Доход жены / Общий доход / Расходы семьи / Остаток денег
  + список расходов (дата, сумма, наименование).

Акцент сделан на быстром вводе расхода с телефона:
большая цифровая клавиатура на экране + кнопки-категории + Сегодня/Вчера,
вместо того чтобы открывать таблицу и печатать в ячейках.
"""

import os
import datetime

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, RoundedRectangle
from kivy.properties import StringProperty

from storage import Storage

DEFAULT_CATEGORIES = ["Продукты", "Транспорт", "Коммуналка", "Развлечения", "Одежда", "Аптека"]

COLOR_BG = (0.95, 0.96, 0.98, 1)
COLOR_CARD = (1, 1, 1, 1)
COLOR_PRIMARY = (0.20, 0.55, 0.95, 1)
COLOR_DANGER = (0.90, 0.30, 0.30, 1)
COLOR_TEXT = (0.12, 0.14, 0.18, 1)
COLOR_MUTED = (0.45, 0.48, 0.55, 1)


def money(value):
    return f"{value:,.0f}".replace(",", " ")


class Card(BoxLayout):
    """Простая белая карточка со скруглёнными углами (фон рисуется вручную)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*COLOR_CARD)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(14)])
        self.bind(pos=self._update_rect, size=self._update_rect)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class FlatButton(Button):
    """Кнопка без стандартного скина Kivy, со своим цветом фона."""

    def __init__(self, bg=COLOR_PRIMARY, color=(1, 1, 1, 1), **kwargs):
        super().__init__(**kwargs)
        self.background_normal = ""
        self.background_down = ""
        self.background_color = bg
        self.color = color


class CategoryChip(FlatButton):
    pass


class ExpenseRow(BoxLayout):
    def __init__(self, expense_id, date_str, amount, category, on_delete, **kwargs):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(52),
                          padding=(dp(10), 0), spacing=dp(8), **kwargs)
        with self.canvas.before:
            Color(1, 1, 1, 1)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(10)])
        self.bind(pos=self._update_rect, size=self._update_rect)

        try:
            d = datetime.date.fromisoformat(date_str)
            date_disp = d.strftime("%d.%m")
        except ValueError:
            date_disp = date_str

        self.add_widget(Label(text=date_disp, size_hint_x=0.18, color=COLOR_MUTED,
                               font_size=dp(13)))
        self.add_widget(Label(text=category, size_hint_x=0.47, color=COLOR_TEXT,
                               font_size=dp(14), halign="left", valign="middle",
                               text_size=(dp(120), dp(52))))
        self.add_widget(Label(text=f"{money(amount)} ₽", size_hint_x=0.25, color=COLOR_TEXT,
                               font_size=dp(14), bold=True))
        del_btn = FlatButton(text="X", bg=(0, 0, 0, 0), color=COLOR_DANGER,
                              size_hint_x=0.10, font_size=dp(16), bold=True)
        del_btn.bind(on_release=lambda *_: on_delete(expense_id))
        self.add_widget(del_btn)

    def _update_rect(self, *args):
        self._rect.pos = self.pos
        self._rect.size = self.size


class AddExpenseContent(BoxLayout):
    """Содержимое всплывающего окна быстрого добавления расхода."""

    amount_text = StringProperty("0")

    def __init__(self, storage: Storage, on_saved, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        super().__init__(orientation="vertical", spacing=dp(10), padding=dp(14), **kwargs)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        self.storage = storage
        self.on_saved = on_saved
        self.selected_category = None
        self.selected_date = datetime.date.today()

        # --- сумма ---
        self.amount_label = Label(text="0 ₽", font_size=dp(34), bold=True,
                                   color=COLOR_TEXT, size_hint_y=None, height=dp(56))
        self.add_widget(self.amount_label)

        # --- клавиатура ---
        keypad = GridLayout(cols=3, spacing=dp(6), size_hint_y=None, height=dp(220))
        keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", ".", "0", "<-"]
        for k in keys:
            btn = FlatButton(text=k, bg=(0.92, 0.93, 0.96, 1), color=COLOR_TEXT,
                              font_size=dp(20))
            btn.bind(on_release=lambda inst, key=k: self._on_key(key))
            keypad.add_widget(btn)
        self.add_widget(keypad)

        # --- дата: Сегодня / Вчера ---
        date_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(8))
        self.today_btn = FlatButton(text="Сегодня", bg=COLOR_PRIMARY)
        self.yesterday_btn = FlatButton(text="Вчера", bg=(0.85, 0.87, 0.92, 1), color=COLOR_TEXT)
        self.today_btn.bind(on_release=lambda *_: self._pick_date(0))
        self.yesterday_btn.bind(on_release=lambda *_: self._pick_date(1))
        date_row.add_widget(self.today_btn)
        date_row.add_widget(self.yesterday_btn)
        self.add_widget(date_row)

        # --- категории ---
        self.add_widget(Label(text="Категория", size_hint_y=None, height=dp(20),
                               color=COLOR_MUTED, font_size=dp(13), halign="left",
                               text_size=(dp(280), dp(20))))
        cats_scroll = ScrollView(size_hint_y=None, height=dp(96))
        self.cats_grid = GridLayout(cols=3, spacing=dp(6), size_hint_y=None, padding=(0, 0))
        self.cats_grid.bind(minimum_height=self.cats_grid.setter("height"))
        cats_scroll.add_widget(self.cats_grid)
        self.add_widget(cats_scroll)
        self._build_category_chips()

        # --- своя категория ---
        self.custom_category = TextInput(hint_text="Своя категория (необязательно)",
                                          size_hint_y=None, height=dp(40),
                                          multiline=False, font_size=dp(14))
        self.add_widget(self.custom_category)

        # --- сохранить ---
        self.save_btn = FlatButton(text="Сохранить расход", bg=COLOR_PRIMARY,
                                    size_hint_y=None, height=dp(48), font_size=dp(16))
        self.save_btn.bind(on_release=lambda *_: self._save())
        self.add_widget(self.save_btn)

        self.status_label = Label(text="", size_hint_y=None, height=dp(18),
                                   color=COLOR_DANGER, font_size=dp(12))
        self.add_widget(self.status_label)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _build_category_chips(self):
        cats = self.storage.top_categories(limit=6)
        for c in DEFAULT_CATEGORIES:
            if c not in cats:
                cats.append(c)
        cats = cats[:6]
        for c in cats:
            chip = CategoryChip(text=c, bg=(0.90, 0.92, 0.97, 1), color=COLOR_TEXT,
                                 size_hint_y=None, height=dp(40), font_size=dp(13))
            chip.bind(on_release=lambda inst, cat=c: self._select_category(inst, cat))
            self.cats_grid.add_widget(chip)

    def _select_category(self, inst, cat):
        for child in self.cats_grid.children:
            child.background_color = (0.90, 0.92, 0.97, 1)
            child.color = COLOR_TEXT
        inst.background_color = COLOR_PRIMARY
        inst.color = (1, 1, 1, 1)
        self.selected_category = cat
        self.custom_category.text = ""

    def _pick_date(self, days_ago):
        self.selected_date = datetime.date.today() - datetime.timedelta(days=days_ago)
        if days_ago == 0:
            self.today_btn.background_color = COLOR_PRIMARY
            self.today_btn.color = (1, 1, 1, 1)
            self.yesterday_btn.background_color = (0.85, 0.87, 0.92, 1)
            self.yesterday_btn.color = COLOR_TEXT
        else:
            self.yesterday_btn.background_color = COLOR_PRIMARY
            self.yesterday_btn.color = (1, 1, 1, 1)
            self.today_btn.background_color = (0.85, 0.87, 0.92, 1)
            self.today_btn.color = COLOR_TEXT

    def _on_key(self, key):
        text = self.amount_text
        if key == "<-":
            text = text[:-1] or "0"
        elif key == ".":
            if "." not in text:
                text += "."
        else:
            if text == "0":
                text = key
            else:
                if len(text.split(".")[-1]) <= 2 or "." not in text:
                    text += key
        self.amount_text = text
        self.amount_label.text = f"{text} ₽"

    def _save(self):
        try:
            amount = float(self.amount_text)
        except ValueError:
            amount = 0
        category = self.custom_category.text.strip() or self.selected_category
        if amount <= 0:
            self.status_label.text = "Введите сумму больше нуля"
            return
        if not category:
            self.status_label.text = "Выберите или введите категорию"
            return
        self.storage.add_expense(self.selected_date.isoformat(), amount, category)
        self.on_saved()


class EditIncomesContent(BoxLayout):
    def __init__(self, storage: Storage, on_saved, **kwargs):
        super().__init__(orientation="vertical", spacing=dp(10), padding=dp(14), **kwargs)
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._update_bg, size=self._update_bg)
        self.storage = storage
        self.on_saved = on_saved
        husband, wife = storage.get_incomes()

        self.add_widget(Label(text="Доход мужа", size_hint_y=None, height=dp(20),
                               color=COLOR_MUTED, font_size=dp(13)))
        self.husband_input = TextInput(text=str(int(husband)), input_filter="float",
                                        multiline=False, size_hint_y=None, height=dp(44),
                                        font_size=dp(16), input_type="number")
        self.add_widget(self.husband_input)

        self.add_widget(Label(text="Доход жены", size_hint_y=None, height=dp(20),
                               color=COLOR_MUTED, font_size=dp(13)))
        self.wife_input = TextInput(text=str(int(wife)), input_filter="float",
                                     multiline=False, size_hint_y=None, height=dp(44),
                                     font_size=dp(16), input_type="number")
        self.add_widget(self.wife_input)

        save_btn = FlatButton(text="Сохранить", bg=COLOR_PRIMARY, size_hint_y=None,
                               height=dp(46), font_size=dp(16))
        save_btn.bind(on_release=lambda *_: self._save())
        self.add_widget(save_btn)

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def _save(self):
        try:
            husband = float(self.husband_input.text or 0)
            wife = float(self.wife_input.text or 0)
        except ValueError:
            return
        self.storage.set_incomes(husband, wife)
        self.on_saved()


class Dashboard(BoxLayout):
    def __init__(self, storage: Storage, **kwargs):
        super().__init__(orientation="vertical", **kwargs)
        self.storage = storage
        with self.canvas.before:
            Color(*COLOR_BG)
            self._bg_rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[0])
        self.bind(pos=self._update_bg, size=self._update_bg)

        # --- верхняя панель ---
        top_bar = BoxLayout(size_hint_y=None, height=dp(48), padding=(dp(12), 0))
        top_bar.add_widget(Label(text="Бюджет семьи", font_size=dp(20), bold=True,
                                  color=COLOR_TEXT, halign="left", valign="middle",
                                  text_size=(dp(200), dp(48))))
        settings_btn = FlatButton(text="Доходы", bg=(0, 0, 0, 0), color=COLOR_PRIMARY,
                                   size_hint_x=None, width=dp(80), font_size=dp(13))
        settings_btn.bind(on_release=lambda *_: self.open_incomes())
        export_btn = FlatButton(text="Экспорт", bg=(0, 0, 0, 0), color=COLOR_PRIMARY,
                                 size_hint_x=None, width=dp(80), font_size=dp(13))
        export_btn.bind(on_release=lambda *_: self.export_xlsx())
        top_bar.add_widget(settings_btn)
        top_bar.add_widget(export_btn)
        self.add_widget(top_bar)

        # --- карточка со сводкой ---
        self.summary_card = Card(orientation="vertical", size_hint_y=None, height=dp(150),
                                  padding=dp(14), spacing=dp(4))
        self.summary_labels = {}
        for key, title in (("total_income", "Общий доход"),
                            ("total_expenses", "Расходы семьи"),
                            ("remaining", "Остаток денег")):
            row = BoxLayout(size_hint_y=None, height=dp(28))
            row.add_widget(Label(text=title, color=COLOR_MUTED, font_size=dp(14),
                                  halign="left", valign="middle",
                                  text_size=(dp(180), dp(28))))
            val = Label(text="0 ₽", color=COLOR_TEXT, font_size=dp(16), bold=True)
            self.summary_labels[key] = val
            row.add_widget(val)
            self.summary_card.add_widget(row)
        self.summary_card.padding = [dp(14), dp(14), dp(14), dp(14)]

        outer_card = BoxLayout(size_hint_y=None, height=dp(160), padding=(dp(12), dp(6)))
        outer_card.add_widget(self.summary_card)
        self.add_widget(outer_card)

        # --- список расходов ---
        list_title = Label(text="Последние расходы", size_hint_y=None, height=dp(24),
                            color=COLOR_MUTED, font_size=dp(13), halign="left", valign="middle")
        list_title.bind(size=lambda inst, val: setattr(inst, "text_size", val))
        list_title.padding_x = dp(12)
        self.add_widget(list_title)

        scroll = ScrollView()
        self.expenses_list = GridLayout(cols=1, spacing=dp(6), size_hint_y=None,
                                         padding=(dp(12), dp(4)))
        self.expenses_list.bind(minimum_height=self.expenses_list.setter("height"))
        scroll.add_widget(self.expenses_list)
        self.add_widget(scroll)

        # --- кнопка добавления ---
        add_btn = FlatButton(text="+  Добавить расход", bg=COLOR_PRIMARY,
                              size_hint_y=None, height=dp(54), font_size=dp(17), bold=True)
        add_btn.bind(on_release=lambda *_: self.open_add_expense())
        self.add_widget(add_btn)

        self.refresh()

    def _update_bg(self, *args):
        self._bg_rect.pos = self.pos
        self._bg_rect.size = self.size

    def refresh(self):
        s = self.storage.summary()
        self.summary_labels["total_income"].text = f"{money(s['total_income'])} ₽"
        self.summary_labels["total_expenses"].text = f"{money(s['total_expenses'])} ₽"
        self.summary_labels["remaining"].text = f"{money(s['remaining'])} ₽"
        if s["remaining"] < 0:
            self.summary_labels["remaining"].color = COLOR_DANGER
        else:
            self.summary_labels["remaining"].color = COLOR_TEXT

        self.expenses_list.clear_widgets()
        for row in self.storage.list_expenses(limit=100):
            self.expenses_list.add_widget(
                ExpenseRow(row["id"], row["date"], row["amount"], row["category"],
                           on_delete=self.delete_expense)
            )

    def delete_expense(self, expense_id):
        self.storage.delete_expense(expense_id)
        self.refresh()

    def open_add_expense(self):
        content = AddExpenseContent(self.storage, on_saved=lambda: self._close_and_refresh(popup))
        scroll = ScrollView()
        scroll.add_widget(content)
        scroll.expense_content = content  # удобный доступ, в т.ч. для тестов
        popup = Popup(title="Новый расход", content=scroll, size_hint=(0.94, 0.92))
        popup.open()

    def open_incomes(self):
        content = EditIncomesContent(self.storage, on_saved=lambda: self._close_and_refresh(popup))
        popup = Popup(title="Доходы семьи", content=content, size_hint=(0.85, 0.5))
        popup.open()

    def _close_and_refresh(self, popup):
        popup.dismiss()
        self.refresh()

    def export_xlsx(self):
        app = App.get_running_app()
        out_dir = os.path.join(app.user_data_dir, "export")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "Расходы_семьи.xlsx")
        try:
            self.storage.export_to_xlsx(path)
            msg = f"Сохранено:\n{path}"
        except Exception as exc:  # noqa: BLE001
            msg = f"Ошибка экспорта: {exc}"
        popup = Popup(title="Экспорт в Excel",
                       content=Label(text=msg, font_size=dp(13)),
                       size_hint=(0.85, 0.3))
        popup.open()


class BudgetApp(App):
    title = "Бюджет семьи"

    def build(self):
        Window.clearcolor = COLOR_BG
        db_path = os.path.join(self.user_data_dir, "budget.db")
        self.storage = Storage(db_path)
        return Dashboard(self.storage)

    def on_stop(self):
        if hasattr(self, "storage"):
            self.storage.close()


if __name__ == "__main__":
    BudgetApp().run()
