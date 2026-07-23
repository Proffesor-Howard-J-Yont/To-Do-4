"""
corkboard_rich_text.py

Rich-text pin content for the freeform Corkboard.

Fixes/changes in this version:
- Compact preview no longer uses state='disabled' on its Text widget --
  that was silently breaking hyperlink clicks (a known Tkinter behavior:
  a disabled Text widget stops firing tag click bindings, not just
  editing). Read-only-but-clickable is now done by keeping state='normal'
  and swallowing <Key>/<<Paste>>/<Button-2> instead.
- Colors are pulled from ttkbootstrap's Style().colors at render time and
  applied explicitly to the raw tk.Text/tk.Label widgets, since those
  don't auto-theme the way bootstyle= widgets do (this was the "black
  background" bug).
- Compact preview no longer shows an image thumbnail or a button toolbar --
  those were overflowing the pin's fixed height. Images are now a small
  "[Image]" badge; text gets a trailing "..." if it doesn't fit. All
  actions (color, image, formatting, links, delete) now live in the
  expanded view, reached via a plain click on the pin.
- The expanded view opens read-only first (open_pin_view), with an Edit
  button that opens the full editor (open_pin_editor) for formatting,
  images, color, and delete.
- Deleting a pin also deletes its attached image file from disk, if any.

STORAGE FORMAT (content_json column) is unchanged from before -- raw text
plus a list of formatting "runs" (start/end + bold/italic/underline/font/
size/link). See the module-level comment in the previous version's history
for the full rationale; unchanged here.
"""

import json
import os
import time
import webbrowser
import tkinter as tk
from tkinter import filedialog
from ttkbootstrap import Frame, Label, Button, Entry, Combobox, Scrollbar, StringVar, Style
from PIL import Image, ImageTk

FONT_OPTIONS = ['Calibri', 'Arial', 'Georgia', 'Consolas', 'Comic Sans MS']
SIZE_OPTIONS = [10, 12, 14, 16, 18, 20, 24, 28]
DEFAULT_FONT = 'Calibri'
DEFAULT_SIZE = 14

IMAGE_DIR = 'corkboard_images'
EXPANDED_IMAGE_SIZE = (420, 220)

PREVIEW_MAX_CHARS = 90  # rough heuristic for when to truncate the compact preview text


# ---------------------------------------------------------------------------
# Color matching (fixes raw Text/Label widgets not following the theme)
# ---------------------------------------------------------------------------

def _pin_colors(color):
    """Returns (background_hex, foreground_hex) matching a ttkbootstrap
    bootstyle color name, pulled live from the active theme."""
    style = Style()
    bg = getattr(style.colors, color, None) or style.colors.secondary
    try:
        fg = style.colors.get_foreground(color)
    except Exception:
        fg = style.colors.fg
    return bg, fg


def delete_image_file(image_path):
    """Public helper: safely deletes a pin's attached image file, if any."""
    if image_path and os.path.exists(image_path):
        try:
            os.remove(image_path)
        except OSError:
            pass


# ---------------------------------------------------------------------------
# Read-only-but-clickable Text widget helper (replaces disabled state)
# ---------------------------------------------------------------------------

def _make_readonly(text_widget):
    """
    Keeps the widget in state='normal' (so tag click bindings, e.g.
    hyperlinks, keep working) while blocking actual editing.
    """
    text_widget.bind('<Key>', lambda e: 'break')
    text_widget.bind('<<Paste>>', lambda e: 'break')
    text_widget.bind('<Button-2>', lambda e: 'break')  # middle-click paste (Linux/X11)


# ---------------------------------------------------------------------------
# Serialization: Tk Text widget <-> content_json
# ---------------------------------------------------------------------------

def _offset(text_widget, index):
    return len(text_widget.get('1.0', index))


def _style_tag_for(bold, italic):
    if bold and italic:
        return 'style_bolditalic'
    if bold:
        return 'style_bold'
    if italic:
        return 'style_italic'
    return None


def text_widget_to_json(text_widget, link_urls):
    text = text_widget.get('1.0', 'end-1c')
    runs = []

    for tag in text_widget.tag_names():
        if tag == 'sel':
            continue
        ranges = text_widget.tag_ranges(tag)
        for i in range(0, len(ranges), 2):
            start = _offset(text_widget, ranges[i])
            end = _offset(text_widget, ranges[i + 1])
            if start == end:
                continue
            if tag == 'style_bold':
                runs.append({'start': start, 'end': end, 'bold': True})
            elif tag == 'style_italic':
                runs.append({'start': start, 'end': end, 'italic': True})
            elif tag == 'style_bolditalic':
                runs.append({'start': start, 'end': end, 'bold': True, 'italic': True})
            elif tag == 'underline':
                runs.append({'start': start, 'end': end, 'underline': True})
            elif tag.startswith('fontsize_|'):
                _, fontname, size = tag.split('|')
                runs.append({'start': start, 'end': end, 'font': fontname, 'size': int(size)})
            elif tag.startswith('link_'):
                url = link_urls.get(tag)
                if url:
                    runs.append({'start': start, 'end': end, 'link': url})

    return {'text': text, 'runs': runs}


def apply_json_to_text_widget(text_widget, data, on_link_click, board=None, rowid=None,
                               base_font=DEFAULT_FONT, base_size=DEFAULT_SIZE,
                               fg='#ffffff'):
    """
    Rebuilds a Text widget's content + tags from a content_json dict.
    `board`/`rowid`: if given, link clicks call board.suppress_click(rowid)
    first, so a click on a link inside a pin on the freeform board doesn't
    ALSO register as a click on the pin itself (which would open it).
    Returns the link_urls dict so the caller can keep editing/re-saving.
    """
    text_widget.delete('1.0', 'end')
    text_widget.insert('1.0', data.get('text', ''))

    text_widget.tag_configure('style_bold', font=(base_font, base_size, 'bold'))
    text_widget.tag_configure('style_italic', font=(base_font, base_size, 'italic'))
    text_widget.tag_configure('style_bolditalic', font=(base_font, base_size, 'bold italic'))
    text_widget.tag_configure('underline', underline=True)

    link_urls = {}
    link_counter = 0

    def handle_link(event, url):
        if board is not None and rowid is not None:
            board.suppress_click(rowid)
        on_link_click(event, url)

    for run in data.get('runs', []):
        start = f"1.0+{run['start']}c"
        end = f"1.0+{run['end']}c"

        if run.get('bold') or run.get('italic'):
            tagname = _style_tag_for(run.get('bold', False), run.get('italic', False))
            text_widget.tag_add(tagname, start, end)

        if run.get('underline'):
            text_widget.tag_add('underline', start, end)

        if run.get('font') or run.get('size'):
            fontname = run.get('font', base_font)
            size = run.get('size', base_size)
            tagname = f"fontsize_|{fontname}|{size}"
            text_widget.tag_configure(tagname, font=(fontname, size))
            text_widget.tag_add(tagname, start, end)

        if run.get('link'):
            tagname = f"link_{link_counter}"
            link_counter += 1
            link_urls[tagname] = run['link']
            text_widget.tag_configure(tagname, foreground='#3ea6ff', underline=True)
            text_widget.tag_raise(tagname)
            text_widget.tag_add(tagname, start, end)
            text_widget.tag_bind(tagname, '<ButtonPress-1>',
                                  lambda e, url=run['link']: handle_link(e, url))
            text_widget.tag_bind(tagname, '<Enter>',
                                  lambda e: text_widget.configure(cursor='hand2'))
            text_widget.tag_bind(tagname, '<Leave>',
                                  lambda e: text_widget.configure(cursor='xterm' if not board else 'arrow'))

    return link_urls


def _truncate_content_for_preview(data, max_chars=PREVIEW_MAX_CHARS):
    """
    Approximate truncation for the compact preview: if the raw text is
    longer than max_chars, cut it (and clip any runs that extend past the
    cut) and append '...'. This is a heuristic based on character count,
    not exact pixel/line wrapping -- good enough for a small preview box,
    not meant to be pixel-perfect.
    """
    text = data.get('text', '')
    if len(text) <= max_chars:
        return data, False

    cut = max_chars
    new_text = text[:cut].rstrip() + '...'
    new_runs = []
    for run in data.get('runs', []):
        if run['start'] >= cut:
            continue
        new_run = dict(run)
        new_run['end'] = min(run['end'], cut)
        new_runs.append(new_run)

    return {'text': new_text, 'runs': new_runs}, True


# ---------------------------------------------------------------------------
# Two-click hyperlink confirm popup
# ---------------------------------------------------------------------------

class LinkConfirmPopup:
    _active = None

    def __init__(self, root, x, y, url):
        LinkConfirmPopup.dismiss_active()
        LinkConfirmPopup._active = self
        self.root = root

        self.win = tk.Toplevel(root)
        self.win.overrideredirect(True)
        self.win.geometry(f'+{x}+{y}')
        self.win.attributes('-topmost', True)

        Button(self.win, text='Open \u2197', bootstyle='info',
               command=lambda: self._open(url)).pack(ipadx=6, ipady=2)

        self._bind_id = root.bind_all('<ButtonPress-1>', self._maybe_dismiss, add='+')

    def _open(self, url):
        webbrowser.open(url)
        self.close()

    def _maybe_dismiss(self, event):
        try:
            if event.widget.winfo_toplevel() != self.win:
                self.close()
        except tk.TclError:
            self.close()

    def close(self):
        if LinkConfirmPopup._active is self:
            LinkConfirmPopup._active = None
        try:
            self.root.unbind_all('<ButtonPress-1>')
        except tk.TclError:
            pass
        try:
            self.win.destroy()
        except tk.TclError:
            pass

    @classmethod
    def dismiss_active(cls):
        if cls._active is not None:
            cls._active.close()


def make_link_click_handler(root):
    def handler(event, url):
        LinkConfirmPopup(root, event.x_root + 10, event.y_root + 10, url)
    return handler


# ---------------------------------------------------------------------------
# Compact pin preview (lives on the freeform board)
# ---------------------------------------------------------------------------

def build_pin_preview(parent, root, board, rowid, title, color, content_json_str,
                       image_path, pin_width, pin_height):
    """
    Read-only preview card. The whole card is draggable/clickable via the
    FreeformCorkboard's own binding (registered by the caller through
    add_pin(..., on_click=...)) -- this function only builds the visuals.
    """
    data = json.loads(content_json_str) if content_json_str else {'text': '', 'runs': []}
    has_image = bool(image_path and os.path.exists(image_path))

    bg, fg = _pin_colors(color)

    card = Frame(parent, bootstyle=color, padding=8)

    Label(card, text=title, bootstyle=f'{color} inverse', font=('Calibri', 14, 'bold'),
          wraplength=pin_width - 16).pack(anchor='w', fill='x')

    preview_data, was_truncated = _truncate_content_for_preview(data)

    body = tk.Text(card, height=4, width=1, wrap='word', borderwidth=0,
                    highlightthickness=0, background=bg, foreground=fg,
                    insertbackground=fg, cursor='arrow')
    body.pack(fill='x', pady=(4, 0))
    apply_json_to_text_widget(body, preview_data, make_link_click_handler(root),
                               board=board, rowid=rowid, fg=fg)
    _make_readonly(body)

    if has_image:
        Label(card, text='\U0001F5BC [Image]', bootstyle=f'{color} inverse',
              font=('Calibri', 11, 'italic')).pack(anchor='w', pady=(2, 0))

    return card


# ---------------------------------------------------------------------------
# View-only expanded screen
# ---------------------------------------------------------------------------

def open_pin_view(root, rowid, title, content_json_str, image_path, on_edit):
    data = json.loads(content_json_str) if content_json_str else {'text': '', 'runs': []}

    win = tk.Toplevel(root)
    win.title(title or 'Pin')
    screen_h = win.winfo_screenheight()
    win_h = min(560, screen_h - 100)
    win.geometry(f'460x{win_h}')
    win.resizable(True, True)

    btn_frame = Frame(win)
    btn_frame.pack(side='bottom', fill='x', padx=15, pady=15)
    Button(btn_frame, text='\u270F Edit', bootstyle='primary',
           command=lambda: (win.destroy(), on_edit(rowid))).pack(side='left', padx=5)
    Button(btn_frame, text='Close', bootstyle='secondary outline',
           command=win.destroy).pack(side='right', padx=5)

    Label(win, text=title, font=('Calibri', 20, 'bold')).pack(anchor='w', padx=15, pady=(15, 5))

    body_frame = Frame(win)
    body_frame.pack(fill='both', expand=True, padx=15)
    body = tk.Text(body_frame, wrap='word', font=(DEFAULT_FONT, DEFAULT_SIZE),
                    borderwidth=0, highlightthickness=0, cursor='arrow')
    body_scroll = Scrollbar(body_frame, orient='vertical', command=body.yview)
    body.configure(yscrollcommand=body_scroll.set)
    body.pack(side='left', fill='both', expand=True)
    body_scroll.pack(side='right', fill='y')

    apply_json_to_text_widget(body, data, make_link_click_handler(win))
    _make_readonly(body)

    if image_path and os.path.exists(image_path):
        img = Image.open(image_path)
        img.thumbnail(EXPANDED_IMAGE_SIZE)
        photo = ImageTk.PhotoImage(img)
        img_L = Label(win, image=photo)
        img_L.image = photo
        img_L.pack(pady=10)

    return win


# ---------------------------------------------------------------------------
# Full editor (Toplevel) -- formatting, image, color, delete
# ---------------------------------------------------------------------------

def open_pin_editor(root, rowid, title, content_json_str, image_path, color,
                     on_save, on_delete):
    """
    on_save(rowid, new_title, new_content_json_str, new_image_path, new_color)
    on_delete(rowid, image_path)
    """
    data = json.loads(content_json_str) if content_json_str else {'text': '', 'runs': []}
    state = {'image_path': image_path, 'color': color}

    win = tk.Toplevel(root)
    win.title('Edit Pin')
    screen_h = win.winfo_screenheight()
    win_h = min(700, screen_h - 100)
    win.geometry(f'540x{win_h}')
    win.resizable(True, True)

    # Pack the action bar FIRST, anchored to the bottom -- this guarantees
    # Save/Delete/Close always have their space reserved and stay reachable,
    # regardless of how tall the body content or the screen itself is.
    btn_frame = Frame(win)
    btn_frame.pack(side='bottom', fill='x', padx=10, pady=10)

    Label(win, text='Title:', font=('Calibri', 12)).pack(anchor='w', padx=10, pady=(10, 0))
    title_E = Entry(win, font=('Calibri', 16))
    title_E.pack(fill='x', padx=10)
    title_E.insert(0, title)

    # ---- color picker ----
    color_frame = Frame(win)
    color_frame.pack(fill='x', padx=10, pady=8)
    Label(color_frame, text='Color:', font=('Calibri', 12)).pack(side='left', padx=(0, 8))
    colors = ['dark', 'secondary', 'light', 'success', 'danger', 'warning', 'info', 'primary']
    for c in colors:
        Button(color_frame, bootstyle=c, text='  ',
               command=lambda c=c: state.update(color=c)).pack(side='left', padx=2)

    # ---- formatting toolbar ----
    toolbar = Frame(win)
    toolbar.pack(fill='x', padx=10, pady=8)

    bold_B = Button(toolbar, text='B', width=3)
    bold_B.pack(side='left', padx=2)
    italic_B = Button(toolbar, text='I', width=3)
    italic_B.pack(side='left', padx=2)
    underline_B = Button(toolbar, text='U', width=3)
    underline_B.pack(side='left', padx=2)

    font_var = StringVar(value=DEFAULT_FONT)
    Combobox(toolbar, textvariable=font_var, values=FONT_OPTIONS,
             width=13, state='readonly').pack(side='left', padx=(10, 2))

    size_var = StringVar(value=str(DEFAULT_SIZE))
    Combobox(toolbar, textvariable=size_var, values=SIZE_OPTIONS,
             width=4, state='readonly').pack(side='left', padx=2)

    link_B = Button(toolbar, text='\U0001F517 Link', bootstyle='info outline')
    link_B.pack(side='left', padx=(10, 0))

    body_frame = Frame(win)
    body_frame.pack(fill='both', expand=True, padx=10)
    body = tk.Text(body_frame, wrap='word', font=(DEFAULT_FONT, DEFAULT_SIZE), undo=True)
    body_scroll = Scrollbar(body_frame, orient='vertical', command=body.yview)
    body.configure(yscrollcommand=body_scroll.set)
    body.pack(side='left', fill='both', expand=True)
    body_scroll.pack(side='right', fill='y')

    link_urls = apply_json_to_text_widget(body, data, make_link_click_handler(win))

    img_frame = Frame(win)
    img_frame.pack(fill='x', padx=10, pady=8)

    def refresh_image_preview():
        for w in img_frame.winfo_children():
            w.destroy()
        if state['image_path'] and os.path.exists(state['image_path']):
            img = Image.open(state['image_path'])
            img.thumbnail(EXPANDED_IMAGE_SIZE)
            photo = ImageTk.PhotoImage(img)
            preview_L = Label(img_frame, image=photo)
            preview_L.image = photo
            preview_L.pack()
            Button(img_frame, text='\u2715 Remove image', bootstyle='danger link',
                   command=lambda: (state.update(image_path=None), refresh_image_preview())
                   ).pack(pady=(4, 0))
        Button(img_frame, text='\U0001F5BC Add/Change Image', bootstyle='secondary outline',
               command=attach_image).pack(pady=(6, 0))

    def attach_image():
        path = filedialog.askopenfilename(
            title='Choose an image',
            filetypes=[('Images', '*.png *.jpg *.jpeg *.gif')]
        )
        if not path:
            return
        os.makedirs(IMAGE_DIR, exist_ok=True)
        ext = os.path.splitext(path)[1]
        dest = os.path.join(IMAGE_DIR, f'{rowid}_{int(time.time())}{ext}')
        with open(path, 'rb') as src, open(dest, 'wb') as dst:
            dst.write(src.read())
        state['image_path'] = dest
        refresh_image_preview()

    refresh_image_preview()

    def current_style(index):
        tags = body.tag_names(index)
        return ('style_bold' in tags or 'style_bolditalic' in tags,
                'style_italic' in tags or 'style_bolditalic' in tags)

    def toggle_style(which):
        try:
            sel_start = body.index('sel.first')
            sel_end = body.index('sel.last')
        except tk.TclError:
            return
        bold_now, italic_now = current_style(sel_start)
        if which == 'bold':
            bold_now = not bold_now
        else:
            italic_now = not italic_now
        for t in ('style_bold', 'style_italic', 'style_bolditalic'):
            body.tag_remove(t, sel_start, sel_end)
        newtag = _style_tag_for(bold_now, italic_now)
        if newtag:
            body.tag_add(newtag, sel_start, sel_end)

    def toggle_underline():
        try:
            sel_start = body.index('sel.first')
            sel_end = body.index('sel.last')
        except tk.TclError:
            return
        if 'underline' in body.tag_names(sel_start):
            body.tag_remove('underline', sel_start, sel_end)
        else:
            body.tag_add('underline', sel_start, sel_end)

    def apply_font_size(*_):
        try:
            sel_start = body.index('sel.first')
            sel_end = body.index('sel.last')
        except tk.TclError:
            return
        fontname = font_var.get()
        size = int(size_var.get())
        tagname = f"fontsize_|{fontname}|{size}"
        body.tag_configure(tagname, font=(fontname, size))
        body.tag_add(tagname, sel_start, sel_end)

    def add_link():
        try:
            sel_start = body.index('sel.first')
            sel_end = body.index('sel.last')
        except tk.TclError:
            return
        url_win = tk.Toplevel(win)
        url_win.title('Add Link')
        Label(url_win, text='URL:').pack(padx=10, pady=(10, 0))
        url_E = Entry(url_win, width=40)
        url_E.pack(padx=10, pady=5)
        url_E.focus_force()

        def confirm(event=None):
            url = url_E.get().strip()
            if url:
                tagname = f"link_{len(link_urls)}"
                link_urls[tagname] = url
                body.tag_configure(tagname, foreground='#3ea6ff', underline=True)
                body.tag_raise(tagname)
                body.tag_add(tagname, sel_start, sel_end)
                body.tag_bind(tagname, '<ButtonPress-1>',
                               lambda e, u=url: make_link_click_handler(win)(e, u))
            url_win.destroy()

        url_E.bind('<Return>', confirm)
        Button(url_win, text='Add', bootstyle='primary', command=confirm).pack(pady=(0, 10))

    bold_B.configure(command=lambda: toggle_style('bold'))
    italic_B.configure(command=lambda: toggle_style('italic'))
    underline_B.configure(command=toggle_underline)
    font_var.trace_add('write', apply_font_size)
    size_var.trace_add('write', apply_font_size)
    link_B.configure(command=add_link)

    # ---- save / delete / close (buttons added into the bar already packed above) ----

    def do_save():
        new_data = text_widget_to_json(body, link_urls)
        on_save(rowid, title_E.get().strip(), json.dumps(new_data),
                state['image_path'], state['color'])
        win.destroy()

    def do_delete():
        on_delete(rowid, state['image_path'])
        win.destroy()

    Button(btn_frame, text='Save', bootstyle='success', command=do_save).pack(side='left', padx=5)
    Button(btn_frame, text='\U0001F5D1 Delete', bootstyle='danger outline',
           command=do_delete).pack(side='left', padx=5)
    Button(btn_frame, text='X Close', bootstyle='secondary outline',
           command=win.destroy).pack(side='right', padx=5)

    return win