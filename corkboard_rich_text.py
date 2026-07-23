"""
corkboard_rich_text.py

Rich-text pin content for the freeform Corkboard: bold/italic/underline,
curated font/size selection, two-click-confirm hyperlinks, and a single
image attachment per pin.

STORAGE FORMAT (the `content_json` column, stored as a JSON string):

    {
      "text": "raw text, no formatting baked in",
      "runs": [
        {"start": 0, "end": 5, "bold": true},
        {"start": 6, "end": 10, "italic": true},
        {"start": 6, "end": 10, "underline": true},
        {"start": 12, "end": 20, "font": "Georgia", "size": 18},
        {"start": 25, "end": 33, "link": "https://example.com"}
      ]
    }

Each run covers ONE property over a character range. Runs are free to
overlap (e.g. underline + font/size over the same span) since those become
independent Tkinter tags that layer cleanly. Bold/italic are the one
exception: Tkinter Text tags each carry a full font spec, and only one
tag's font "wins" per character -- tags don't merge weight+slant. To keep
bold+italic combinations rendering correctly, this module uses a single
internal style tag per range with 4 possible states (plain / bold / italic
/ bolditalic) rather than two independent tags. This is transparent in the
stored JSON (still just "bold": true / "italic": true side by side) -- it
only matters internally, when applying tags to the widget.

Known simplification: if a hyperlink's range overlaps a bold/italic range,
Tkinter's tag-priority rules (not this module) decide whether the bold/
italic styling or the link's blue/underline color wins visually. In
practice this only comes up if you deliberately bold part of a link, which
is an unusual thing to do -- flagging it here rather than hiding it.
"""

import json
import os
import time
import webbrowser
import tkinter as tk
from tkinter import filedialog
from ttkbootstrap import Frame, Label, Button, Entry, Combobox, Scrollbar, StringVar
from PIL import Image, ImageTk
from ttkbootstrap.scrolled import ScrolledFrame

FONT_OPTIONS = ['Calibri', 'Arial', 'Georgia', 'Consolas', 'Comic Sans MS']
SIZE_OPTIONS = [10, 12, 14, 16, 18, 20, 24, 28]
DEFAULT_FONT = 'Calibri'
DEFAULT_SIZE = 14

IMAGE_DIR = 'corkboard_images'
THUMB_SIZE = (200, 90)
EXPANDED_IMAGE_SIZE = (420, 220)


# ---------------------------------------------------------------------------
# Serialization: Tk Text widget <-> content_json
# ---------------------------------------------------------------------------

def _offset(text_widget, index):
    """Convert a Tkinter text index (e.g. '3.7') to a plain character offset."""
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
    """
    Reads the current contents + tags of a Text widget and produces the
    content_json dict. `link_urls` maps this widget's link tag names
    (e.g. 'link_0') to their URL, built up during editing.
    """
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


def apply_json_to_text_widget(text_widget, data, on_link_click,
                               base_font=DEFAULT_FONT, base_size=DEFAULT_SIZE):
    """
    Clears the widget and rebuilds its content + tags from a content_json
    dict (as produced by text_widget_to_json, or freshly loaded from the DB).
    Returns the link_urls dict so the caller can keep editing/re-saving.
    """
    was_disabled = text_widget.cget('state') == 'disabled'
    text_widget.configure(state='normal')
    text_widget.delete('1.0', 'end')
    text_widget.insert('1.0', data.get('text', ''))

    text_widget.tag_configure('style_bold', font=(base_font, base_size, 'bold'))
    text_widget.tag_configure('style_italic', font=(base_font, base_size, 'italic'))
    text_widget.tag_configure('style_bolditalic', font=(base_font, base_size, 'bold italic'))
    text_widget.tag_configure('underline', underline=True)

    link_urls = {}
    link_counter = 0

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
            text_widget.tag_configure(tagname, foreground='#3498db', underline=True)
            text_widget.tag_raise(tagname)  # links win the visual tug-of-war over style tags
            text_widget.tag_add(tagname, start, end)
            text_widget.tag_bind(tagname, '<Button-1>',
                                  lambda e, url=run['link']: on_link_click(e, url))
            text_widget.tag_bind(tagname, '<Enter>',
                                  lambda e: text_widget.configure(cursor='hand2'))
            text_widget.tag_bind(tagname, '<Leave>',
                                  lambda e: text_widget.configure(cursor='xterm'))

    if was_disabled:
        text_widget.configure(state='disabled')

    return link_urls


# ---------------------------------------------------------------------------
# Two-click hyperlink confirm popup
# ---------------------------------------------------------------------------

class LinkConfirmPopup:
    """
    Shows a small borderless 'Open' button near a click point. Clicking it
    opens the URL; clicking anywhere else dismisses it with no action taken.
    No auto-timeout -- tested in practice and found unnecessary.
    """
    _active = None  # only one popup at a time, app-wide

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

        # dismiss on any click anywhere else in the app
        self._bind_id = root.bind_all('<Button-1>', self._maybe_dismiss, add='+')

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
            self.root.unbind_all('<Button-1>')
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
    """Returns an (event, url) -> None handler that shows the confirm popup."""
    def handler(event, url):
        LinkConfirmPopup(root, event.x_root + 10, event.y_root + 10, url)
    return handler


# ---------------------------------------------------------------------------
# Compact pin preview (lives on the freeform board)
# ---------------------------------------------------------------------------

def build_pin_preview(parent, root, rowid, title, color, content_json_str, image_path,
                       on_expand, on_color, on_delete, pin_width, pin_height):
    """Builds the small, read-only card shown on the corkboard itself."""
    data = json.loads(content_json_str) if content_json_str else {'text': '', 'runs': []}
    has_image = bool(image_path and os.path.exists(image_path))

    card = Frame(parent, bootstyle=color, padding=8)

    Label(card, text=title, bootstyle=f'{color} inverse', font=('Calibri', 14, 'bold'),
          wraplength=pin_width - 16).pack(anchor='w', fill='x')

    body = tk.Text(card, height=(2 if has_image else 3), width=1, wrap='word',
                    borderwidth=0, highlightthickness=0, cursor='arrow')
    body.pack(fill='x', pady=(4, 0))
    apply_json_to_text_widget(body, data, make_link_click_handler(root))
    body.configure(state='disabled')

    if has_image:
        try:
            img = Image.open(image_path)
            img.thumbnail(THUMB_SIZE)
            photo = ImageTk.PhotoImage(img)
            img_L = Label(card, image=photo)
            img_L.image = photo  # keep a reference so it isn't garbage-collected
            img_L.pack(pady=(4, 0))
        except Exception:
            pass

    toolbar = Frame(card, bootstyle=color)
    toolbar.pack(fill='x', pady=(6, 0))
    Button(toolbar, text='\U0001F50D', bootstyle=f'{color} link',
           command=lambda: on_expand(rowid)).pack(side='left')
    Button(toolbar, text='\U0001F3A8', bootstyle=f'{color} link',
           command=lambda: on_color(rowid)).pack(side='left')
    Button(toolbar, text='\U0001F5D1', bootstyle=f'{color} link',
           command=lambda: on_delete(rowid)).pack(side='left')

    return card


# ---------------------------------------------------------------------------
# Expanded editor (Toplevel popup) -- all real editing happens here
# ---------------------------------------------------------------------------

def open_pin_editor(root, rowid, title, content_json_str, image_path, on_save):
    """
    Opens the full editor for one pin. on_save(rowid, new_title,
    new_content_json_str, new_image_path) is called when Save is clicked.
    """
    data = json.loads(content_json_str) if content_json_str else {'text': '', 'runs': []}
    state = {'image_path': image_path}

    win = tk.Toplevel(root)
    win.title('Edit Pin')
    win.geometry('520x640')

    win_frame = ScrolledFrame(win, padding=10)
    win_frame.pack(fill='both', expand=True, padx=10, pady=10)

    Label(win_frame, text='Title:', font=('Calibri', 12)).pack(anchor='w', padx=10, pady=(10, 0))
    title_E = Entry(win_frame, font=('Calibri', 16))
    title_E.pack(fill='x', padx=10)
    title_E.insert(0, title)

    toolbar = Frame(win_frame)
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

    body_frame = Frame(win_frame)
    body_frame.pack(fill='both', expand=True, padx=10)
    body = tk.Text(body_frame, wrap='word', font=(DEFAULT_FONT, DEFAULT_SIZE), undo=True)
    body_scroll = Scrollbar(body_frame, orient='vertical', command=body.yview)
    body.configure(yscrollcommand=body_scroll.set)
    body.pack(side='left', fill='both', expand=True)
    body_scroll.pack(side='right', fill='y')

    link_urls = apply_json_to_text_widget(body, data, make_link_click_handler(win))

    img_frame = Frame(win_frame)
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

    # ---- toolbar button behavior ----

    def current_style(index):
        tags = body.tag_names(index)
        return ('style_bold' in tags or 'style_bolditalic' in tags,
                'style_italic' in tags or 'style_bolditalic' in tags)

    def toggle_style(which):
        try:
            sel_start = body.index('sel.first')
            sel_end = body.index('sel.last')
        except tk.TclError:
            return  # nothing selected -- no-op, rather than guessing intent
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

    def apply_font_size(event=None):
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
                body.tag_configure(tagname, foreground='#3498db', underline=True)
                body.tag_raise(tagname)
                body.tag_add(tagname, sel_start, sel_end)
                body.tag_bind(tagname, '<Button-1>',
                               lambda e, u=url: make_link_click_handler(win)(e, u))
            url_win.destroy()

        url_E.bind('<Return>', confirm)
        Button(url_win, text='Add', bootstyle='primary', command=confirm).pack(pady=(0, 10))

    bold_B.configure(command=lambda: toggle_style('bold'))
    italic_B.configure(command=lambda: toggle_style('italic'))
    underline_B.configure(command=toggle_underline)
    font_var.trace_add('write', lambda *a: apply_font_size())
    size_var.trace_add('write', lambda *a: apply_font_size())
    link_B.configure(command=add_link)

    # ---- save / close ----

    btn_frame = Frame(win)
    btn_frame.pack(fill='x', padx=10, pady=10)

    def do_save():
        new_data = text_widget_to_json(body, link_urls)
        on_save(rowid, title_E.get().strip(), json.dumps(new_data), state['image_path'])
        win.destroy()

    Button(btn_frame, text='Save', bootstyle='success', command=do_save).pack(side='left', padx=5)
    Button(btn_frame, text='X Close', bootstyle='secondary outline',
           command=win.destroy).pack(side='right', padx=5)

    return win