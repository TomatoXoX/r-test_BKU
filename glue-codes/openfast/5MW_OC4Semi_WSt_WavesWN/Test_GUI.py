import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import numpy as np
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
import re
import subprocess
import threading
import queue

class OpenFASTTestCaseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenFAST Test Case Generator")
        self.root.geometry("1200x800")
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Accent.TButton", foreground="white", background="#0078D7")
        
        # Main container with notebook for tabs
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Create tabs
        self.setup_tab = ttk.Frame(self.notebook)
        self.run_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.setup_tab, text="Setup Test Cases")
        self.notebook.add(self.run_tab, text="Run Tests")
        
        # Variables
        self.base_fst_path = tk.StringVar()
        self.output_dir = tk.StringVar(value="test_cases")
        self.num_cases = tk.IntVar(value=5)
        self.parameter_entries = []
        self.discovered_parameters = {}
        self.file_structure = {}
        self.openfast_exe = tk.StringVar()
        # For multi-threading in the run tab
        self.num_threads = tk.IntVar(value=max(1, os.cpu_count() // 2))
        self.run_button = None
        self.job_queue = queue.Queue()
        self.progress_lock = threading.Lock()
        self.completed_cases = 0
        self.total_cases_to_run = 0

        # Queue for thread communication
        self.message_queue = queue.Queue()
        
        # Create GUI sections
        self.create_setup_tab()
        self.create_run_tab()
        
        # Start queue processor
        self.process_queue()
        
    def create_setup_tab(self):
        """Create the setup tab"""
        # Main frame with scrollbar
        canvas = tk.Canvas(self.setup_tab)
        scrollbar = ttk.Scrollbar(self.setup_tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Add all sections to scrollable frame
        self.create_file_selection_section(scrollable_frame)
        self.create_test_config_section(scrollable_frame)
        self.create_parameter_discovery_section(scrollable_frame)
        self.create_parameter_section(scrollable_frame)
        self.create_action_section(scrollable_frame)
        self.create_log_section(scrollable_frame)
        
    def create_run_tab(self):
        """Create the run tests tab with multi-threading options"""
        main_frame = ttk.Frame(self.run_tab, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # Configuration frame for executable and threading
        config_frame = ttk.LabelFrame(main_frame, text="Run Configuration", padding="10")
        config_frame.pack(fill='x', pady=5)
        
        ttk.Label(config_frame, text="OpenFAST Path:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        ttk.Entry(config_frame, textvariable=self.openfast_exe, width=50).grid(row=0, column=1, sticky='ew', padx=5, pady=2)
        ttk.Button(config_frame, text="Browse", command=self.browse_openfast_exe).grid(row=0, column=2, padx=5, pady=2)
        
        ttk.Label(config_frame, text="Number of parallel runs:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        ttk.Spinbox(config_frame, from_=1, to=os.cpu_count() or 8, textvariable=self.num_threads, width=8).grid(row=1, column=1, sticky='w', padx=5, pady=2)
        
        config_frame.columnconfigure(1, weight=1)

        # Test case selection
        case_frame = ttk.LabelFrame(main_frame, text="Test Cases", padding="10")
        case_frame.pack(fill='both', expand=True, pady=5)
        
        # Buttons for controlling the list and running tests
        btn_frame = ttk.Frame(case_frame)
        btn_frame.pack(fill='x', pady=5)
        
        ttk.Button(btn_frame, text="Load Test Cases", command=self.load_test_cases).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_cases).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Deselect All", command=self.deselect_all_cases).pack(side='left', padx=5)
        self.run_button = ttk.Button(btn_frame, text="Run Selected", command=self.run_selected_cases, style="Accent.TButton")
        self.run_button.pack(side='left', padx=20)
        
        # Test case list
        list_frame = ttk.Frame(case_frame)
        list_frame.pack(fill='both', expand=True)
        
        columns = ('Status', 'Parameters', 'Runtime', 'Result')
        self.case_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10, selectmode='extended')
        
        self.case_tree.heading('Status', text='Status')
        self.case_tree.heading('Parameters', text='Modified Parameters')
        self.case_tree.heading('Runtime', text='Runtime')
        self.case_tree.heading('Result', text='Result')
        
        # Use column #0 for the test case name
        self.case_tree.column('#0', width=150, anchor='w')
        self.case_tree.heading('#0', text='Test Case')

        self.case_tree.column('Status', width=100, anchor='w')
        self.case_tree.column('Parameters', width=300, anchor='w')
        self.case_tree.column('Runtime', width=100, anchor='center')
        self.case_tree.column('Result', width=200, anchor='w')
        
        tree_scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.case_tree.yview)
        tree_scroll_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.case_tree.xview)
        self.case_tree.configure(yscrollcommand=tree_scroll_y.set, xscrollcommand=tree_scroll_x.set)
        
        self.case_tree.grid(row=0, column=0, sticky='nsew')
        tree_scroll_y.grid(row=0, column=1, sticky='ns')
        tree_scroll_x.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(main_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', pady=5)
        
        # Run log
        log_frame = ttk.LabelFrame(main_frame, text="Execution Log", padding="10")
        log_frame.pack(fill='both', expand=True, pady=5)
        
        self.run_log = scrolledtext.ScrolledText(log_frame, height=10, width=80, wrap=tk.WORD)
        self.run_log.pack(fill='both', expand=True)
        
        self.test_cases = {}
        
    def create_file_selection_section(self, parent):
        """Create file selection section"""
        frame = ttk.LabelFrame(parent, text="File Selection", padding="10")
        frame.pack(fill='x', pady=5, padx=5)
        
        ttk.Label(frame, text="Base FST File:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Entry(frame, textvariable=self.base_fst_path, width=60).grid(row=0, column=1, padx=5, sticky=tk.EW)
        ttk.Button(frame, text="Browse", command=self.browse_fst_file).grid(row=0, column=2, padx=5)
        
        ttk.Label(frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.output_dir, width=60).grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        ttk.Button(frame, text="Browse", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=5)
        
        frame.columnconfigure(1, weight=1)
        
    def create_test_config_section(self, parent):
        """Create test configuration section"""
        frame = ttk.LabelFrame(parent, text="Test Configuration", padding="10")
        frame.pack(fill='x', pady=5, padx=5)
        
        ttk.Label(frame, text="Number of Test Cases:").grid(row=0, column=0, sticky=tk.W, padx=5)
        spinbox = ttk.Spinbox(frame, from_=2, to=100, textvariable=self.num_cases, width=10)
        spinbox.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(frame, text="Distribution Type:").grid(row=0, column=2, sticky=tk.W, padx=20)
        self.distribution_var = tk.StringVar(value="uniform")
        dist_combo = ttk.Combobox(frame, textvariable=self.distribution_var, 
                                  values=["uniform", "normal", "logarithmic", "latin_hypercube"], width=15)
        dist_combo.grid(row=0, column=3, sticky=tk.W, padx=5)
        
    def create_parameter_discovery_section(self, parent):
        """Create parameter discovery section"""
        frame = ttk.LabelFrame(parent, text="Parameter Discovery", padding="10")
        frame.pack(fill='x', pady=5, padx=5)
        
        ttk.Button(frame, text="Discover Parameters", command=self.discover_parameters,
                  style="Accent.TButton").pack(side='left', padx=5)
        
        self.discovery_status = ttk.Label(frame, text="Select a .fst file and click 'Discover Parameters'")
        self.discovery_status.pack(side='left', padx=20)
        
    def create_parameter_section(self, parent):
        """Create parameter configuration section"""
        frame = ttk.LabelFrame(parent, text="Parameter Configuration", padding="10")
        frame.pack(fill='both', expand=True, pady=5, padx=5)
        
        # Add parameter controls
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill='x', pady=5)
        
        ttk.Button(control_frame, text="Add from Discovery", command=self.show_parameter_selector).pack(side='left', padx=5)
        ttk.Button(control_frame, text="Clear All", command=self.clear_parameters).pack(side='left', padx=5)
        
        # Create scrollable frame for parameters
        canvas = tk.Canvas(frame, height=200)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        self.param_list_frame = ttk.Frame(canvas)
        
        self.param_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.param_list_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def create_action_section(self, parent):
        """Create action buttons section"""
        frame = ttk.Frame(parent, padding="5")
        frame.pack(fill='x', pady=10)
        
        ttk.Button(frame, text="Generate Test Cases", command=self.generate_test_cases,
                  style="Accent.TButton").pack(side='left', padx=5)
        ttk.Button(frame, text="Load Configuration", command=self.load_config).pack(side='left', padx=5)
        ttk.Button(frame, text="Save Configuration", command=self.save_config).pack(side='left', padx=5)
        ttk.Button(frame, text="View File Structure", command=self.show_file_structure).pack(side='left', padx=5)
        
    def create_log_section(self, parent):
        """Create log output section"""
        frame = ttk.LabelFrame(parent, text="Output Log", padding="10")
        frame.pack(fill='both', expand=True, pady=5, padx=5)
        
        self.log_text = scrolledtext.ScrolledText(frame, height=8, width=80, wrap=tk.WORD)
        self.log_text.pack(fill='both', expand=True)
        
    def resolve_file_path(self, base_dir, filename):
        """
        Resolve file path by checking multiple possible locations.
        Handles both absolute and relative paths, including those with '../'.
        """
        if not filename or filename.lower() in ['unused', 'none', '']:
            return None
            
        filename = filename.strip('"').strip("'")
        
        # 1. Try path relative to the directory of the file that references it.
        #    This is the most common case and pathlib handles '..' correctly.
        path1 = base_dir / Path(filename)
        if path1.exists():
            return path1
            
        # 2. Try as an absolute path.
        path2 = Path(filename)
        if path2.is_absolute() and path2.exists():
            return path2

        # 3. Fallback: Try just the filename in the same directory (for cases where path info is wrong).
        path3 = base_dir / Path(filename).name
        if path3.exists():
            return path3

        # 4. Fallback: Try path relative to the *original* FST file's directory.
        #    This helps if all paths are specified relative to the root of the case.
        root_fst_dir = Path(self.base_fst_path.get()).parent
        if base_dir != root_fst_dir:
            path4 = root_fst_dir / Path(filename)
            if path4.exists():
                return path4

        self.log(f"Warning: Could not find file: {filename}")
        return None

    def _find_referenced_files(self, file_path, base_dir):
        """
        Finds all file references within a given OpenFAST input file.
        This is a helper function for the main discovery process.
        """
        found_files = {}
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            self.log(f"Could not read file {file_path}: {e}")
            return {}

        # This generalized regex finds lines like: "SomeFile.dat"  Keyword  - Optional description
        # It captures the filename and the associated keyword.
        # It looks for common OpenFAST file extensions to avoid matching random quoted strings.
        pattern = re.compile(
            r'^\s*["\']([^"\']+\.(?:dat|txt|csv|af|ipt|bld|twr|in))["\']\s+([a-zA-Z_][a-zA-Z0-9_\(\)]*)\s*',
            re.MULTILINE | re.IGNORECASE
        )
        
        for match in pattern.finditer(content):
            filename = match.group(1).strip()
            keyword = match.group(2).strip()

            if keyword.lower() in ['true', 'false', 'default', 'none', 'unused', 'echo']:
                continue
            
            resolved_path = self.resolve_file_path(base_dir, filename)
            if resolved_path:
                found_files[keyword] = resolved_path
        
        # Special case for AeroDyn airfoil files, which are just a list of quoted strings
        # without a keyword on the same line. We use NumAFfiles to be more robust.
        num_af_match = re.search(r'^\s*(\d+)\s+NumAFfiles', content, re.MULTILINE | re.IGNORECASE)
        if num_af_match:
            num_af_files = int(num_af_match.group(1))
            # Regex to find N lines that start with a quoted string after the NumAFfiles line.
            af_block_pattern = re.compile(r'^\s*["\']([^"\']+)["\']', re.MULTILINE)
            start_pos = num_af_match.end()
            af_matches = af_block_pattern.finditer(content, pos=start_pos)
            
            for i, match in enumerate(af_matches):
                if i >= num_af_files:
                    break
                filename = match.group(1).strip()
                resolved_path = self.resolve_file_path(base_dir, filename)
                if resolved_path:
                    # Create a unique key for each airfoil file
                    found_files[f'AirfoilFile_{i+1}'] = resolved_path

        return found_files

    def discover_parameters(self):
        """
        Discover all parameters from the main FST and all referenced files iteratively.
        This method systematically scans each found file for more file references until all
        files in the model are discovered.
        """
        if not self.base_fst_path.get():
            messagebox.showerror("Error", "Please select a base FST file first")
            return

        self.log("Starting parameter discovery...")
        self.discovery_status.config(text="Scanning files...")
        self.root.update()

        # Reset discovered data
        self.discovered_parameters = {}
        self.file_structure = {}
        
        try:
            initial_fst_path = Path(self.base_fst_path.get())
            base_dir = initial_fst_path.parent

            # Use a list as a queue for files to scan and a set to track processed files
            files_to_scan = [('Main_FST', initial_fst_path)]
            processed_paths = set()
            
            while files_to_scan:
                file_key, file_path = files_to_scan.pop(0)

                if not file_path or file_path in processed_paths:
                    continue
                
                if not file_path.exists():
                    self.log(f"Skipping non-existent file: {file_path}")
                    continue

                self.log(f"Processing {file_key}: {file_path.name}")
                processed_paths.add(file_path)
                self.file_structure[file_key] = {'path': file_path, 'params': {}}

                # Find all sub-files referenced in the current file
                newly_found_files = self._find_referenced_files(file_path, file_path.parent)
                
                for new_key, new_path in newly_found_files.items():
                    if new_path not in processed_paths:
                        # Ensure the key for the new file is unique
                        unique_key = new_key
                        if unique_key in self.file_structure:
                            i = 2
                            while f"{new_key}_{i}" in self.file_structure:
                                i += 1
                            unique_key = f"{new_key}_{i}"
                        
                        files_to_scan.append((unique_key, new_path))

            # After discovering the complete file structure, extract parameters from each file
            total_params = 0
            for file_key, file_info in self.file_structure.items():
                path = file_info.get('path')
                if path and path.exists():
                    params = self.extract_parameters_from_file(path, file_key)
                    if params:
                        self.discovered_parameters[file_key] = params
                        total_params += len(params)
            
            self.discovery_status.config(text=f"Discovered {total_params} parameters across {len(self.file_structure)} files.")
            self.log(f"Parameter discovery complete: {total_params} parameters found in {len(self.file_structure)} files.")

        except Exception as e:
            self.log(f"Error during parameter discovery: {str(e)}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Error", f"Failed to discover parameters: {str(e)}")
                        
    def extract_parameters_from_file(self, file_path, file_type):
        """Extract modifiable parameters from a file"""
        parameters = {}
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Flexible pattern to match parameter lines (VALUE  NAME  DESCRIPTION)
        param_pattern = re.compile(r'^\s*([^\s!#"]+)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[-!]')
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            if not line_stripped or line_stripped.startswith(('!', '#', '-', '=')):
                continue
                
            match = param_pattern.match(line_stripped)
            if match:
                value_str, param_name = match.groups()
                
                # Filter out common non-parameter keywords and file references
                if param_name.lower() in ['true', 'false', 'default', 'unused', 'none', 'end', 'echo']:
                    continue
                if any(ext in value_str for ext in ['.dat', '.txt', '.csv']):
                    continue
                    
                # Try to parse the value to determine its type
                param_info = self.parse_parameter_value(value_str, param_name, line)
                if param_info:
                    parameters[param_name] = {
                        'line_number': i,
                        'original_value': param_info['value'],
                        'type': param_info['type'],
                        'description': line.split('!', 1)[-1].split('-', 1)[-1].strip(),
                        'unit': self.extract_unit(line)
                    }
                        
        return parameters
        
    def parse_parameter_value(self, value_str, param_name, description):
        """Parse parameter value and determine its type"""
        value_str = value_str.strip()
        
        if value_str.upper() in ['DEFAULT', '"DEFAULT"']:
            return None
            
        # Try to parse as float or int
        try:
            value = float(value_str)
            if value == int(value) and '.' not in value_str and 'e' not in value_str.lower():
                return {'value': int(value), 'type': 'int'}
            else:
                return {'value': value, 'type': 'float'}
        except ValueError:
            pass
            
        # Check for boolean
        if value_str.lower() in ['true', 'false']:
            return {'value': value_str.lower() == 'true', 'type': 'bool'}
            
        # Check if it's a known string option by looking for keywords in the description
        if any(keyword in description.lower() for keyword in ['option', 'method', 'model', 'type', 'switch', 'code']):
            return {'value': value_str, 'type': 'option'}
            
        return None
        
    def extract_unit(self, description):
        """Extract unit from parameter description"""
        match = re.search(r'\(([^)]+)\)', description)
        if match:
            unit = match.group(1)
            # Filter out non-unit content like "flag", "switch", etc.
            if not any(word in unit.lower() for word in ['flag', 'switch', 'quoted', 'string', 'option']):
                return unit
        return ''
        
    def show_parameter_selector(self):
        """Show dialog to select parameters from discovered ones"""
        if not self.discovered_parameters:
            messagebox.showinfo("Info", "No parameters discovered. Please run 'Discover Parameters' first.")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Parameters to Vary")
        dialog.geometry("900x700")
        
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill='x', padx=10, pady=5)
        
        ttk.Label(search_frame, text="Search:").pack(side='left', padx=5)
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var, width=30)
        search_entry.pack(side='left', padx=5)
        
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(tree_frame, columns=('Type', 'Value', 'Unit', 'Description'), show='tree headings')
        tree.heading('#0', text='Parameter')
        tree.heading('Type', text='Type')
        tree.heading('Value', text='Current Value')
        tree.heading('Unit', text='Unit')
        tree.heading('Description', text='Description')
        
        tree.column('#0', width=200, anchor='w')
        tree.column('Type', width=80, anchor='w')
        tree.column('Value', width=100, anchor='e')
        tree.column('Unit', width=80, anchor='w')
        tree.column('Description', width=350, anchor='w')
        
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        all_items = []
        for file_type, params in sorted(self.discovered_parameters.items()):
            file_node = tree.insert('', 'end', text=file_type, open=False, tags=('file_node',))
            
            for param_name, param_info in sorted(params.items()):
                val = param_info['original_value']
                if isinstance(val, float):
                    val_str = f"{val:.4g}"
                else:
                    val_str = str(val)

                item = tree.insert(file_node, 'end', text=param_name, 
                                  values=(param_info['type'], 
                                         val_str,
                                         param_info.get('unit', ''),
                                         param_info['description'][:100]))
                all_items.append((item, file_type.lower(), param_name.lower(), param_info['description'].lower()))

        tree.tag_configure('file_node', font=('TkDefaultFont', 10, 'bold'))

        def search_params(*args):
            search_term = search_var.get().lower()
            # Un-hide all items before searching
            for child in tree.get_children():
                tree.item(child, open=False)
                tree.reattach(child, '', 'end')

            if not search_term:
                return

            # Hide all items and then show only matching ones
            for child in tree.get_children():
                tree.detach(child)

            for item, file_type, param_name, desc in all_items:
                if search_term in param_name or search_term in desc or search_term in file_type:
                    parent = tree.parent(item)
                    tree.reattach(parent, '', 'end')
                    tree.item(parent, open=True)
                    
        search_var.trace('w', search_params)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', pady=10, padx=10)
        
        def add_selected():
            selection = tree.selection()
            added_count = 0
            for item in selection:
                parent = tree.parent(item)
                if parent:
                    file_type = tree.item(parent)['text']
                    param_name = tree.item(item)['text']
                    param_info = self.discovered_parameters[file_type][param_name]
                    self.add_parameter_with_info(file_type, param_name, param_info)
                    added_count += 1
            dialog.destroy()
            if added_count > 0:
                self.log(f"Added {added_count} parameters for variation.")
                messagebox.showinfo("Success", f"Added {added_count} parameters.")
            
        ttk.Button(btn_frame, text="Add Selected", command=add_selected, style="Accent.TButton").pack(side='right')
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='right', padx=5)
        
    def add_parameter_with_info(self, file_type, param_name, param_info):
        """Add parameter with information from discovery"""
        # Prevent adding the same parameter twice
        for entry in self.parameter_entries:
            if entry['file_type'] == file_type and entry['param_name'] == param_name:
                self.log(f"Parameter {file_type} - {param_name} is already added.")
                return

        row_frame = ttk.Frame(self.param_list_frame)
        row_frame.pack(fill='x', pady=2, padx=2)
        
        param_label_text = f"{file_type} - {param_name}"
        param_label = ttk.Label(row_frame, text=param_label_text, width=40, anchor='w', wraplength=250)
        param_label.grid(row=0, column=0, padx=5, sticky='w')
        
        current_val = param_info['original_value']
        unit = param_info.get('unit', '')
        
        min_default, max_default = 0, 1
        if param_info['type'] in ['float', 'int'] and isinstance(current_val, (int, float)):
            if abs(current_val) > 1e-9:
                min_default = current_val * 0.8
                max_default = current_val * 1.2
            else:
                min_default, max_default = -1.0, 1.0
            
        min_var = tk.DoubleVar(value=min_default)
        ttk.Label(row_frame, text="Min:").grid(row=0, column=1, padx=(10, 2))
        min_entry = ttk.Entry(row_frame, textvariable=min_var, width=10)
        min_entry.grid(row=0, column=2, padx=(0, 5))
        
        max_var = tk.DoubleVar(value=max_default)
        ttk.Label(row_frame, text="Max:").grid(row=0, column=3, padx=5)
        max_entry = ttk.Entry(row_frame, textvariable=max_var, width=10)
        max_entry.grid(row=0, column=4, padx=5)
        
        info_text = f"[{unit}]" if unit else ""
        if isinstance(current_val, float):
            info_text += f" (Current: {current_val:.4g})"
        else:
            info_text += f" (Current: {current_val})"
        ttk.Label(row_frame, text=info_text, foreground='gray').grid(row=0, column=5, padx=5, sticky='w')
            
        remove_btn = ttk.Button(row_frame, text="Remove", command=lambda: self.remove_parameter(row_frame))
        remove_btn.grid(row=0, column=6, padx=10)
        
        row_frame.columnconfigure(5, weight=1)

        self.parameter_entries.append({
            'frame': row_frame, 'min_var': min_var, 'max_var': max_var,
            'file_type': file_type, 'param_name': param_name, 'param_info': param_info
        })
        
    def remove_parameter(self, frame):
        """Remove a parameter configuration row"""
        self.parameter_entries = [entry for entry in self.parameter_entries if entry['frame'] != frame]
        frame.destroy()
        
    def generate_test_cases(self):
        """Generate test cases based on configuration"""
        if not self.base_fst_path.get():
            messagebox.showerror("Error", "Please select a base FST file")
            return
        if not self.parameter_entries:
            messagebox.showerror("Error", "Please add at least one parameter to vary")
            return
            
        self.log_text.delete(1.0, tk.END)
        self.log("Starting test case generation...")
        
        try:
            output_path = Path(self.output_dir.get())
            if output_path.exists() and any(output_path.iterdir()):
                if not messagebox.askyesno("Warning", f"Output directory '{output_path}' is not empty. Overwrite?"):
                    return
            output_path.mkdir(parents=True, exist_ok=True)
            
            num_cases = self.num_cases.get()
            parameter_values = self.generate_parameter_values(num_cases)
            
            test_summary = []
            
            for i in range(num_cases):
                case_name = f"case_{i+1:03d}"
                case_dir = output_path / case_name
                case_dir.mkdir(exist_ok=True)
                
                self.log(f"Creating test case {i+1}/{num_cases}: {case_name}")
                
                # Copy all discovered files to the new case directory
                for file_info in self.file_structure.values():
                    src_path = file_info['path']
                    if src_path.exists():
                        shutil.copy2(src_path, case_dir / src_path.name)
                
                case_params = {}
                for j, param_entry in enumerate(self.parameter_entries):
                    file_type = param_entry['file_type']
                    param_name = param_entry['param_name']
                    param_info = param_entry['param_info']
                    value = parameter_values[j][i]
                    case_params[f"{file_type}/{param_name}"] = value
                    self.modify_parameter_in_file(case_dir, file_type, param_name, value, param_info)
                
                case_info = {
                    'case_name': case_name,
                    'fst_file': Path(self.base_fst_path.get()).name,
                    'parameters': case_params,
                    'created': datetime.now().isoformat()
                }
                test_summary.append(case_info)
                with open(case_dir / 'case_info.json', 'w') as f:
                    json.dump(case_info, f, indent=2)
            
            summary_file = output_path / "test_cases_summary.json"
            with open(summary_file, 'w') as f:
                json.dump({
                    'generation_date': datetime.now().isoformat(),
                    'base_fst_file': self.base_fst_path.get(),
                    'num_cases': num_cases,
                    'distribution': self.distribution_var.get(),
                    'test_cases': test_summary,
                    'file_structure': {k: str(v.get('path')) for k, v in self.file_structure.items()}
                }, f, indent=4)
            
            self.log(f"Successfully generated {num_cases} test cases in '{output_path}'")
            if messagebox.askyesno("Success", f"Generated {num_cases} test cases.\nSwitch to the 'Run Tests' tab now?"):
                self.notebook.select(self.run_tab)
                self.output_dir.set(str(output_path))
                self.load_test_cases()
            
        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to generate test cases: {str(e)}")
            
    def modify_parameter_in_file(self, case_dir, file_type, param_name, value, param_info):
        """Robustly modify a parameter in the appropriate file"""
        original_path = self.file_structure[file_type]['path']
        file_path = case_dir / original_path.name
                
        if not file_path.exists():
            self.log(f"Warning: File {file_path} not found in case directory for parameter {param_name}")
            return
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        modified = False
        line_num = param_info.get('line_number', -1)
        
        # Try to modify by exact line number first for speed and accuracy
        if 0 <= line_num < len(lines) and param_name in lines[line_num]:
            lines[line_num] = self.format_parameter_line(lines[line_num], value, param_info)
            modified = True
                
        # If that fails, search the file for the parameter name
        if not modified:
            for i, line in enumerate(lines):
                # Use regex to ensure we are matching the parameter name as a whole word
                if re.search(r'\s' + re.escape(param_name) + r'\s', ' ' + line):
                    if not line.strip().startswith(('!', '#')):
                        lines[i] = self.format_parameter_line(line, value, param_info)
                        modified = True
                        break
                    
        if modified:
            with open(file_path, 'w', encoding='utf-8', errors='ignore') as f:
                f.writelines(lines)
        else:
            self.log(f"Warning: Parameter '{param_name}' not found or modified in {file_path.name}")
            
    def format_parameter_line(self, line, new_value, param_info):
        """Format a parameter line with a new value while preserving structure"""
        parts = line.split()
        if not parts: return line

        # Format new value based on its type
        param_type = param_info.get('type')
        if param_type == 'int':
            value_str = str(int(new_value))
        elif param_type == 'float':
            if 0.001 < abs(new_value) < 10000:
                value_str = f"{new_value:.7f}".rstrip('0').rstrip('.')
            else:
                value_str = f"{new_value:.6e}"
        else: # bool, option, etc.
            value_str = str(new_value)
            
        # Replace the first element (the old value) with the new formatted value
        parts[0] = value_str
        
        # Reconstruct the line to preserve spacing and comments
        # Find where the old value ended
        old_value_pos = line.find(line.split()[0])
        end_of_value_pos = old_value_pos + len(line.split()[0])
        rest_of_line = line[end_of_value_pos:]

        new_line = line[:old_value_pos] + value_str + rest_of_line
        
        return new_line if new_line.endswith('\n') else new_line + '\n'
        
    def generate_parameter_values(self, num_cases):
        """Generate parameter values based on distribution type"""
        parameter_values = []
        num_params = len(self.parameter_entries)

        try:
            from scipy.stats import qmc
            scipy_available = True
        except ImportError:
            scipy_available = False
            if self.distribution_var.get() == "latin_hypercube":
                self.log("Warning: 'scipy' is not installed. Latin Hypercube sampling is unavailable. Falling back to uniform.")
                self.distribution_var.set("uniform")

        if self.distribution_var.get() == "latin_hypercube" and scipy_available:
            sampler = qmc.LatinHypercube(d=num_params)
            sample = sampler.sample(n=num_cases)
        else:
            sample = np.random.rand(num_cases, num_params) # Fallback for uniform scaling

        for j, param_entry in enumerate(self.parameter_entries):
            min_val = param_entry['min_var'].get()
            max_val = param_entry['max_var'].get()
            dist = self.distribution_var.get()

            if dist == "latin_hypercube" and scipy_available:
                # Scale the uniform (0,1) sample to the specified range
                values = qmc.scale(sample, [min_val]*num_params, [max_val]*num_params)[:, j]
            elif dist == "uniform":
                values = np.linspace(min_val, max_val, num_cases)
            elif dist == "normal":
                mean = (min_val + max_val) / 2
                std_dev = (max_val - mean) / 3 # 99.7% within range
                values = np.random.normal(mean, std_dev, num_cases)
                values = np.clip(values, min_val, max_val)
            elif dist == "logarithmic":
                if min_val <= 0 or max_val <= 0:
                    self.log("Warning: Logarithmic scale requires positive min/max. Falling back to uniform.")
                    values = np.linspace(min_val, max_val, num_cases)
                else:
                    values = np.logspace(np.log10(min_val), np.log10(max_val), num_cases)
            else:
                values = np.linspace(min_val, max_val, num_cases) # Default
                
            parameter_values.append(values)
            
        return np.array(parameter_values)
        
    def browse_fst_file(self):
        filename = filedialog.askopenfilename(
            title="Select base FST file",
            filetypes=[("FST files", "*.fst"), ("All files", "*.*")]
        )
        if filename:
            self.base_fst_path.set(filename)
            self.log("Selected FST file: " + filename)
            if messagebox.askyesno("Discover Parameters", "Do you want to discover parameters for this file now?"):
                self.discover_parameters()
            
    def browse_output_dir(self):
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir.set(dirname)
            self.log("Selected output directory: " + dirname)
            
    def browse_openfast_exe(self):
        filename = filedialog.askopenfilename(
            title="Select OpenFAST executable",
            filetypes=[("Executable", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.openfast_exe.set(filename)
            self.run_log_message(f"Selected OpenFAST executable: {filename}")
            
    def load_test_cases(self):
        """Load test cases from a directory containing a summary JSON."""
        test_dir = self.output_dir.get()
        if not test_dir:
            test_dir = filedialog.askdirectory(title="Select Test Case Directory")
            if not test_dir: return
            self.output_dir.set(test_dir)

        self.case_tree.delete(*self.case_tree.get_children())
        self.test_cases = {}
        
        summary_file = Path(test_dir) / "test_cases_summary.json"
        
        if not summary_file.exists():
            messagebox.showerror("Error", f"Could not find 'test_cases_summary.json' in {test_dir}")
            return
            
        with open(summary_file, 'r') as f:
            summary = json.load(f)
            
        for case_info in summary.get('test_cases', []):
            case_name = case_info['case_name']
            params_str = ', '.join([f"{k.split('/')[-1]}={v:.3g}" for k, v in case_info['parameters'].items()])
            
            item_id = self.case_tree.insert('', 'end', text=case_name,
                                           values=('Ready', params_str, '-', '-'))
            
            self.test_cases[item_id] = {
                'path': Path(test_dir) / case_name,
                'fst_file': case_info['fst_file'],
                'name': case_name
            }
        self.run_log_message(f"Loaded {len(self.test_cases)} test cases from {test_dir}")
        self.select_all_cases()

    def select_all_cases(self):
        """Select all test cases in the tree view."""
        all_items = self.case_tree.get_children()
        self.case_tree.selection_set(all_items)

    def deselect_all_cases(self):
        """Deselect all test cases in the tree view."""
        self.case_tree.selection_set([])

    def run_selected_cases(self):
        """Set up and start the multi-threaded test execution."""
        if not self.openfast_exe.get() or not Path(self.openfast_exe.get()).exists():
            messagebox.showerror("Error", "Please select a valid OpenFAST executable.")
            return
            
        selected_items = self.case_tree.selection()
        if not selected_items:
            messagebox.showwarning("Warning", "No test cases selected to run.")
            return
            
        if not messagebox.askyesno("Confirm", f"This will run {len(selected_items)} OpenFAST simulations. Continue?"):
            return
            
        # Reset progress and clear job queue
        self.progress_var.set(0)
        self.completed_cases = 0
        self.total_cases_to_run = len(selected_items)
        while not self.job_queue.empty():
            self.job_queue.get()

        # Populate the job queue with the selected test cases
        for item_id in selected_items:
            self.job_queue.put(item_id)
        
        # Disable the run button to prevent multiple concurrent runs
        self.run_button.config(state='disabled')
        
        # Start the manager thread that will spawn workers
        manager_thread = threading.Thread(target=self.run_manager_thread, daemon=True)
        manager_thread.start()

    def run_manager_thread(self):
        """Manages worker threads for running simulations."""
        num_workers = self.num_threads.get()
        self.message_queue.put(('log', f"Starting {self.total_cases_to_run} simulations with {num_workers} parallel workers..."))
        
        threads = []
        for _ in range(num_workers):
            t = threading.Thread(target=self.run_worker, daemon=True)
            t.start()
            threads.append(t)
            
        # Wait for the queue to be empty (all jobs processed)
        self.job_queue.join()
        
        # All workers are done
        self.message_queue.put(('log', "\n--- All selected tests completed. ---"))
        self.message_queue.put(('enable_run_button', None))

    def run_worker(self):
        """A worker thread that processes test cases from the job queue."""
        while True:
            try:
                item_id = self.job_queue.get_nowait()
            except queue.Empty:
                return # No more jobs left
            
            case_data = self.test_cases[item_id]
            self.message_queue.put(('tree_update', (item_id, 'Status', 'Running')))
            self.message_queue.put(('log', f"--- Running {case_data['name']} ---"))
            
            start_time = datetime.now()
            try:
                cmd = [self.openfast_exe.get(), case_data['fst_file']]
                process = subprocess.Popen(
                    cmd, cwd=str(case_data['path']),
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding='utf-8', errors='ignore'
                )
                
                # Log output line by line
                for line in iter(process.stdout.readline, ''):
                    self.message_queue.put(('log', f"[{case_data['name']}] {line.strip()}"))
                process.wait()
                
                runtime = (datetime.now() - start_time).total_seconds()
                if process.returncode == 0:
                    result, status = "Success", "Completed"
                else:
                    result, status = f"Error (code {process.returncode})", "Failed"
                    
            except Exception as e:
                runtime = (datetime.now() - start_time).total_seconds()
                result, status = f"Exception: {str(e)}", "Failed"
                self.message_queue.put(('log', f"FATAL ERROR in {case_data['name']}: {str(e)}"))
            
            # Update GUI via the main thread's queue
            self.message_queue.put(('tree_update', (item_id, 'Status', status)))
            self.message_queue.put(('tree_update', (item_id, 'Runtime', f"{runtime:.1f}s")))
            self.message_queue.put(('tree_update', (item_id, 'Result', result)))
            
            # Update overall progress safely
            with self.progress_lock:
                self.completed_cases += 1
                progress = (self.completed_cases / self.total_cases_to_run) * 100
                self.message_queue.put(('progress', progress))
            
            self.job_queue.task_done()

    def show_file_structure(self):
        """Show discovered file structure in a new window."""
        if not self.file_structure:
            messagebox.showinfo("Info", "No file structure discovered. Run 'Discover Parameters' first.")
            return
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Discovered File Structure")
        dialog.geometry("800x600")
        
        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=('Consolas', 10))
        text.pack(fill='both', expand=True, padx=10, pady=10)
        
        text.insert('end', "OpenFAST File Structure:\n" + "="*60 + "\n\n")
        
        for file_type, file_info in sorted(self.file_structure.items()):
            path = file_info.get('path')
            if path:
                text.insert('end', f"{file_type}:\n", 'heading')
                text.insert('end', f"  Path: {path}\n")
                param_count = len(self.discovered_parameters.get(file_type, {}))
                text.insert('end', f"  Parameters Found: {param_count}\n\n")
                
        text.tag_config('heading', font=('Consolas', 11, 'bold'), foreground='darkblue')
        text.config(state='disabled')
        
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
        
    def save_config(self):
        """Save current parameter variation setup to a JSON file."""
        if not self.parameter_entries:
            messagebox.showinfo("Info", "No parameters have been added to save.")
            return

        config = {
            'base_fst_path': self.base_fst_path.get(),
            'output_dir': self.output_dir.get(),
            'num_cases': self.num_cases.get(),
            'distribution': self.distribution_var.get(),
            'parameters': [{
                'file_type': p['file_type'], 'param_name': p['param_name'],
                'min': p['min_var'].get(), 'max': p['max_var'].get()
            } for p in self.parameter_entries]
        }
        
        filename = filedialog.asksaveasfilename(
            title="Save Configuration", defaultextension=".json",
            filetypes=[("JSON config files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=4)
            self.log(f"Configuration saved to: {filename}")
            
    def load_config(self):
        """Load a parameter variation setup from a JSON file."""
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("JSON config files", "*.json"), ("All files", "*.*")]
        )
        if not filename: return
            
        try:
            with open(filename, 'r') as f:
                config = json.load(f)
                
            self.base_fst_path.set(config.get('base_fst_path', ''))
            self.output_dir.set(config.get('output_dir', 'test_cases'))
            self.num_cases.set(config.get('num_cases', 5))
            self.distribution_var.set(config.get('distribution', 'uniform'))
            
            self.clear_parameters()
            
            if self.base_fst_path.get() and not self.discovered_parameters:
                self.log("Base FST found in config, running discovery...")
                self.discover_parameters()

            if not self.discovered_parameters:
                messagebox.showwarning("Warning", "Run parameter discovery on the correct FST file before loading parameters.")
                return

            for param_config in config.get('parameters', []):
                file_type = param_config.get('file_type')
                param_name = param_config.get('param_name')
                
                if file_type and param_name and file_type in self.discovered_parameters and param_name in self.discovered_parameters[file_type]:
                    param_info = self.discovered_parameters[file_type][param_name]
                    self.add_parameter_with_info(file_type, param_name, param_info)
                    entry = self.parameter_entries[-1]
                    entry['min_var'].set(param_config['min'])
                    entry['max_var'].set(param_config['max'])
                else:
                    self.log(f"Warning: Could not find '{param_name}' in '{file_type}' from config. It may be from a different FST file.")
                
            self.log(f"Configuration loaded from: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
            self.log(f"Error loading config: {e}")
                
    def clear_parameters(self):
        """Clear all parameter entries"""
        for entry in self.parameter_entries:
            entry['frame'].destroy()
        self.parameter_entries.clear()
        
    def log(self, message):
        """Add message to setup log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()
        
    def run_log_message(self, message):
        """Add message to run log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.run_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.run_log.see(tk.END)
        
    def process_queue(self):
        """Process messages from worker threads to update the GUI safely."""
        try:
            while True:
                msg_type, msg_data = self.message_queue.get_nowait()
                
                if msg_type == 'log':
                    self.run_log.insert(tk.END, msg_data + '\n')
                    self.run_log.see(tk.END)
                elif msg_type == 'tree_update':
                    item_id, column, value = msg_data
                    if self.case_tree.exists(item_id):
                        self.case_tree.set(item_id, column, value)
                elif msg_type == 'progress':
                    self.progress_bar['value'] = msg_data
                elif msg_type == 'enable_run_button':
                    self.run_button.config(state='normal')

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_queue)

def main():
    """Main function to run the application."""
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except (ImportError, AttributeError):
        pass # For non-Windows OS

    root = tk.Tk()
    app = OpenFASTTestCaseGUI(root)
    
    app.log("Welcome to the OpenFAST Test Case Generator!")
    app.log("=" * 60)
    app.log("1. Use 'Browse' to select your main '.fst' file.")
    app.log("2. Click 'Discover Parameters' to scan all input files.")
    app.log("3. Click 'Add from Discovery' to choose which parameters to vary.")
    app.log("4. Set the min/max range for each chosen parameter.")
    app.log("5. Adjust the number of cases and distribution type.")
    app.log("6. Click 'Generate Test Cases'.")
    app.log("7. Switch to the 'Run Tests' tab to load and execute the simulations.")
    app.log("=" * 60)
    
    root.mainloop()

if __name__ == "__main__":
    main()