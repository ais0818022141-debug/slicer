#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TealMED Master Studio & Question Bank Control Center
====================================================
Unified graphical command center uniting all TealMED tools into a single,
beautiful, and sequentially ordered desktop application.

Organized by the clinical publishing pipeline:
  Phase 1: Ingestion & Slicing
  Phase 2: AI Enrichment & Explanations
  Phase 3: Topic Classification & Sorting
  Phase 4: Synchronization & Data Integrity
  Phase 5: Publishing & PDF/HTML Study Views
  Phase 6: Clinical Study Notes Studio
"""

import os
import sys
import subprocess
import threading
from pathlib import Path

# Enable High-DPI sharpness on Windows
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog

BASE_DIR = Path(__file__).resolve().parent

# -----------------------------------------------------------------------------
# Tool Definitions & Explanations (Ordered by Pipeline)
# -----------------------------------------------------------------------------
PIPELINE_TOOLS = [
    # Phase 1
    {
        "phase": "Phase 1: Ingestion & Slicing",
        "phase_color": "#2563eb",
        "id": "slicer",
        "title": "TealMED Fast Slicer Pipeline",
        "script": "tools/slicer.py",
        "badge": "Splits & Converts",
        "what_it_does": "Splits large raw medical question banks (Excel / CSV) into manageable chunks (e.g. 12 questions per file) and converts each chunk directly into TealMED JSON and AI Markdown prompt files.",
        "how_it_works": "Click Launch -> Select your raw Excel/CSV file -> Enter subject prefix (e.g. cardio, renal) and rows per chunk -> Outputs organized subfolders: csv/, json/, and md/ with sequential IDs.",
        "args": []
    },
    {
        "phase": "Phase 1: Ingestion & Slicing",
        "phase_color": "#2563eb",
        "id": "txt_to_csv",
        "title": "Text & Markdown to CSV Converter",
        "script": "tools/txt_to_csv.py",
        "badge": "mcq.txt -> CSV",
        "what_it_does": "Converts plain text or markdown questions (e.g. mcq.txt copied from drafts or AI outputs) into a structured TealMED CSV format with full choices (A-F), correct answer, and High Yield Notes.",
        "how_it_works": "Click Launch -> Select your text file (e.g. mcq.txt) -> Automatically parses question stems, choices, and explanations into a clean, slicer-ready CSV file.",
        "args": []
    },
    {
        "phase": "Phase 1: Ingestion & Slicing",
        "phase_color": "#2563eb",
        "id": "tealmed_converter",
        "title": "Medical Schema Normalizer",
        "script": "tools/tealmed_converter.py",
        "badge": "Data Integrity",
        "what_it_does": "Converts raw question files into production-grade TealMED JSON database format with safe HTML tag stripping that carefully protects clinical inequality signs (e.g. < 30 g/L, > 140 mmHg).",
        "how_it_works": "Click Launch -> Pick CSV/Excel file -> Generates clean database JSON with collision-free sequential IDs (q_prefix_01..NN) and randomized option distribution.",
        "args": []
    },
    {
        "phase": "Phase 1: Ingestion & Slicing",
        "phase_color": "#2563eb",
        "id": "build_from_md_template",
        "title": "Markdown Template to Final Subject Builder",
        "script": "tools/build_from_md_template.py",
        "badge": "MD -> Full final/",
        "what_it_does": "Builds the complete final/ subject folder directly from a filled Markdown questions template (CSV, JSON, AI prompts, topics CSVs, sessions CSVs, and topics_md).",
        "how_it_works": "Click Launch -> Select your Markdown template file (e.g. QUESTION_TEMPLATE.md) -> Automatically compiles and registers everything into final/<subject>/ and manifest.json.",
        "args": []
    },

    # Phase 2
    {
        "phase": "Phase 2: AI Enrichment & Explanations",
        "phase_color": "#7c3aed",
        "id": "ai_preparer",
        "title": "AI Prompt Preparer",
        "script": "tools/ai_preparer.py",
        "badge": "Token-Optimized Prompts",
        "what_it_does": "Generates concise, token-optimized Markdown prompts (_ai.md) from question files ready to feed into AI models (ChatGPT, Claude, Gemini) to generate high-yield clinical explanations.",
        "how_it_works": "Click Launch -> Select JSON or CSV files -> Outputs compact prompt files formatted specifically for medical AI models.",
        "args": []
    },
    {
        "phase": "Phase 2: AI Enrichment & Explanations",
        "phase_color": "#7c3aed",
        "id": "explanation_updater",
        "title": "Clinical Explanations Batch Updater",
        "script": "tools/explanation_updater.py",
        "badge": "Batch Injector",
        "what_it_does": "Parses structured explanations returned by AI models (Educational Objective, High Yield Note, Clinical Explanation) and injects them directly into both JSON and CSV question banks.",
        "how_it_works": "Click Launch -> Select the question bank files to update -> Select the text file containing the AI explanations -> Automatically matches IDs and updates Explanation and High_Yield_Note.",
        "args": []
    },
    {
        "phase": "Phase 2: AI Enrichment & Explanations",
        "phase_color": "#7c3aed",
        "id": "export_explained_topics_md",
        "title": "Explained Topics Markdown Exporter",
        "script": "tools/export_explained_topics_md.py",
        "badge": "AI MD + Topics",
        "what_it_does": "Generates unified Markdown question banks with clinical explanations: creates '<subject>_all_explained.md' and splits questions by topic into individual Markdown files inside 'topics_md/'.",
        "how_it_works": "Click Launch -> Select target subject (or all 23 subjects) -> Exports complete questions with Educational Objective, High Yield Note, and Explanation partitioned by topic.",
        "args": ["--gui"]
    },

    # Phase 3
    {
        "phase": "Phase 3: Topic Classification & Sorting",
        "phase_color": "#059669",
        "id": "topic_updater",
        "title": "Topic Classifier & Batch Updater",
        "script": "tools/topic_updater.py",
        "badge": "Chapter Mapping",
        "what_it_does": "Batch-assigns standardized medical chapter/topic names (e.g. أمراض الصمامات, أمراض الكبيبات) to questions in JSON, CSV, and Markdown files from a simple numbered text list.",
        "how_it_works": "Click Launch -> Select target files -> Select text file containing topic list (e.g. 1. Topic A, 2. Topic B) -> Injects Chapter_or_Section into all matching questions.",
        "args": []
    },
    {
        "phase": "Phase 3: Topic Classification & Sorting",
        "phase_color": "#059669",
        "id": "topic_sorter",
        "title": "Topic Grouper & Chronological Sorter",
        "script": "tools/topic_sorter.py",
        "badge": "Date & Topic Sorter",
        "what_it_does": "Groups all questions for a subject by topic, and sorts questions chronologically within each topic from newest exam session (e.g. May 2026) down to oldest session.",
        "how_it_works": "Click Launch -> Select question files -> Organizes questions by topic and outputs sorted JSON, CSV, and AI Markdown files into classified/ subfolder.",
        "args": []
    },
    {
        "phase": "Phase 3: Topic Classification & Sorting",
        "phase_color": "#059669",
        "id": "merger",
        "title": "Sequential File Merger",
        "script": "tools/merger.py",
        "badge": "Chunks -> Master File",
        "what_it_does": "Combines multiple chunk files (e.g. cardio_01 through cardio_17) back into a single unified master file (cardio_all.json / cardio_all.csv) in exact natural chronological and numerical order.",
        "how_it_works": "Click Launch -> Choose JSON or CSV -> Select multiple chunk files -> Concatenates all rows into a single master file with unified headers and no data loss.",
        "args": []
    },

    # Phase 4
    {
        "phase": "Phase 4: Synchronization & Data Integrity",
        "phase_color": "#d97706",
        "id": "file_syncer",
        "title": "Bidirectional File Synchronizer (JSON ⇄ CSV)",
        "script": "file_syncer.py",
        "badge": "100% Fidelity Sync",
        "what_it_does": "Keeps companion JSON and CSV files in 100% verbatim sync. When you edit either file in Excel or VS Code, it updates the companion file with zero metadata loss. Includes High_Yield_Note column and dynamic 4, 5, or 6 options per question.",
        "how_it_works": "Click Launch -> Select edited file as Source -> Counterpart is updated automatically. Creates timestamped backups and provides full difference reports.",
        "args": ["--gui"]
    },

    # Phase 5
    {
        "phase": "Phase 5: Publishing & PDF/HTML Study Views",
        "phase_color": "#dc2626",
        "id": "generator",
        "title": "Dual-View PDF & Study HTML Generator",
        "script": "pdf_maker/generator.py",
        "badge": "Interactive & Print-Ready",
        "what_it_does": "Produces high-density, beautifully styled interactive HTML question banks with dedicated Arabic typography (Alexandria for questions, IBM Plex Sans Arabic for explanations), High-Yield callout cards, and instant Print-to-PDF styles. Generates dual views: By Topics and By Sessions.",
        "how_it_works": "Click Launch -> Select any question bank (.json or .csv) or click 'Regenerate All' -> Opens interactive dual views in your browser, ready for direct print to PDF.",
        "args": ["--gui"]
    },

    # Phase 6
    {
        "phase": "Phase 6: Clinical Study Notes Studio",
        "phase_color": "#0891b2",
        "id": "notes_studio",
        "title": "Clinical Notes Studio & Visual Pipeline",
        "script": "notes/run_studio.py",
        "badge": "Markdown -> Notes Cards",
        "what_it_does": "Converts medical summary notes from Markdown into platform-ready JSON/CSV study cards with an interactive visual studio, live preview, and batch processing.",
        "how_it_works": "Click Launch -> Opens the interactive Notes Studio window -> Load your study notes markdown files to convert, preview, and export.",
        "args": []
    }
]


class TealMedMasterCenter:
    """Master Unified Desktop Dashboard for all TealMED Question Bank tools."""

    def __init__(self, root):
        self.root = root
        self.root.title("TealMED Studio - Master Question Bank Control Center")
        self.root.geometry("1100x820")
        self.root.minsize(980, 680)

        # Center on screen
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, int((sw - 1100) / 2))
            y = max(0, int((sh - 820) / 2))
            self.root.geometry(f"1100x820+{x}+{y}")
        except Exception:
            pass

        self.style = ttk.Style(self.root)
        for theme in ['vista', 'clam', 'default']:
            if theme in self.style.theme_names():
                self.style.theme_use(theme)
                break

        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *args: self.filter_cards())
        self.card_frames = []

        self._build_ui()

    def _build_ui(self):
        # 1. Top Header Banner
        header = tk.Frame(self.root, bg="#0f172a", padx=20, pady=14)
        header.pack(fill=tk.X)

        title_lbl = tk.Label(
            header,
            text="TealMED Studio - Master Question Bank Suite",
            font=("Segoe UI", 16, "bold"),
            fg="#ffffff",
            bg="#0f172a"
        )
        title_lbl.pack(anchor=tk.W)

        subtitle_lbl = tk.Label(
            header,
            text="Complete End-to-End Medical Publishing Pipeline: Ingestion -> AI Enrichment -> Classification -> Sync -> PDF/HTML Export",
            font=("Segoe UI", 9),
            fg="#94a3b8",
            bg="#0f172a"
        )
        subtitle_lbl.pack(anchor=tk.W, pady=(2, 0))

        # 2. Quick Action Toolbar
        toolbar = tk.Frame(self.root, bg="#1e293b", padx=16, pady=8)
        toolbar.pack(fill=tk.X)

        # Search / Filter
        tk.Label(toolbar, text="Filter Tools:", font=("Segoe UI", 9, "bold"), fg="#e2e8f0", bg="#1e293b").pack(side=tk.LEFT, padx=(0, 6))
        search_entry = ttk.Entry(toolbar, textvariable=self.filter_var, width=22)
        search_entry.pack(side=tk.LEFT, padx=(0, 14))

        # Action Buttons
        btn_sync_all = tk.Button(
            toolbar,
            text="⚡ Auto-Sync All Banks",
            font=("Segoe UI", 8, "bold"),
            bg="#d97706",
            fg="#ffffff",
            activebackground="#b45309",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.run_auto_sync_all
        )
        btn_sync_all.pack(side=tk.LEFT, padx=4)

        btn_regen_all = tk.Button(
            toolbar,
            text="📄 Regenerate All PDF / HTML",
            font=("Segoe UI", 8, "bold"),
            bg="#dc2626",
            fg="#ffffff",
            activebackground="#b91c1c",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.run_regenerate_all_pdf
        )
        btn_regen_all.pack(side=tk.LEFT, padx=4)

        btn_open_out = tk.Button(
            toolbar,
            text="📁 Open HTML Output Folder",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.open_output_folder
        )
        btn_open_out.pack(side=tk.RIGHT, padx=4)

        btn_open_ws = tk.Button(
            toolbar,
            text="📂 Open Workspace Folder",
            font=("Segoe UI", 8),
            bg="#334155",
            fg="#ffffff",
            activebackground="#475569",
            activeforeground="#ffffff",
            relief=tk.FLAT,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self.open_workspace_folder
        )
        btn_open_ws.pack(side=tk.RIGHT, padx=4)

        # 3. Main Scrollable Canvas for Cards
        body_container = tk.Frame(self.root, bg="#f1f5f9")
        body_container.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(body_container, bg="#f1f5f9", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(body_container, orient=tk.VERTICAL, command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f1f5f9", padx=16, pady=12)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(xscrollcommand=None, yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Ensure canvas window stretches with resize
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width)
        )

        # Mouse wheel scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Render Cards
        self._render_tool_cards()

        # 4. Bottom Activity & Execution Output Log
        log_frame = ttk.LabelFrame(self.root, text=" Live Execution Log & Status ", padding=6)
        log_frame.pack(fill=tk.X, padx=14, pady=(4, 6))

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=5,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#0f172a",
            fg="#f8fafc",
            insertbackground="#ffffff"
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(6, 0))

        ttk.Button(log_btn_frame, text="Clear Log", command=self.clear_log, width=11).pack(pady=2)
        ttk.Button(log_btn_frame, text="Copy Log", command=self.copy_log, width=11).pack(pady=2)

        self.log("TealMED Control Center initialized. Ready.")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _render_tool_cards(self):
        current_phase = None

        for idx, tool in enumerate(PIPELINE_TOOLS, start=1):
            phase = tool["phase"]
            phase_color = tool["phase_color"]

            # If new phase, insert Phase Section Header
            if phase != current_phase:
                current_phase = phase
                phase_hdr = tk.Frame(self.scrollable_frame, bg="#f1f5f9", pady=6)
                phase_hdr.pack(fill=tk.X, pady=(10 if idx > 1 else 2, 4))

                dot = tk.Label(phase_hdr, text="●", font=("Segoe UI", 12), fg=phase_color, bg="#f1f5f9")
                dot.pack(side=tk.LEFT, padx=(4, 6))

                lbl = tk.Label(
                    phase_hdr,
                    text=phase.upper(),
                    font=("Segoe UI", 11, "bold"),
                    fg=phase_color,
                    bg="#f1f5f9"
                )
                lbl.pack(side=tk.LEFT)

            # Tool Card Frame
            card = tk.Frame(
                self.scrollable_frame,
                bg="#ffffff",
                bd=1,
                relief=tk.SOLID,
                padx=14,
                pady=10
            )
            card.pack(fill=tk.X, pady=4)
            card.tool_data = tool
            self.card_frames.append(card)

            # Card Top Row: Index + Title + Badge + Launch Button
            top_row = tk.Frame(card, bg="#ffffff")
            top_row.pack(fill=tk.X)

            # Number badge
            num_lbl = tk.Label(
                top_row,
                text=f"{idx:02d}",
                font=("Segoe UI", 11, "bold"),
                fg=phase_color,
                bg="#ffffff",
                width=3,
                anchor=tk.W
            )
            num_lbl.pack(side=tk.LEFT)

            # Title
            title_lbl = tk.Label(
                top_row,
                text=tool["title"],
                font=("Segoe UI", 11, "bold"),
                fg="#0f172a",
                bg="#ffffff"
            )
            title_lbl.pack(side=tk.LEFT, padx=(2, 8))

            # Script file tag
            script_lbl = tk.Label(
                top_row,
                text=f"({tool['script']})",
                font=("Consolas", 8),
                fg="#64748B",
                bg="#ffffff"
            )
            script_lbl.pack(side=tk.LEFT, padx=(0, 8))

            # Badge
            badge_lbl = tk.Label(
                top_row,
                text=f" {tool['badge']} ",
                font=("Segoe UI", 8, "bold"),
                fg="#ffffff",
                bg=phase_color,
                padx=4,
                pady=1
            )
            badge_lbl.pack(side=tk.LEFT)

            # Launch Button (Far Right)
            launch_btn = tk.Button(
                top_row,
                text="▶ Launch Tool",
                font=("Segoe UI", 9, "bold"),
                bg="#0f172a",
                fg="#ffffff",
                activebackground=phase_color,
                activeforeground="#ffffff",
                relief=tk.FLAT,
                padx=12,
                pady=4,
                cursor="hand2",
                command=lambda t=tool: self.launch_tool(t)
            )
            launch_btn.pack(side=tk.RIGHT)

            # Card Middle: What it does
            desc_row = tk.Frame(card, bg="#ffffff", pady=3)
            desc_row.pack(fill=tk.X, padx=(28, 0))

            tk.Label(
                desc_row,
                text="• Purpose:",
                font=("Segoe UI", 8, "bold"),
                fg="#334155",
                bg="#ffffff",
                width=9,
                anchor=tk.W
            ).pack(side=tk.LEFT, anchor=tk.N)

            desc_txt = tk.Label(
                desc_row,
                text=tool["what_it_does"],
                font=("Segoe UI", 9),
                fg="#1e293b",
                bg="#ffffff",
                justify=tk.LEFT,
                wraplength=860
            )
            desc_txt.pack(side=tk.LEFT, fill=tk.X, expand=True)

            # Card Bottom: How it works
            how_row = tk.Frame(card, bg="#ffffff", pady=2)
            how_row.pack(fill=tk.X, padx=(28, 0))

            tk.Label(
                how_row,
                text="• Workflow:",
                font=("Segoe UI", 8, "bold"),
                fg="#0369a1",
                bg="#ffffff",
                width=9,
                anchor=tk.W
            ).pack(side=tk.LEFT, anchor=tk.N)

            how_txt = tk.Label(
                how_row,
                text=tool["how_it_works"],
                font=("Segoe UI", 8, "italic"),
                fg="#475569",
                bg="#ffffff",
                justify=tk.LEFT,
                wraplength=860
            )
            how_txt.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def filter_cards(self):
        query = self.filter_var.get().strip().lower()
        for card in self.card_frames:
            t = card.tool_data
            text_haystack = f"{t['title']} {t['script']} {t['what_it_does']} {t['how_it_works']} {t['phase']}".lower()
            if not query or query in text_haystack:
                card.pack(fill=tk.X, pady=4)
            else:
                card.pack_forget()

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def clear_log(self):
        self.log_text.delete("1.0", tk.END)

    def copy_log(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.log_text.get("1.0", tk.END))
        messagebox.showinfo("Copied", "Log content copied to clipboard!")

    def launch_tool(self, tool):
        script_path = BASE_DIR / tool["script"]
        if not script_path.exists():
            messagebox.showerror("Error", f"Script not found:\n{script_path}")
            return

        self.log(f"---> Launching: {tool['title']} ({tool['script']})...")

        # Launch in background thread/process
        def runner():
            try:
                cmd = [sys.executable, str(script_path)] + tool["args"]
                # On Windows, start as detached GUI if supported
                subprocess.Popen(cmd, cwd=str(BASE_DIR))
                self.log(f"[✓] {tool['title']} launched successfully.")
            except Exception as e:
                self.log(f"[!] Failed to launch {tool['title']}: {e}")

        threading.Thread(target=runner, daemon=True).start()

    def run_auto_sync_all(self):
        if not messagebox.askyesno("Confirm Auto-Sync", "Scan all companion question bank pairs (.json and .csv) and automatically synchronize older files from newer counterparts?"):
            return

        self.log("\n---> Starting Workspace Auto-Sync across all subjects...")
        def worker():
            try:
                from file_syncer import scan_workspace_pairs, sync_pair
                pairs = scan_workspace_pairs()
                count = 0
                for p in pairs:
                    if p['newer'] == 'json' and p['diff_sec'] > 2:
                        self.log(f"  • Syncing JSON -> CSV: {p['folder']}/{p['stem']}")
                        sync_pair(p['json_path'], p['csv_path'])
                        count += 1
                    elif p['newer'] == 'csv' and p['diff_sec'] > 2:
                        self.log(f"  • Syncing CSV -> JSON: {p['folder']}/{p['stem']}")
                        sync_pair(p['csv_path'], p['json_path'])
                        count += 1

                if count == 0:
                    self.log("[✓] All question banks are already 100% synchronized and up to date!")
                    messagebox.showinfo("Sync Complete", "All companion files are already synchronized and up to date!")
                else:
                    self.log(f"[✓] Successfully synchronized {count} file pair(s)!")
                    messagebox.showinfo("Sync Complete", f"Successfully synchronized {count} companion file pair(s)!")
            except Exception as e:
                self.log(f"[!] Auto-sync error: {e}")
                messagebox.showerror("Sync Error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def run_regenerate_all_pdf(self):
        if not messagebox.askyesno("Confirm HTML/PDF Generation", "Regenerate both Topics and Sessions study HTML files for all subjects in the workspace?"):
            return

        self.log("\n---> Regenerating dual HTML/PDF views for all subjects...")
        def worker():
            try:
                gen_script = BASE_DIR / "pdf_maker" / "generator.py"
                proc = subprocess.Popen(
                    [sys.executable, str(gen_script), "--all"],
                    cwd=str(BASE_DIR),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )
                for line in proc.stdout:
                    line_s = line.strip()
                    if line_s:
                        self.log(f"  {line_s}")
                proc.wait()
                self.log("[✓] Finished regenerating all PDF/HTML study files!")
                messagebox.showinfo("Complete", "Successfully regenerated all PDF/HTML study banks!")
            except Exception as e:
                self.log(f"[!] PDF generation error: {e}")
                messagebox.showerror("Error", str(e))

        threading.Thread(target=worker, daemon=True).start()

    def open_output_folder(self):
        out_p = BASE_DIR / "pdf_maker" / "output"
        out_p.mkdir(parents=True, exist_ok=True)
        os.startfile(str(out_p))

    def open_workspace_folder(self):
        os.startfile(str(BASE_DIR))


def main():
    root = tk.Tk()
    app = TealMedMasterCenter(root)
    root.mainloop()


if __name__ == "__main__":
    main()
