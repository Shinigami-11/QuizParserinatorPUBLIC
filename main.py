import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Set
import random
import json
import os
import threading

# Function to install TTKBootstrap if not installed
def install_dependencies():
    """Install missing dependencies automatically."""
    required_libraries = ["ttkbootstrap"]  # Removed pyttsx3

    for library in required_libraries:
        try:
            __import__(library.split(">=")[0])
        except ImportError:
            print(f"Installing {library}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", library])

# Install dependencies before running the rest of the program
install_dependencies()

# Now import the libraries
import ttkbootstrap as ttk
from ttkbootstrap.constants import *

# Your original code starts here
class Question:
    def __init__(self, text: str, answer: str, subjects: List[str], difficulty: str, year: int):
        self.text = text
        self.answer = answer
        self.subjects = subjects
        self.difficulty = difficulty
        self.year = year

    def to_dict(self):
        return {
            "text": self.text,
            "answer": self.answer,
            "subjects": self.subjects,
            "difficulty": self.difficulty,
            "year": self.year
        }

    @classmethod
    def from_dict(cls, data: Dict):
        return cls(data["text"], data["answer"], data["subjects"], data["difficulty"], data["year"])


class ContentView:
    def __init__(self, root: ttk.Window):
        self.root = root
        self.root.title("Quiz Parserinator")
        self.root.geometry("1200x900")

        # Initialize theme
        self.current_theme = "cosmo"  # Default to light mode
        self.root.style.theme_use(self.current_theme)

        # Center the window
        self.center_window()

        self.question_index = 0
        self.user_answer = ""
        self.is_correct = False
        self.show_answer = False
        self.score = 0
        self.total_questions = 0
        self.reading_text = ""
        self.read_index = 0
        self.selected_subjects: Set[str] = set()
        self.reading_speed = 0.05
        self.filtered_questions: List[Question] = []
        self.selected_difficulty = "District"
        self.selected_year = 2024
        self.is_adding_question = False
        self.timer_running = False
        self.timer_seconds = 5  # Default timer duration
        self.timer_enabled = True  # Timer starts enabled
        self.timer_label = None
        self.reading_active = False  # Flag to control text display
        self.next_question_cooldown = False  # Flag to prevent rapid next question clicks
        self.score_updated = False  # Flag to track if score has been updated for the current question
        self.submitted = False  # Flag to track if the user has submitted an answer for the current question

        # Default keybind settings
        self.keybinds = {
            "submit_answer": "<Return>",  # Enter key to submit answer
        }

        # Load keybinds from file or use defaults
        self.load_keybinds()

        # Load questions from file or use default questions
        self.all_questions = self.load_questions()

        # Create a scrollable canvas
        self.canvas = tk.Canvas(self.root)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add a scrollbar
        self.scrollbar_y = ttk.Scrollbar(self.root, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)

        self.scrollbar_x = ttk.Scrollbar(self.root, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)

        # Configure the canvas
        self.canvas.configure(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        self.canvas.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        # Create a frame inside the canvas
        self.main_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")

        # Bind mouse wheel scrolling
        self.root.bind_all("<MouseWheel>", self.on_mousewheel)
        self.root.bind_all("<Button-4>", self.on_mousewheel)  # For Linux, scroll up
        self.root.bind_all("<Button-5>", self.on_mousewheel)  # For Linux, scroll down
        self.root.bind_all("<Shift-MouseWheel>", self.on_shift_mousewheel)  # Horizontal scrolling

        self.setup_ui()
        self.filter_questions()
        self.start_reading()

    def center_window(self):
        """Center the window on the screen."""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

    def on_mousewheel(self, event):
        """Handle vertical mouse wheel scrolling."""
        if event.num == 4 or event.delta > 0:
            self.canvas.yview_scroll(-1, "units")  # Scroll up
        elif event.num == 5 or event.delta < 0:
            self.canvas.yview_scroll(1, "units")  # Scroll down

    def on_shift_mousewheel(self, event):
        """Handle horizontal mouse wheel scrolling."""
        if event.num == 4 or event.delta > 0:
            self.canvas.xview_scroll(-1, "units")  # Scroll left
        elif event.num == 5 or event.delta < 0:
            self.canvas.xview_scroll(1, "units")  # Scroll right

    def setup_ui(self):
        # Increase font sizes for better readability
        title_font = ("Arial", 36, "bold")
        label_font = ("Arial", 14)
        button_font = ("Arial", 12)
        entry_font = ("Arial", 12)

        # Title Label
        self.title_label = ttk.Label(self.main_frame, text="Quiz Parserinator", font=title_font, bootstyle="primary")
        self.title_label.pack(pady=20)

        # Theme Switcher (Light/Dark Mode)
        self.theme_var = tk.StringVar(value="light")
        self.theme_switcher = ttk.Checkbutton(
            self.main_frame,
            text="Dark Mode",
            variable=self.theme_var,
            bootstyle="round-toggle",
            command=self.toggle_theme,
        )
        self.theme_switcher.pack(pady=10)

        # Settings Dropdown Menu (Top of the program)
        settings_frame = ttk.Frame(self.main_frame)
        settings_frame.pack(pady=10, padx=10, fill=tk.X)

        self.settings_var = tk.StringVar(value="Settings")
        self.settings_menu = ttk.Combobox(settings_frame, textvariable=self.settings_var, values=["Keybind Settings", "Reading Speed", "Timer Settings", "Manage Questions", "Add New Question"], state="readonly", font=label_font, width=20)
        self.settings_menu.grid(row=0, column=0, padx=5, pady=5)
        self.settings_menu.bind("<<ComboboxSelected>>", lambda e: self.handle_settings_selection())

        # Filters Frame
        filters_frame = ttk.LabelFrame(self.main_frame, text="Filters")
        filters_frame.pack(pady=10, padx=10, fill=tk.X)

        # Year Dropdown (Non-Editable)
        ttk.Label(filters_frame, text="Year:", font=label_font).grid(row=0, column=0, padx=5, pady=5)
        self.year_var = tk.StringVar(value="2024")
        self.year_menu = ttk.Combobox(filters_frame, textvariable=self.year_var, values=[str(year) for year in range(2017, 2025)], font=entry_font, state="readonly")
        self.year_menu.grid(row=0, column=1, padx=5, pady=5)
        self.year_menu.bind("<<ComboboxSelected>>", lambda e: self.update_year())

        # Difficulty Dropdown (Non-Editable)
        ttk.Label(filters_frame, text="Difficulty:", font=label_font).grid(row=0, column=2, padx=5, pady=5)
        self.difficulty_var = tk.StringVar(value="District")
        self.difficulty_menu = ttk.Combobox(filters_frame, textvariable=self.difficulty_var, values=["District", "Regional", "State"], font=entry_font, state="readonly")
        self.difficulty_menu.grid(row=0, column=3, padx=5, pady=5)
        self.difficulty_menu.bind("<<ComboboxSelected>>", lambda e: self.update_difficulty())

        # Subjects Dropdown (Non-Editable)
        ttk.Label(filters_frame, text="Subjects:", font=label_font).grid(row=0, column=4, padx=5, pady=5)
        self.subjects_var = tk.StringVar(value="All")
        self.subjects_menu = ttk.Combobox(filters_frame, textvariable=self.subjects_var, values=["Language Arts", "Social Studies", "Arts and Humanities", "Math", "Science"], font=entry_font, state="readonly")
        self.subjects_menu.grid(row=0, column=5, padx=5, pady=5)
        self.subjects_menu.bind("<<ComboboxSelected>>", lambda e: self.update_subjects())

        # Reading Speed Slider
        speed_frame = ttk.LabelFrame(self.main_frame, text="Reading Speed")
        speed_frame.pack(pady=10, padx=10, fill=tk.X)

        # Slider: Faster on the right, slower on the left
        self.speed_slider = ttk.Scale(speed_frame, from_=0.1, to=0.01, orient=tk.HORIZONTAL, command=self.update_speed, length=400)
        self.speed_slider.set(self.reading_speed)
        self.speed_slider.pack(pady=10)

        # Question Display (Non-Editable)
        question_frame = ttk.LabelFrame(self.main_frame, text="Question")
        question_frame.pack(pady=10, padx=10, fill=tk.X)

        self.question_text = tk.Text(question_frame, height=10, width=80, wrap=tk.WORD, font=entry_font, state=tk.DISABLED)
        self.question_text.pack(pady=10)

        # Answer Input (Editable)
        answer_frame = ttk.LabelFrame(self.main_frame, text="Your Answer")
        answer_frame.pack(pady=10, padx=10, fill=tk.X)

        self.answer_entry = ttk.Entry(answer_frame, width=80, font=entry_font)
        self.answer_entry.pack(pady=10)
        self.answer_entry.bind("<Return>", lambda e: self.check_answer())  # Bind Enter key to submit answer

        # Timer Label
        timer_frame = ttk.LabelFrame(self.main_frame, text="Timer")
        timer_frame.pack(pady=10, padx=10, fill=tk.X)

        self.timer_label = ttk.Label(timer_frame, text=f"Time Left: {self.timer_seconds}", font=label_font)
        self.timer_label.pack(pady=10)

        # Buttons Frame
        buttons_frame = ttk.LabelFrame(self.main_frame, text="Actions")
        buttons_frame.pack(pady=10, padx=10, fill=tk.X)

        # Submit Button
        self.submit_button = ttk.Button(buttons_frame, text="Submit", command=self.check_answer, bootstyle="success")
        self.submit_button.grid(row=0, column=0, padx=5, pady=5)

        # Next Question Button
        self.next_button = ttk.Button(buttons_frame, text="Next Question", command=self.next_question, bootstyle="primary")
        self.next_button.grid(row=0, column=1, padx=5, pady=5)

        # Correct/Incorrect Buttons
        self.correct_button = ttk.Button(buttons_frame, text="I was correct", command=lambda: self.mark_answer(True), bootstyle="success")
        self.correct_button.grid(row=0, column=2, padx=5, pady=5)

        self.incorrect_button = ttk.Button(buttons_frame, text="I was incorrect", command=lambda: self.mark_answer(False), bootstyle="danger")
        self.incorrect_button.grid(row=0, column=3, padx=5, pady=5)

        # Randomize Button
        self.randomize_button = ttk.Button(buttons_frame, text="Randomize", command=self.randomize_questions, bootstyle="warning")
        self.randomize_button.grid(row=0, column=4, padx=5, pady=5)

        # Reset Button
        self.reset_button = ttk.Button(buttons_frame, text="Reset", command=self.reset_quiz, bootstyle="secondary")
        self.reset_button.grid(row=0, column=5, padx=5, pady=5)

        # Score Display
        score_frame = ttk.LabelFrame(self.main_frame, text="Score")
        score_frame.pack(pady=10, padx=10, fill=tk.X)

        self.score_label = ttk.Label(score_frame, text=f"Score: {self.score}/{self.total_questions}", font=label_font)
        self.score_label.pack(pady=10)

        # Keybinds
        self.setup_keybinds()

    def toggle_theme(self):
        """Toggle between light and dark mode."""
        if self.theme_var.get() == "light":
            self.current_theme = "cosmo"  # Light theme
        else:
            self.current_theme = "darkly"  # Dark theme

        # Update the theme
        self.root.style.theme_use(self.current_theme)

        # Update the background color of the canvas and main frame
        self.canvas.configure(bg=self.root.style.colors.bg)
        self.main_frame.configure(bootstyle=self.current_theme)

    def handle_settings_selection(self):
        """Handle selection from the settings dropdown menu."""
        selected = self.settings_var.get()
        if selected == "Keybind Settings":
            self.show_keybind_settings()
        elif selected == "Reading Speed":
            self.show_reading_speed_settings()
        elif selected == "Timer Settings":
            self.show_timer_settings()
        elif selected == "Manage Questions":
            self.show_manage_questions()
        elif selected == "Add New Question":
            self.add_question()

    def show_keybind_settings(self):
        """Display keybind settings."""
        messagebox.showinfo("Keybind Settings", f"Current Keybind for Submit Answer: {self.keybinds['submit_answer']}")

    def show_reading_speed_settings(self):
        """Display reading speed settings."""
        messagebox.showinfo("Reading Speed", f"Current Reading Speed: {self.reading_speed}")

    def show_timer_settings(self):
        """Display timer settings."""
        timer_window = ttk.Toplevel(self.root)
        timer_window.title("Timer Settings")
        timer_window.geometry("300x200")

        # Enable/Disable Timer
        ttk.Label(timer_window, text="Enable Timer:", font=("Arial", 12)).pack(pady=5)
        self.timer_enabled_var = tk.BooleanVar(value=self.timer_enabled)
        ttk.Checkbutton(timer_window, text="Enabled", variable=self.timer_enabled_var, command=self.update_timer_enabled).pack(pady=5)

        # Set Timer Duration
        ttk.Label(timer_window, text="Timer Duration (seconds):", font=("Arial", 12)).pack(pady=5)
        self.timer_duration_var = tk.IntVar(value=self.timer_seconds)
        ttk.Entry(timer_window, textvariable=self.timer_duration_var, font=("Arial", 12)).pack(pady=5)
        ttk.Button(timer_window, text="Save", command=self.update_timer_duration, bootstyle="success").pack(pady=10)

    def update_timer_enabled(self):
        """Update timer enabled state."""
        self.timer_enabled = self.timer_enabled_var.get()

    def update_timer_duration(self):
        """Update timer duration."""
        self.timer_seconds = self.timer_duration_var.get()
        messagebox.showinfo("Timer Settings", f"Timer duration updated to {self.timer_seconds} seconds.")

    def show_manage_questions(self):
        """Display manage questions options."""
        manage_window = ttk.Toplevel(self.root)
        manage_window.title("Manage Questions")
        manage_window.geometry("400x300")

        self.question_var = tk.StringVar()
        self.question_dropdown = ttk.Combobox(manage_window, textvariable=self.question_var, width=50, font=("Arial", 12), state="readonly")
        self.question_dropdown.pack(pady=10)
        self.update_question_dropdown()

        ttk.Button(manage_window, text="Delete Selected Question", command=self.delete_question, bootstyle="danger").pack(pady=10)

    def setup_keybinds(self):
        # Bind keys to actions
        self.root.bind(self.keybinds["submit_answer"], lambda e: self.check_answer())

    def load_keybinds(self):
        if os.path.exists("keybinds.json"):
            try:
                with open("keybinds.json", "r", encoding="utf-8") as file:
                    self.keybinds = json.load(file)
            except json.JSONDecodeError:
                messagebox.showerror("Error", "The keybinds file is corrupted or improperly formatted.")
        else:
            self.save_keybinds()  # Save default keybinds if file doesn't exist

    def save_keybinds(self):
        with open("keybinds.json", "w", encoding="utf-8") as file:
            json.dump(self.keybinds, file, indent=4)

    def load_questions(self):
        if os.path.exists("questions.json"):
            try:
                with open("questions.json", "r", encoding="utf-8") as file:
                    questions_data = json.load(file)
                    return [Question.from_dict(q) for q in questions_data]
            except json.JSONDecodeError:
                messagebox.showerror("Error", "The questions file is corrupted or improperly formatted.")
                return []
        else:
            return []  # Return an empty list if the file doesn't exist

    def save_questions(self):
        with open("questions.json", "w", encoding="utf-8") as file:
            questions_data = [q.to_dict() for q in self.all_questions]
            json.dump(questions_data, file, indent=4, ensure_ascii=False)

    def update_question_dropdown(self):
        self.question_dropdown["values"] = [q.text for q in self.all_questions]

    def delete_question(self):
        selected_text = self.question_var.get()
        if not selected_text:
            messagebox.showwarning("No Selection", "Please select a question to delete.")
            return

        for question in self.all_questions:
            if question.text == selected_text:
                self.all_questions.remove(question)
                self.save_questions()
                self.filter_questions()
                self.update_question_dropdown()
                messagebox.showinfo("Deleted", "Question deleted successfully.")
                return

    def update_score(self):
        self.score_label.config(text=f"Score: {self.score}/{self.total_questions}")

    def update_year(self):
        self.selected_year = int(self.year_var.get())
        self.filter_questions()

    def update_difficulty(self):
        self.selected_difficulty = self.difficulty_var.get()
        self.filter_questions()

    def update_subjects(self):
        selected = self.subjects_var.get()
        if selected == "All":
            self.selected_subjects = set()
        else:
            self.selected_subjects = {selected}
        self.filter_questions()

    def update_speed(self, value):
        self.reading_speed = float(value)

    def filter_questions(self):
        self.filtered_questions = [
            q for q in self.all_questions
            if (not self.selected_subjects or any(subject in self.selected_subjects for subject in q.subjects)) and
               q.difficulty == self.selected_difficulty and
               q.year == self.selected_year
        ]
        if not self.filtered_questions:
            self.question_text.config(state=tk.NORMAL)
            self.question_text.delete(1.0, tk.END)
            self.question_text.insert(tk.END, "No questions match selected filters.")
            self.question_text.config(state=tk.DISABLED)
            return
        self.question_index = 0
        self.start_reading()

    def start_reading(self):
        if not self.filtered_questions:
            return
        self.reading_text = ""
        self.read_index = 0
        self.reading_active = True  # Enable text display
        question_text = self.filtered_questions[self.question_index].text

        # Start text display
        self.update_reading_text(question_text)

    def update_reading_text(self, question_text: str):
        if self.reading_active and self.read_index < len(question_text):
            self.reading_text += question_text[self.read_index]
            self.question_text.config(state=tk.NORMAL)
            self.question_text.delete(1.0, tk.END)
            self.question_text.insert(tk.END, self.reading_text)
            self.question_text.config(state=tk.DISABLED)
            self.read_index += 1
            self.root.after(int(self.reading_speed * 1000), self.update_reading_text, question_text)
        elif not self.reading_active:
            # Stop text display if reading is no longer active
            return
        else:
            self.start_timer()  # Start the 5-second timer after the question is fully read

    def start_timer(self):
        """Start the timer."""
        if not self.timer_enabled:
            return
        self.timer_running = True
        self.timer_seconds = self.timer_seconds  # Reset to configured duration
        self.update_timer()

    def update_timer(self):
        """Update the timer every second."""
        if self.timer_running:
            self.timer_label.config(text=f"Time Left: {self.timer_seconds}")
            if self.timer_seconds > 0:
                self.timer_seconds -= 1
                self.root.after(1000, self.update_timer)
            else:
                self.timer_running = False
                self.timer_label.config(text="Time's up!")
                self.reveal_question()  # Reveal the question when the timer ends

    def reveal_question(self):
        """Reveal the full question and correct answer."""
        if not self.filtered_questions:
            return

        # Stop text display
        self.reading_active = False

        # Display the full question text and correct answer
        self.question_text.config(state=tk.NORMAL)
        self.question_text.delete(1.0, tk.END)
        self.question_text.insert(tk.END, f"Question: {self.filtered_questions[self.question_index].text}\n\n")
        self.question_text.insert(tk.END, f"Correct Answer: {self.filtered_questions[self.question_index].answer}\n\n")
        if hasattr(self, "is_correct"):  # Only show correctness if the user has submitted an answer
            if self.is_correct:
                self.question_text.insert(tk.END, "Your answer was CORRECT!", "correct")
            else:
                self.question_text.insert(tk.END, "Your answer was INCORRECT!", "incorrect")
        self.question_text.config(state=tk.DISABLED)

    def check_answer(self):
        if not self.filtered_questions or self.submitted:  # Check if already submitted
            return

        # Stop the reading timer if it's running
        if self.timer_running:
            self.timer_running = False

        # Stop text display
        self.reading_active = False

        # Get the user's answer
        self.user_answer = self.answer_entry.get()
        self.is_correct = self.user_answer.lower() == self.filtered_questions[self.question_index].answer.lower()
        self.show_answer = True

        # Update score (only numerator)
        if self.is_correct:
            self.score += 1  # Increment score if the answer is correct
        self.update_score()

        # Display the full question text, correct answer, and whether the user was correct
        self.reveal_question()

        # Clear the answer box
        self.answer_entry.delete(0, tk.END)

        # Mark the question as submitted
        self.submitted = True  # Set the flag to prevent further submissions

    def next_question(self):
        """Move to the next question."""
        if self.next_question_cooldown:
            return  # Ignore if cooldown is active

        # Start cooldown
        self.next_question_cooldown = True
        self.root.after(1500, lambda: setattr(self, "next_question_cooldown", False))  # 1.5-second cooldown

        # Stop the reading timer if it's running
        if self.timer_running:
            self.timer_running = False

        # Stop text display
        self.reading_active = False

        if self.question_index < len(self.filtered_questions) - 1 and self.filtered_questions:
            self.question_index += 1
            self.user_answer = ""
            self.show_answer = False
            self.answer_entry.delete(0, tk.END)  # Clear the answer box
            self.score_updated = False  # Reset the score update flag for the new question
            self.submitted = False  # Reset the submission flag for the new question
            self.total_questions += 1  # Increment the denominator by 1
            self.update_score()
            self.start_reading()

    def mark_answer(self, correct: bool):
        if not self.filtered_questions or self.score_updated:
            return  # Ignore if no questions or score already updated for this question

        self.score_updated = True  # Mark score as updated for this question
        if correct:
            self.score += 1
        else:
            self.score -= 1
        self.update_score()

    def randomize_questions(self):
        """Randomize the order of questions."""
        if self.filtered_questions:
            random.shuffle(self.filtered_questions)
            self.question_index = 0
            self.start_reading()
            messagebox.showinfo("Randomized", "Questions have been randomized!")

    def reset_quiz(self):
        """Reset the quiz to start over with the same set of questions."""
        self.question_index = 0
        self.score = 0
        self.total_questions = 0
        self.update_score()
        self.start_reading()
        messagebox.showinfo("Reset", "Quiz has been reset!")

    def add_question(self):
        self.is_adding_question = True
        add_window = ttk.Toplevel(self.root)
        add_window.title("Add New Question")
        add_window.geometry("400x300")

        ttk.Label(add_window, text="Question Text:").pack()
        question_text_entry = ttk.Entry(add_window, width=50)
        question_text_entry.pack()

        ttk.Label(add_window, text="Answer:").pack()
        answer_entry = ttk.Entry(add_window, width=50)
        answer_entry.pack()

        ttk.Label(add_window, text="Subjects:").pack()
        subjects_var = tk.StringVar(value="Language Arts")
        subjects_menu = ttk.Combobox(add_window, textvariable=subjects_var, values=["Language Arts", "Social Studies", "Arts and Humanities", "Math", "Science"], state="readonly")
        subjects_menu.pack()

        ttk.Label(add_window, text="Difficulty:").pack()
        difficulty_var = tk.StringVar(value="District")
        difficulty_menu = ttk.Combobox(add_window, textvariable=difficulty_var, values=["District", "Regional", "State"], state="readonly")
        difficulty_menu.pack()

        ttk.Label(add_window, text="Year:").pack()
        year_var = tk.StringVar(value="2024")
        year_menu = ttk.Combobox(add_window, textvariable=year_var, values=[str(year) for year in range(2017, 2025)], state="readonly")
        year_menu.pack()

        def save_question():
            text = question_text_entry.get().strip()
            answer = answer_entry.get().strip()
            if not text or not answer:
                messagebox.showwarning("Input Error", "Question text and answer cannot be empty.")
                return
            subjects = [subjects_var.get()]
            difficulty = difficulty_var.get()
            year = int(year_var.get())
            new_question = Question(text, answer, subjects, difficulty, year)
            self.all_questions.append(new_question)
            self.save_questions()
            self.filter_questions()
            self.update_question_dropdown()
            add_window.destroy()

        ttk.Button(add_window, text="Save", command=save_question, bootstyle="success").pack()


if __name__ == "__main__":
    # Use TTKBootstrap's themed window
    root = ttk.Window(themename="cosmo")
    app = ContentView(root)
    root.mainloop()
