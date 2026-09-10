"""
color_picker.py

Shared preset-swatches + colorwheel color-picker popup, used by both
myday_weekview.py (per-task block_color) and main.py (per-list color).
Kept as its own standalone module -- like myday_time_wheel.py -- so
neither of those two files has to import from the other.
"""

import tkinter as tk
from ttkbootstrap import Frame, Label, Button, Separator
from ttkbootstrap.style import Style as BSStyle
from ttkbootstrap.dialogs import Querybox

PRESET_COLORS = [
    '#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#1abc9c',
    '#3498db', '#9b59b6', '#e84393', '#7f8c8d', '#34495e',
]


def open_color_picker_popup(parent, current_color, on_save, title='Choose a color'):
    """Opens a modal color picker: a grid of preset swatches (click to
    apply immediately) plus a "Custom color..." button wired to
    ttkbootstrap's built-in color-wheel dialog, and "Reset to default".

    on_save(hex_value) is called with a '#rrggbb' string, or '' for
    "reset to default". The popup destroys itself after any choice
    (including Cancel, which calls nothing)."""
    colors = BSStyle().colors
    popup = tk.Toplevel(parent)
    popup.title(title)
    popup.configure(bg=colors.bg)

    # Everything lives inside one bootstyle='dark' Frame filling the
    # Toplevel -- a plain Toplevel + plain tk chrome defaults to the OS's
    # native light-mode colors, which clash badly against the dark-themed
    # swatches/buttons inside it otherwise.
    contentF = Frame(popup, bootstyle='dark')
    contentF.pack(fill='both', expand=True)

    Label(contentF, text=title, bootstyle='dark inverse',
          font=('Calibri', 12, 'bold')).pack(pady=(14, 8), padx=16)

    def apply_and_close(hex_value):
        on_save(hex_value)
        popup.destroy()

    swatchF = tk.Frame(contentF, bg=colors.bg)
    swatchF.pack(padx=16, pady=(0, 10))
    swatch_size, cols = 32, 5
    for i, hexcol in enumerate(PRESET_COLORS):
        row_i, col_i = divmod(i, cols)
        border = colors.selectfg if hexcol == current_color else colors.bg
        sw = tk.Frame(swatchF, width=swatch_size, height=swatch_size, bg=hexcol,
                      highlightthickness=2, highlightbackground=border, cursor='hand2')
        sw.grid(row=row_i, column=col_i, padx=4, pady=4)
        sw.grid_propagate(False)
        sw.bind('<Button-1>', lambda e, h=hexcol: apply_and_close(h))

    Separator(contentF, bootstyle='secondary').pack(fill='x', padx=16, pady=(4, 10))

    def open_colorwheel():
        result = Querybox.get_color(popup, title='Custom color', initialcolor=current_color or None)
        if result is not None:
            apply_and_close(result.hex)

    Button(contentF, text='Custom color...', bootstyle='secondary outline',
           command=open_colorwheel).pack(pady=(0, 8), padx=16, fill='x')
    Button(contentF, text='Reset to default', bootstyle='secondary outline',
           command=lambda: apply_and_close('')).pack(pady=(0, 8), padx=16, fill='x')
    Button(contentF, text='Cancel', bootstyle='secondary',
           command=popup.destroy).pack(pady=(0, 14), padx=16, fill='x')

    return popup
