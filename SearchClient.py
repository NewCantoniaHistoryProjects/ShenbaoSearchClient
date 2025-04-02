import os
import re
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
from threading import Thread
from queue import Queue
from pathlib import Path

class ShenbaoSearchApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Shenbao Newspaper Search")
        self.root.geometry("1200x800")
        
        self.txt_dir = Path("shenbao-txt/txt")
        self.recent_searches_file = Path("recent_searches.txt")
        self.years = self.get_year_range()
        
        if not self.check_text_folder():
            return
        
        self.recent_searches = self.load_recent_searches()
        self.create_widgets()
        
        self.result_queue = Queue()
        self.results = []
        self.processed_files = set()
        self.sort_ascending = True
        self.search_thread = None
        self.file_buttons = []  # Store buttons for cleanup

    def check_text_folder(self):
        if not self.txt_dir.exists() or not self.txt_dir.is_dir():
            messagebox.showerror(
                "Setup Error",
                "The 'shenbao-txt/txt' directory is missing.\n\n"
                "Please run: git clone https://github.com/moss-on-stone/shenbao-txt.git\n"
                "Then restart the application."
            )
            self.root.quit()
            return False
        if not any(self.txt_dir.glob("*.txt")):
            messagebox.showerror(
                "Setup Error",
                "No .txt files found in 'shenbao-txt/txt'.\n\n"
                "Ensure you cloned: git clone https://github.com/moss-on-stone/shenbao-txt.git\n"
                "Then restart the application."
            )
            self.root.quit()
            return False
        return True

    def get_year_range(self):
        years = set()
        for file in self.txt_dir.glob("*.txt"):
            year = int(str(file.name)[:4])
            years.add(year)
        return sorted(years)

    def load_recent_searches(self):
        if self.recent_searches_file.exists():
            with open(self.recent_searches_file, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines() if line.strip()][-5:]
        return []

    def save_recent_searches(self, keyword):
        if keyword in self.recent_searches:
            self.recent_searches.remove(keyword)
        self.recent_searches.append(keyword)
        self.recent_searches = self.recent_searches[-5:]
        with open(self.recent_searches_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.recent_searches))
        self.update_recent_search_buttons()

    def create_widgets(self):
        search_frame = ttk.Frame(self.root, padding="10")
        search_frame.pack(fill="x")

        ttk.Label(search_frame, text="Keyword:").grid(row=0, column=0, padx=5)
        self.keyword_entry = ttk.Entry(search_frame, width=30)
        self.keyword_entry.grid(row=0, column=1, padx=5)
        self.keyword_entry.bind("<Return>", lambda e: self.start_search())

        self.search_mode = tk.StringVar(value="regex")
        ttk.Radiobutton(search_frame, text="Regex", variable=self.search_mode, 
                       value="regex").grid(row=0, column=2, padx=5)
        ttk.Radiobutton(search_frame, text="Whole Word", variable=self.search_mode, 
                       value="whole").grid(row=0, column=3, padx=5)
        ttk.Radiobutton(search_frame, text="Vague", variable=self.search_mode, 
                       value="vague").grid(row=0, column=4, padx=5)

        self.search_button = ttk.Button(search_frame, text="Search", command=self.start_search)
        self.search_button.grid(row=0, column=5, padx=5)

        self.sort_button = ttk.Button(search_frame, text="Sort Ascending", command=self.toggle_sort)
        self.sort_button.grid(row=0, column=6, padx=5)

        ttk.Label(search_frame, text="Year From:").grid(row=1, column=0, pady=5)
        self.year_from = ttk.Combobox(search_frame, values=[str(y) for y in self.years], width=6)
        self.year_from.grid(row=1, column=1)
        ttk.Button(search_frame, text="Reset", command=self.reset_year_from).grid(row=1, column=2, padx=5)

        ttk.Label(search_frame, text="To:").grid(row=1, column=3)
        self.year_to = ttk.Combobox(search_frame, values=[str(y) for y in self.years], width=6)
        self.year_to.grid(row=1, column=4)
        ttk.Button(search_frame, text="Reset", command=self.reset_year_to).grid(row=1, column=5, padx=5)

        recent_frame = ttk.Frame(self.root, padding="10")
        recent_frame.pack(fill="x")
        ttk.Label(recent_frame, text="Recent Searches:").pack(side="left")
        self.recent_buttons = []
        self.update_recent_search_buttons()

        # Frame for results with scrollbar
        self.results_frame = ttk.Frame(self.root, padding="10")
        self.results_frame.pack(fill="both", expand=True)
        self.results_text = scrolledtext.ScrolledText(self.results_frame, wrap=tk.WORD, width=90, height=30)
        self.results_text.pack(side="left", fill="both", expand=True)

        self.progress = ttk.Label(self.root, text="")
        self.progress.pack(pady=5)

    def update_recent_search_buttons(self):
        for button in self.recent_buttons:
            button.destroy()
        self.recent_buttons.clear()
        
        recent_frame = self.root.winfo_children()[1]
        for i, keyword in enumerate(self.recent_searches):
            button = ttk.Button(recent_frame, text=keyword, 
                              command=lambda k=keyword: self.reuse_search(k))
            button.pack(side="left", padx=5)
            self.recent_buttons.append(button)

    def reuse_search(self, keyword):
        self.keyword_entry.delete(0, tk.END)
        self.keyword_entry.insert(0, keyword)
        self.start_search()

    def reset_year_from(self):
        self.year_from.set("")

    def reset_year_to(self):
        self.year_to.set("")

    def toggle_sort(self):
        self.sort_ascending = not self.sort_ascending
        self.sort_button.config(text="Sort Ascending" if self.sort_ascending else "Sort Descending")
        self.display_results()

    def start_search(self):
        if self.search_thread and self.search_thread.is_alive():
            return

        keyword = self.keyword_entry.get().strip()
        if not keyword:
            return

        self.results_text.delete(1.0, tk.END)
        self.clear_file_buttons()  # Clear previous buttons
        self.progress.config(text="Searching...")
        self.results = []
        self.processed_files.clear()
        
        self.save_recent_searches(keyword)
        
        while not self.result_queue.empty():
            self.result_queue.get()

        self.search_button.config(state="disabled")
        self.search_thread = Thread(target=self.search_files, args=(keyword,), daemon=True)
        self.search_thread.start()
        
        self.root.after(200, self.check_queue)

    def search_files(self, keyword):
        files = [f for f in self.txt_dir.glob("*.txt")]
        year_from = self.year_from.get() or str(min(self.years))
        year_to = self.year_to.get() or str(max(self.years))
        
        mode = self.search_mode.get()
        if mode == "whole":
            keyword = r"\b" + re.escape(keyword) + r"\b"
        elif mode == "vague":
            keyword = ".*" + ".*".join(re.escape(c) for c in keyword) + ".*"

        total_files = len(files)
        processed = 0

        for file in files:
            year = int(str(file.name)[:4])
            if not (int(year_from) <= year <= int(year_to)):
                continue

            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                continue

            pages = re.split(r'Page (\d+)', content)[1:]
            results = []
            
            for i in range(0, len(pages), 2):
                page_num = pages[i]
                page_content = pages[i + 1]
                matches = list(re.finditer(keyword, page_content, re.IGNORECASE))
                
                for match in matches:
                    start = max(0, match.start() - 30)
                    end = min(len(page_content), match.end() + 30)
                    context = page_content[start:end].replace('\n', ' ')
                    results.append((page_num, match.group(), context))

            if results:
                self.result_queue.put((file.name, results))
            
            processed += 1
            self.result_queue.put(("progress", processed, total_files))

        self.result_queue.put(("done", total_files))

    def open_file(self, filename):
        """Open the text file in the default system editor."""
        file_path = self.txt_dir / filename
        try:
            if os.name == 'nt':  # Windows
                os.startfile(str(file_path))
            else:  # macOS or Linux
                opener = 'open' if os.uname().sysname == 'Darwin' else 'xdg-open'
                os.system(f"{opener} {str(file_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open {filename}: {e}")

    def clear_file_buttons(self):
        """Remove all existing file buttons."""
        for button in self.file_buttons:
            button.destroy()
        self.file_buttons.clear()

    def display_results(self):
        self.results_text.delete(1.0, tk.END)
        self.clear_file_buttons()
        if not self.results:
            return

        sorted_results = sorted(self.results, key=lambda x: int(x[0][:4]), reverse=not self.sort_ascending)

        for filename, matches in sorted_results:
            # Insert filename with bold formatting
            self.results_text.insert(tk.END, f"\nFile: {filename} ", "bold")
            # Add an "Open" button next to the filename
            button = ttk.Button(self.results_frame, text="Open", 
                              command=lambda fn=filename: self.open_file(fn))
            button_window = self.results_text.window_create(tk.END, window=button)
            self.file_buttons.append(button)
            self.results_text.insert(tk.END, "\n")
            
            # List matches below the filename
            for page, match, context in matches:
                display_text = f"Page {page}: ...{context}...\n"
                self.results_text.insert(tk.END, display_text)
                start_idx = self.results_text.search(match, tk.END, backwards=True)
                if start_idx:
                    end_idx = f"{start_idx}+{len(match)}c"
                    self.results_text.tag_add("highlight", start_idx, end_idx)

    def check_queue(self):
        try:
            while not self.result_queue.empty():
                item = self.result_queue.get_nowait()
                if item[0] == "progress":
                    _, processed, total = item
                    self.progress.config(text=f"Processed {processed}/{total} files")
                elif item[0] == "done":
                    _, total_files = item
                    total_matches = sum(len(matches) for _, matches in self.results)
                    total_files_with_matches = len(self.results)
                    self.progress.config(text=f"Search Completed: {total_matches} matches in {total_files_with_matches} files")
                    self.search_button.config(state="normal")
                    self.display_results()
                else:
                    filename, matches = item
                    if filename not in self.processed_files:
                        self.results.append((filename, matches))
                        self.processed_files.add(filename)
                    else:
                        for i, (existing_fn, existing_matches) in enumerate(self.results):
                            if existing_fn == filename:
                                self.results[i] = (filename, existing_matches + matches)
                                break
                    self.display_results()
        except:
            pass
        
        if self.search_thread and self.search_thread.is_alive():
            self.root.after(200, self.check_queue)
        else:
            self.search_thread = None

    def run(self):
        self.results_text.tag_configure("bold", font=("Helvetica", 10, "bold"))
        self.results_text.tag_configure("highlight", background="yellow")
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = ShenbaoSearchApp(root)
    app.run()