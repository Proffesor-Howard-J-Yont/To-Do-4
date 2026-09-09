import tkinter as tk
from datetime import date, timedelta

class StructuredCalendarApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Calendar Day View")
        self.geometry("700x300")

        # Core State: tracks the active selected date
        self.selected_date = date.today()

        # Frame for top navigation bar
        self.nav_frame = tk.Frame(self, bg="#f0f0f0")#, py=10)
        self.nav_frame.pack(fill="x")

        # Main content area
        self.content_frame = tk.Frame(self)#, py=40)
        self.content_frame.pack(expand=True, fill="both")

        self.display_label = tk.Label(
            self.content_frame, 
            font=("Helvetica", 16, "bold")
        )
        self.display_label.pack()

        # Render initial view
        self.render_navigation()
        self.update_view()

    def render_navigation(self):
        """Re-creates the top button bar showing 7 days relative to selected_date."""
        # Clear existing buttons
        for widget in self.nav_frame.winfo_children():
            widget.destroy()

        # Previous week button
        prev_btn = tk.Button(
            self.nav_frame, 
            text="◄", 
            command=self.go_previous_week,
            width=3
        )
        prev_btn.pack(side="left", padx=2)

        # 7-day strip centered around selected_date (3 days prior to 3 days after)
        start_date = self.selected_date - timedelta(days=3)

        for i in range(7):
            day_date = start_date + timedelta(days=i)
            
            # Format label: "Wed\n09"
            btn_text = day_date.strftime("%a\n%d")

            # Style selected day differently
            is_selected = (day_date == self.selected_date)
            bg_color = "#007AFF" if is_selected else "#E0E0E0"
            fg_color = "white" if is_selected else "black"

            # Create date button; use lambda with default argument to capture day_date
            btn = tk.Button(
                self.nav_frame, 
                text=btn_text, 
                bg=bg_color, 
                fg=fg_color,
                width=5, 
                height=2,
                font=("Helvetica", 10, "bold" if is_selected else "normal"),
                command=lambda d=day_date: self.select_date(d)
            )
            btn.pack(side="left", padx=3)

        # Next week button
        next_btn = tk.Button(
            self.nav_frame, 
            text="►", 
            command=self.go_next_week,
            width=3
        )
        next_btn.pack(side="left", padx=2)

        # "Today" button
        today_btn = tk.Button(self.nav_frame, text="Today", command=self.go_today)#, padding=(5, 2))
        today_btn.pack(side="left", padx=(10, 2))

    def select_date(self, new_date):
        """Updates active date and triggers UI re-render."""
        self.selected_date = new_date
        self.render_navigation()
        self.update_view()

    def go_previous_week(self):
        self.select_date(self.selected_date - timedelta(days=7))

    def go_next_week(self):
        self.select_date(self.selected_date + timedelta(days=7))

    def go_today(self):
        self.select_date(date.today())

    def update_view(self):
        """Updates main content area with tasks for the selected date."""
        formatted_str = self.selected_date.strftime('%B %d, %Y')
        self.display_label.config(text=f"Tasks for {formatted_str}")


if __name__ == "__main__":
    app = StructuredCalendarApp()
    app.mainloop()
