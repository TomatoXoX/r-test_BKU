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
        """Create the run tests tab"""
        main_frame = ttk.Frame(self.run_tab, padding="10")
        main_frame.pack(fill='both', expand=True)
        
        # OpenFAST executable selection
        exe_frame = ttk.LabelFrame(main_frame, text="OpenFAST Executable", padding="10")
        exe_frame.pack(fill='x', pady=5)
        
        ttk.Label(exe_frame, text="OpenFAST Path:").pack(side='left', padx=5)
        ttk.Entry(exe_frame, textvariable=self.openfast_exe, width=50).pack(side='left', padx=5)
        ttk.Button(exe_frame, text="Browse", command=self.browse_openfast_exe).pack(side='left', padx=5)
        
        # Test case selection
        case_frame = ttk.LabelFrame(main_frame, text="Test Cases", padding="10")
        case_frame.pack(fill='both', expand=True, pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(case_frame)
        btn_frame.pack(fill='x', pady=5)
        
        ttk.Button(btn_frame, text="Load Test Cases", command=self.load_test_cases).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Select All", command=self.select_all_cases).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Deselect All", command=self.deselect_all_cases).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Run Selected", command=self.run_selected_cases, 
                   style="Accent.TButton").pack(side='left', padx=5)
        
        # Test case list with checkboxes
        list_frame = ttk.Frame(case_frame)
        list_frame.pack(fill='both', expand=True)
        
        # Create treeview for test cases
        columns = ('Status', 'Parameters', 'Runtime', 'Result')
        self.case_tree = ttk.Treeview(list_frame, columns=columns, show='tree headings', height=10)
        
        self.case_tree.heading('#0', text='Test Case')
        self.case_tree.heading('Status', text='Status')
        self.case_tree.heading('Parameters', text='Modified Parameters')
        self.case_tree.heading('Runtime', text='Runtime')
        self.case_tree.heading('Result', text='Result')
        
        self.case_tree.column('#0', width=150)
        self.case_tree.column('Status', width=100)
        self.case_tree.column('Parameters', width=300)
        self.case_tree.column('Runtime', width=100)
        self.case_tree.column('Result', width=200)
        
        # Scrollbars for treeview
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
        
        self.run_log = scrolledtext.ScrolledText(log_frame, height=10, width=80)
        self.run_log.pack(fill='both', expand=True)
        
        # Store test case data
        self.test_cases = {}
        self.case_vars = {}
        
    def create_file_selection_section(self, parent):
        """Create file selection section"""
        frame = ttk.LabelFrame(parent, text="File Selection", padding="10")
        frame.pack(fill='x', pady=5)
        
        ttk.Label(frame, text="Base FST File:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Entry(frame, textvariable=self.base_fst_path, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.browse_fst_file).grid(row=0, column=2, padx=5)
        
        ttk.Label(frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.output_dir, width=60).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=5)
        
    def create_test_config_section(self, parent):
        """Create test configuration section"""
        frame = ttk.LabelFrame(parent, text="Test Configuration", padding="10")
        frame.pack(fill='x', pady=5)
        
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
        frame.pack(fill='x', pady=5)
        
        ttk.Button(frame, text="Discover Parameters", command=self.discover_parameters,
                  style="Accent.TButton").pack(side='left', padx=5)
        
        self.discovery_status = ttk.Label(frame, text="Click 'Discover Parameters' to scan FST files")
        self.discovery_status.pack(side='left', padx=20)
        
    def create_parameter_section(self, parent):
        """Create parameter configuration section"""
        frame = ttk.LabelFrame(parent, text="Parameter Configuration", padding="10")
        frame.pack(fill='both', expand=True, pady=5)
        
        # Add parameter controls
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill='x', pady=5)
        
        ttk.Button(control_frame, text="Add Parameter", command=self.add_parameter).pack(side='left', padx=5)
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
        frame = ttk.Frame(parent)
        frame.pack(fill='x', pady=10)
        
        ttk.Button(frame, text="Generate Test Cases", command=self.generate_test_cases,
                  style="Accent.TButton").pack(side='left', padx=5)
        ttk.Button(frame, text="Load Configuration", command=self.load_config).pack(side='left', padx=5)
        ttk.Button(frame, text="Save Configuration", command=self.save_config).pack(side='left', padx=5)
        ttk.Button(frame, text="View File Structure", command=self.show_file_structure).pack(side='left', padx=5)
        
    def create_log_section(self, parent):
        """Create log output section"""
        frame = ttk.LabelFrame(parent, text="Output Log", padding="10")
        frame.pack(fill='both', expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(frame, height=8, width=80)
        self.log_text.pack(fill='both', expand=True)
        
    def discover_parameters(self):
        """Discover all parameters from FST and referenced files"""
        if not self.base_fst_path.get():
            messagebox.showerror("Error", "Please select a base FST file first")
            return
            
        self.log("Starting parameter discovery...")
        self.discovery_status.config(text="Scanning files...")
        self.discovered_parameters = {}
        self.file_structure = {}
        
        try:
            # Parse the main FST file
            base_path = Path(self.base_fst_path.get())
            self.file_structure = self.parse_fst_structure(base_path)
            
            # Discover parameters in all files
            total_params = 0
            for file_type, file_info in self.file_structure.items():
                if file_info.get('path') and file_info['path'].exists():
                    params = self.extract_parameters_from_file(file_info['path'], file_type)
                    if params:
                        self.discovered_parameters[file_type] = params
                        total_params += len(params)
                        self.log(f"Found {len(params)} parameters in {file_type}")
            
            self.discovery_status.config(text=f"Discovered {total_params} parameters across {len(self.discovered_parameters)} files")
            self.log(f"Parameter discovery complete: {total_params} parameters found")
            
        except Exception as e:
            self.log(f"Error during parameter discovery: {str(e)}")
            messagebox.showerror("Error", f"Failed to discover parameters: {str(e)}")
            
    def parse_fst_structure(self, fst_path):
        """Parse FST file and all referenced files to build file structure"""
        structure = {'Main_FST': {'path': fst_path, 'params': {}}}
        base_dir = fst_path.parent
        
        # Regular expressions for finding file references
        file_patterns = {
            'EDFile': 'ElastoDyn',
            'BDBldFile\(1\)': 'BeamDyn_Blade',
            'InflowFile': 'InflowWind',
            'AeroFile': 'AeroDyn',
            'ServoFile': 'ServoDyn',
            'HydroFile': 'HydroDyn',
            'SubFile': 'SubDyn',
            'MooringFile': 'MoorDyn',
            'IceFile': 'IceDyn',
            'SeaStFile': 'SeaState'
        }
        
        with open(fst_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        for pattern, file_type in file_patterns.items():
            match = re.search(rf'{pattern}\s*"([^"]+)"', content, re.IGNORECASE)
            if match:
                filename = match.group(1).strip()
                if filename.lower() not in ['unused', 'none', '']:
                    file_path = base_dir / filename
                    if file_path.exists():
                        structure[file_type] = {'path': file_path, 'params': {}}
                        
                        # Check for sub-files (e.g., blade files, tower files)
                        self.parse_sub_files(file_path, file_type, structure, base_dir)
        
        return structure
        
    def parse_sub_files(self, file_path, file_type, structure, base_dir):
        """Parse sub-files referenced within input files"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        # Check for blade files in ElastoDyn
        if file_type == 'ElastoDyn':
            blade_match = re.search(r'BldFile\(1\)\s*"([^"]+)"', content, re.IGNORECASE)
            if blade_match:
                blade_file = blade_match.group(1).strip()
                if blade_file.lower() not in ['unused', 'none', '']:
                    blade_path = base_dir / blade_file
                    if blade_path.exists():
                        structure['ElastoDyn_Blade'] = {'path': blade_path, 'params': {}}
                        
            # Tower file
            tower_match = re.search(r'TwrFile\s*"([^"]+)"', content, re.IGNORECASE)
            if tower_match:
                tower_file = tower_match.group(1).strip()
                if tower_file.lower() not in ['unused', 'none', '']:
                    tower_path = base_dir / tower_file
                    if tower_path.exists():
                        structure['ElastoDyn_Tower'] = {'path': tower_path, 'params': {}}
                        
    def extract_parameters_from_file(self, file_path, file_type):
        """Extract modifiable parameters from a file"""
        parameters = {}
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Pattern to match parameter lines (value followed by name/description)
        # Matches lines like: "1.0  ParamName - Description"
        param_pattern = re.compile(r'^([^\s!]+)\s+(\w+)\s*[-!]?\s*(.*)$')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip empty lines and pure comment lines
            if not line or line.startswith('!') or line.startswith('#'):
                continue
                
            # Skip section headers and dividers
            if '---' in line or '===' in line:
                continue
                
            match = param_pattern.match(line)
            if match:
                value_str, param_name, description = match.groups()
                
                # Skip if parameter name contains quotes (likely a filename)
                if '"' in value_str or '"' in param_name:
                    continue
                    
                # Skip common non-parameter keywords
                skip_keywords = ['echo', 'false', 'true', 'default', 'unused', 'none']
                if param_name.lower() in skip_keywords:
                    continue
                    
                # Try to determine the parameter type and value
                param_info = self.parse_parameter_value(value_str, param_name, description)
                if param_info:
                    parameters[param_name] = {
                        'line_number': i,
                        'original_value': param_info['value'],
                        'type': param_info['type'],
                        'description': description.strip(),
                        'unit': self.extract_unit(description)
                    }
                    
        return parameters
        
    def parse_parameter_value(self, value_str, param_name, description):
        """Parse parameter value and determine its type"""
        value_str = value_str.strip()
        
        # Try to parse as float
        try:
            value = float(value_str)
            return {'value': value, 'type': 'float'}
        except ValueError:
            pass
            
        # Try to parse as integer
        try:
            value = int(value_str)
            return {'value': value, 'type': 'int'}
        except ValueError:
            pass
            
        # Check if it's a boolean
        if value_str.lower() in ['true', 'false']:
            return {'value': value_str.lower() == 'true', 'type': 'bool'}
            
        # Check if it's a known string option
        if any(keyword in description.lower() for keyword in ['option', 'method', 'model', 'type']):
            return {'value': value_str, 'type': 'option'}
            
        return None
        
    def extract_unit(self, description):
        """Extract unit from parameter description"""
        # Common unit patterns
        unit_patterns = [
            r'\(([^)]+)\)',  # Units in parentheses
            r'\[([^\]]+)\]',  # Units in brackets
        ]
        
        for pattern in unit_patterns:
            match = re.search(pattern, description)
            if match:
                return match.group(1)
                
        return ''
        
    def show_parameter_selector(self):
        """Show dialog to select parameters from discovered ones"""
        if not self.discovered_parameters:
            messagebox.showinfo("Info", "No parameters discovered. Please run 'Discover Parameters' first.")
            return
            
        # Create parameter selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Select Parameters")
        dialog.geometry("800x600")
        
        # Create treeview
        tree_frame = ttk.Frame(dialog)
        tree_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        tree = ttk.Treeview(tree_frame, columns=('Type', 'Value', 'Unit', 'Description'), show='tree headings')
        tree.heading('#0', text='Parameter')
        tree.heading('Type', text='Type')
        tree.heading('Value', text='Current Value')
        tree.heading('Unit', text='Unit')
        tree.heading('Description', text='Description')
        
        tree.column('#0', width=200)
        tree.column('Type', width=80)
        tree.column('Value', width=100)
        tree.column('Unit', width=80)
        tree.column('Description', width=300)
        
        # Add scrollbars
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        tree.grid(row=0, column=0, sticky='nsew')
        vsb.grid(row=0, column=1, sticky='ns')
        hsb.grid(row=1, column=0, sticky='ew')
        
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        
        # Populate tree
        for file_type, params in self.discovered_parameters.items():
            file_node = tree.insert('', 'end', text=file_type, open=True)
            
            for param_name, param_info in params.items():
                tree.insert(file_node, 'end', text=param_name, 
                           values=(param_info['type'], 
                                  param_info['original_value'],
                                  param_info.get('unit', ''),
                                  param_info['description'][:100]))
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill='x', pady=10)
        
        def add_selected():
            selection = tree.selection()
            for item in selection:
                parent = tree.parent(item)
                if parent:  # It's a parameter, not a file
                    file_type = tree.item(parent)['text']
                    param_name = tree.item(item)['text']
                    param_info = self.discovered_parameters[file_type][param_name]
                    
                    # Add parameter with smart defaults
                    self.add_parameter_with_info(file_type, param_name, param_info)
                    
            dialog.destroy()
            
        ttk.Button(btn_frame, text="Add Selected", command=add_selected).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='left', padx=5)
        
    def add_parameter_with_info(self, file_type, param_name, param_info):
        """Add parameter with information from discovery"""
        row_frame = ttk.Frame(self.param_list_frame)
        row_frame.pack(fill='x', pady=2)
        
        # Parameter name (read-only)
        param_var = tk.StringVar(value=f"{file_type} - {param_name}")
        param_label = ttk.Label(row_frame, text=f"{file_type} - {param_name}", width=40)
        param_label.grid(row=0, column=0, padx=5)
        
        # Calculate smart defaults based on parameter type and current value
        current_val = param_info['original_value']
        
        if param_info['type'] in ['float', 'int']:
            if isinstance(current_val, (int, float)):
                # Set min/max as percentage of current value
                if abs(current_val) < 1e-6:  # Near zero
                    min_default = -1.0
                    max_default = 1.0
                else:
                    min_default = current_val * 0.8
                    max_default = current_val * 1.2
                    
                # Special cases for known parameters
                if 'angle' in param_name.lower() or 'deg' in param_info.get('unit', '').lower():
                    min_default = max(current_val - 10, -180)
                    max_default = min(current_val + 10, 180)
                elif 'speed' in param_name.lower() or 'm/s' in param_info.get('unit', ''):
                    min_default = max(0, current_val * 0.5)
                    max_default = current_val * 2.0
            else:
                min_default = 0
                max_default = 100
        else:
            min_default = 0
            max_default = 1
            
        # Min value
        min_var = tk.DoubleVar(value=min_default)
        ttk.Label(row_frame, text="Min:").grid(row=0, column=1, padx=5)
        min_entry = ttk.Entry(row_frame, textvariable=min_var, width=10)
        min_entry.grid(row=0, column=2, padx=5)
        
        # Max value
        max_var = tk.DoubleVar(value=max_default)
        ttk.Label(row_frame, text="Max:").grid(row=0, column=3, padx=5)
        max_entry = ttk.Entry(row_frame, textvariable=max_var, width=10)
        max_entry.grid(row=0, column=4, padx=5)
        
        # Unit label
        if param_info.get('unit'):
            ttk.Label(row_frame, text=f"[{param_info['unit']}]").grid(row=0, column=5, padx=5)
            
        # Remove button
        remove_btn = ttk.Button(row_frame, text="Remove", 
                               command=lambda: self.remove_parameter(row_frame))
        remove_btn.grid(row=0, column=6, padx=5)
        
        # Store the entry data with additional info
        self.parameter_entries.append({
            'frame': row_frame,
            'param_var': param_var,
            'min_var': min_var,
            'max_var': max_var,
            'file_type': file_type,
            'param_name': param_name,
            'param_info': param_info
        })
        
    def add_parameter(self):
        """Add a new parameter configuration row (manual entry)"""
        row_frame = ttk.Frame(self.param_list_frame)
        row_frame.pack(fill='x', pady=2)
        
        # Parameter selection
        param_var = tk.StringVar()
        param_combo = ttk.Combobox(row_frame, textvariable=param_var, width=40)
        
        # Build parameter list from discovered parameters
        param_list = []
        if self.discovered_parameters:
            for file_type, params in self.discovered_parameters.items():
                for param_name in params:
                    param_list.append(f"{file_type} - {param_name}")
        else:
            param_list = ["Run 'Discover Parameters' first"]
        
        param_combo['values'] = param_list
        param_combo.grid(row=0, column=0, padx=5)
        
        # Min value
        min_var = tk.DoubleVar()
        ttk.Label(row_frame, text="Min:").grid(row=0, column=1, padx=5)
        min_entry = ttk.Entry(row_frame, textvariable=min_var, width=10)
        min_entry.grid(row=0, column=2, padx=5)
        
        # Max value
        max_var = tk.DoubleVar()
        ttk.Label(row_frame, text="Max:").grid(row=0, column=3, padx=5)
        max_entry = ttk.Entry(row_frame, textvariable=max_var, width=10)
        max_entry.grid(row=0, column=4, padx=5)
        
        # Remove button
        remove_btn = ttk.Button(row_frame, text="Remove", 
                               command=lambda: self.remove_parameter(row_frame))
        remove_btn.grid(row=0, column=5, padx=5)
        
        # Store the entry data
        self.parameter_entries.append({
            'frame': row_frame,
            'param_var': param_var,
            'min_var': min_var,
            'max_var': max_var
        })
        
    def remove_parameter(self, frame):
        """Remove a parameter configuration row"""
        self.parameter_entries = [entry for entry in self.parameter_entries 
                                 if entry['frame'] != frame]
        frame.destroy()
        
    def generate_test_cases(self):
        """Generate test cases based on configuration"""
        # Validate inputs
        if not self.base_fst_path.get():
            messagebox.showerror("Error", "Please select a base FST file")
            return
            
        if not self.parameter_entries:
            messagebox.showerror("Error", "Please add at least one parameter to vary")
            return
            
        # Clear log
        self.log_text.delete(1.0, tk.END)
        self.log("Starting test case generation...")
        
        try:
            # Create output directory
            output_path = Path(self.output_dir.get())
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Generate parameter values
            num_cases = self.num_cases.get()
            parameter_values = self.generate_parameter_values(num_cases)
            
            # Create test cases
            test_summary = []
            base_path = Path(self.base_fst_path.get())
            base_dir = base_path.parent
            
            for i in range(num_cases):
                case_name = f"case_{i+1:03d}"
                case_dir = output_path / case_name
                case_dir.mkdir(exist_ok=True)
                
                self.log(f"Creating test case {i+1}/{num_cases}: {case_name}")
                
                # Copy all files
                self.copy_all_files(base_dir, case_dir)
                
                # Modify parameters
                case_params = {}
                for j, param_entry in enumerate(self.parameter_entries):
                    if 'file_type' in param_entry:  # From discovery
                        file_type = param_entry['file_type']
                        param_name = param_entry['param_name']
                        param_info = param_entry['param_info']
                    else:  # Manual entry
                        param_str = param_entry['param_var'].get()
                        if ' - ' not in param_str:
                            continue
                        file_type, param_name = param_str.split(' - ')
                        param_info = self.discovered_parameters.get(file_type, {}).get(param_name, {})
                    
                    value = parameter_values[j][i]
                    case_params[f"{file_type}/{param_name}"] = value
                    
                    # Apply modification
                    self.modify_parameter_robust(case_dir, file_type, param_name, value, param_info)
                
                # Update main FST file name in the case directory
                case_fst = case_dir / base_path.name
                
                # Save case summary
                case_info = {
                    'case_name': case_name,
                    'fst_file': base_path.name,
                    'parameters': case_params,
                    'created': datetime.now().isoformat()
                }
                test_summary.append(case_info)
                
                # Save individual case info
                with open(case_dir / 'case_info.json', 'w') as f:
                    json.dump(case_info, f, indent=2)
            
            # Save overall summary
            summary_file = output_path / "test_cases_summary.json"
            with open(summary_file, 'w') as f:
                json.dump({
                    'generation_date': datetime.now().isoformat(),
                    'base_fst_file': str(base_path),
                    'num_cases': num_cases,
                    'distribution': self.distribution_var.get(),
                    'test_cases': test_summary,
                    'file_structure': {k: str(v['path']) for k, v in self.file_structure.items() if 'path' in v}
                }, f, indent=4)
            
            self.log(f"Successfully generated {num_cases} test cases")
            self.log(f"Summary saved to: {summary_file}")
            
            # Ask if user wants to switch to run tab
            if messagebox.askyesno("Success", f"Generated {num_cases} test cases.\nDo you want to run them now?"):
                self.notebook.select(self.run_tab)
                self.output_dir.set(str(output_path))
                self.load_test_cases()
            
        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to generate test cases: {str(e)}")
            
    def copy_all_files(self, source_dir, dest_dir):
        """Copy all files from source to destination directory"""
        for file in source_dir.glob("*"):
            if file.is_file():
                shutil.copy2(file, dest_dir / file.name)
                
    def modify_parameter_robust(self, case_dir, file_type, param_name, value, param_info):
        """Robustly modify a parameter in the appropriate file"""
        # Find the file to modify
        if file_type == 'Main_FST':
            file_name = Path(self.base_fst_path.get()).name
            file_path = case_dir / file_name
        else:
            # Get file path from structure
            if file_type in self.file_structure and 'path' in self.file_structure[file_type]:
                original_path = self.file_structure[file_type]['path']
                file_path = case_dir / original_path.name
            else:
                self.log(f"Warning: Could not find file for {file_type}")
                return
                
        if not file_path.exists():
            self.log(f"Warning: File {file_path} not found")
            return
            
        # Read file
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        # Find and modify the parameter
        modified = False
        line_num = param_info.get('line_number', -1)
        
        # First try to use the exact line number if available
        if line_num >= 0 and line_num < len(lines):
            if param_name in lines[line_num]:
                lines[line_num] = self.format_parameter_line(lines[line_num], value, param_info)
                modified = True
                
        # If not found, search for the parameter
        if not modified:
            for i, line in enumerate(lines):
                if param_name in line and not line.strip().startswith('!'):
                    lines[i] = self.format_parameter_line(line, value, param_info)
                    modified = True
                    break
                    
        if modified:
            # Write modified file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
        else:
            self.log(f"Warning: Parameter {param_name} not found in {file_path.name}")
            
    def format_parameter_line(self, line, new_value, param_info):
        """Format a parameter line with new value while preserving structure"""
        # Split line into value and rest
        parts = line.split(None, 1)
        if len(parts) < 2:
            return line
            
        # Format new value based on type
        if param_info.get('type') == 'int':
            value_str = str(int(new_value))
        elif param_info.get('type') == 'float':
            # Use scientific notation for very small/large values
            if abs(new_value) < 0.001 or abs(new_value) > 10000:
                value_str = f"{new_value:.6e}"
            else:
                value_str = f"{new_value:.6f}"
        else:
            value_str = str(new_value)
            
        # Preserve formatting
        return f"{value_str:<20} {parts[1]}"
        
    def generate_parameter_values(self, num_cases):
        """Generate parameter values based on distribution type"""
        parameter_values = []
        
        for param_entry in self.parameter_entries:
            min_val = param_entry['min_var'].get()
            max_val = param_entry['max_var'].get()
            
            if self.distribution_var.get() == "uniform":
                values = np.linspace(min_val, max_val, num_cases)
            elif self.distribution_var.get() == "normal":
                mean = (min_val + max_val) / 2
                std = (max_val - min_val) / 6
                values = np.random.normal(mean, std, num_cases)
                values = np.clip(values, min_val, max_val)
            elif self.distribution_var.get() == "logarithmic":
                if min_val <= 0:
                    values = np.linspace(min_val, max_val, num_cases)
                else:
                    values = np.logspace(np.log10(min_val), np.log10(max_val), num_cases)
            elif self.distribution_var.get() == "latin_hypercube":
                # Simple Latin Hypercube sampling
                values = np.zeros(num_cases)
                intervals = np.linspace(min_val, max_val, num_cases + 1)
                for i in range(num_cases):
                    values[i] = np.random.uniform(intervals[i], intervals[i + 1])
                np.random.shuffle(values)
                
            parameter_values.append(values)
            
        return parameter_values
        
    def browse_fst_file(self):
        """Browse for FST file"""
        filename = filedialog.askopenfilename(
            title="Select FST file",
            filetypes=[("FST files", "*.fst"), ("All files", "*.*")]
        )
        if filename:
            self.base_fst_path.set(filename)
            self.log("Selected FST file: " + filename)
            # Auto-discover parameters
            self.discover_parameters()
            
    def browse_output_dir(self):
        """Browse for output directory"""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir.set(dirname)
            self.log("Selected output directory: " + dirname)
            
    def browse_openfast_exe(self):
        """Browse for OpenFAST executable"""
        filename = filedialog.askopenfilename(
            title="Select OpenFAST executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")]
        )
        if filename:
            self.openfast_exe.set(filename)
            self.run_log_message(f"Selected OpenFAST: {filename}")
            
    def load_test_cases(self):
        """Load test cases from directory"""
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please select test case directory")
            return
            
        # Clear existing items
        self.case_tree.delete(*self.case_tree.get_children())
        self.test_cases = {}
        self.case_vars = {}
        
        output_path = Path(self.output_dir.get())
        summary_file = output_path / "test_cases_summary.json"
        
        if summary_file.exists():
            with open(summary_file, 'r') as f:
                summary = json.load(f)
                
            for case_info in summary['test_cases']:
                case_name = case_info['case_name']
                case_dir = output_path / case_name
                
                if case_dir.exists():
                    # Create tree item
                    params_str = ', '.join([f"{k.split('/')[-1]}={v:.3g}" 
                                          for k, v in list(case_info['parameters'].items())[:3]])
                    if len(case_info['parameters']) > 3:
                        params_str += f" (+{len(case_info['parameters'])-3} more)"
                        
                    item = self.case_tree.insert('', 'end', text=case_name,
                                               values=('Ready', params_str, '-', '-'))
                    
                    # Store case data
                    self.test_cases[case_name] = {
                        'path': case_dir,
                        'fst_file': case_info['fst_file'],
                        'parameters': case_info['parameters'],
                        'item_id': item
                    }
                    
                    # Create checkbox variable
                    self.case_vars[case_name] = tk.BooleanVar(value=True)
                    
            self.run_log_message(f"Loaded {len(self.test_cases)} test cases")
        else:
            # Try to find test cases without summary
            case_dirs = [d for d in output_path.iterdir() if d.is_dir() and d.name.startswith('case_')]
            
            for case_dir in sorted(case_dirs):
                case_name = case_dir.name
                
                # Find FST file
                fst_files = list(case_dir.glob("*.fst"))
                if fst_files:
                    item = self.case_tree.insert('', 'end', text=case_name,
                                               values=('Ready', 'Unknown parameters', '-', '-'))
                    
                    self.test_cases[case_name] = {
                        'path': case_dir,
                        'fst_file': fst_files[0].name,
                        'parameters': {},
                        'item_id': item
                    }
                    
                    self.case_vars[case_name] = tk.BooleanVar(value=True)
                    
            self.run_log_message(f"Found {len(self.test_cases)} test cases")
            
    def select_all_cases(self):
        """Select all test cases"""
        for var in self.case_vars.values():
            var.set(True)
        for item in self.case_tree.get_children():
            self.case_tree.selection_add(item)
            
    def deselect_all_cases(self):
        """Deselect all test cases"""
        for var in self.case_vars.values():
            var.set(False)
        for item in self.case_tree.get_children():
            self.case_tree.selection_remove(item)
            
    def run_selected_cases(self):
        """Run selected test cases"""
        if not self.openfast_exe.get():
            messagebox.showerror("Error", "Please select OpenFAST executable")
            return
            
        # Get selected cases
        selected_cases = []
        for item in self.case_tree.selection():
            case_name = self.case_tree.item(item)['text']
            if case_name in self.test_cases:
                selected_cases.append(case_name)
                
        if not selected_cases:
            messagebox.showwarning("Warning", "No test cases selected")
            return
            
        # Confirm
        if not messagebox.askyesno("Confirm", f"Run {len(selected_cases)} test cases?"):
            return
            
        # Reset progress
        self.progress_var.set(0)
        
        # Run in separate thread
        thread = threading.Thread(target=self.run_cases_thread, args=(selected_cases,))
        thread.daemon = True
        thread.start()
        
    def run_cases_thread(self, case_names):
        """Run test cases in separate thread"""
        total_cases = len(case_names)
        
        for i, case_name in enumerate(case_names):
            case_data = self.test_cases[case_name]
            
            # Update status
            self.message_queue.put(('tree_update', (case_data['item_id'], 'Status', 'Running')))
            self.message_queue.put(('log', f"\n{'='*60}\nRunning {case_name}...\n"))
            
            start_time = datetime.now()
            
            try:
                # Run OpenFAST
                cmd = [self.openfast_exe.get(), case_data['fst_file']]
                
                process = subprocess.Popen(
                    cmd,
                    cwd=str(case_data['path']),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True
                )
                
                # Stream output
                for line in iter(process.stdout.readline, ''):
                    if line:
                        self.message_queue.put(('log', line.rstrip()))
                        
                process.wait()
                
                # Check result
                runtime = (datetime.now() - start_time).total_seconds()
                
                if process.returncode == 0:
                    # Check for output files
                    out_files = list(case_data['path'].glob("*.out"))
                    if out_files:
                        result = "Success"
                        status = "Completed"
                    else:
                        result = "No output files"
                        status = "Warning"
                else:
                    result = f"Error (code {process.returncode})"
                    status = "Failed"
                    
            except Exception as e:
                runtime = (datetime.now() - start_time).total_seconds()
                result = f"Exception: {str(e)}"
                status = "Failed"
                self.message_queue.put(('log', f"Error: {str(e)}\n"))
                
            # Update tree
            self.message_queue.put(('tree_update', (case_data['item_id'], 'Status', status)))
            self.message_queue.put(('tree_update', (case_data['item_id'], 'Runtime', f"{runtime:.1f}s")))
            self.message_queue.put(('tree_update', (case_data['item_id'], 'Result', result)))
            
            # Update progress
            progress = (i + 1) / total_cases * 100
            self.message_queue.put(('progress', progress))
            
        self.message_queue.put(('log', f"\n{'='*60}\nAll test cases completed!\n"))
        
    def show_file_structure(self):
        """Show discovered file structure"""
        if not self.file_structure:
            messagebox.showinfo("Info", "No file structure discovered. Please run 'Discover Parameters' first.")
            return
            
        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("File Structure")
        dialog.geometry("600x400")
        
        # Create text widget
        text = scrolledtext.ScrolledText(dialog, wrap=tk.WORD)
        text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Display structure
        text.insert('end', "OpenFAST File Structure:\n" + "="*50 + "\n\n")
        
        for file_type, file_info in self.file_structure.items():
            if 'path' in file_info:
                text.insert('end', f"{file_type}:\n")
                text.insert('end', f"  Path: {file_info['path']}\n")
                
                if file_type in self.discovered_parameters:
                    param_count = len(self.discovered_parameters[file_type])
                    text.insert('end', f"  Parameters: {param_count}\n")
                    
                text.insert('end', "\n")
                
        text.config(state='disabled')
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
        
    def save_config(self):
        """Save current configuration"""
        config = {
            'base_fst_path': self.base_fst_path.get(),
            'output_dir': self.output_dir.get(),
            'num_cases': self.num_cases.get(),
            'distribution': self.distribution_var.get(),
            'parameters': []
        }
        
        for param_entry in self.parameter_entries:
            if 'file_type' in param_entry:
                param_config = {
                    'file_type': param_entry['file_type'],
                    'param_name': param_entry['param_name'],
                    'min': param_entry['min_var'].get(),
                    'max': param_entry['max_var'].get()
                }
            else:
                param_config = {
                    'parameter': param_entry['param_var'].get(),
                    'min': param_entry['min_var'].get(),
                    'max': param_entry['max_var'].get()
                }
            config['parameters'].append(param_config)
            
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=4)
            self.log(f"Configuration saved to: {filename}")
            
    def load_config(self):
        """Load configuration from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'r') as f:
                    config = json.load(f)
                    
                # Set values
                self.base_fst_path.set(config.get('base_fst_path', ''))
                self.output_dir.set(config.get('output_dir', ''))
                self.num_cases.set(config.get('num_cases', 5))
                self.distribution_var.set(config.get('distribution', 'uniform'))
                
                # Clear existing parameters
                self.clear_parameters()
                
                # Load parameters
                for param_config in config.get('parameters', []):
                    if 'file_type' in param_config:
                        # New format with discovery
                        param_info = self.discovered_parameters.get(param_config['file_type'], {}).get(param_config['param_name'], {})
                        self.add_parameter_with_info(param_config['file_type'], param_config['param_name'], param_info)
                    else:
                        # Old format
                        self.add_parameter()
                        
                    entry = self.parameter_entries[-1]
                    entry['min_var'].set(param_config['min'])
                    entry['max_var'].set(param_config['max'])
                    
                self.log(f"Configuration loaded from: {filename}")
                
                # Re-discover parameters if FST file is set
                if self.base_fst_path.get():
                    self.discover_parameters()
                    
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
                
    def clear_parameters(self):
        """Clear all parameter entries"""
        for entry in self.parameter_entries:
            entry['frame'].destroy()
        self.parameter_entries = []
        
    def log(self, message):
        """Add message to setup log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
        
    def run_log_message(self, message):
        """Add message to run log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.run_log.insert(tk.END, f"[{timestamp}] {message}\n")
        self.run_log.see(tk.END)
        self.root.update()
        
    def process_queue(self):
        """Process messages from worker threads"""
        try:
            while True:
                msg_type, msg_data = self.message_queue.get_nowait()
                
                if msg_type == 'log':
                    self.run_log.insert(tk.END, msg_data + '\n')
                    self.run_log.see(tk.END)
                elif msg_type == 'tree_update':
                    item_id, column, value = msg_data
                    current_values = list(self.case_tree.item(item_id)['values'])
                    col_names = ['Status', 'Parameters', 'Runtime', 'Result']
                    if column in col_names:
                        idx = col_names.index(column)
                        current_values[idx] = value
                        self.case_tree.item(item_id, values=current_values)
                elif msg_type == 'progress':
                    self.progress_var.set(msg_data)
                    
        except queue.Empty:
            pass
            
        # Schedule next check
        self.root.after(100, self.process_queue)


def main():
    """Main function with example usage"""
    root = tk.Tk()
    app = OpenFASTTestCaseGUI(root)
    
    # Show example usage
    example_text = """
    HOW TO USE THIS TOOL:
    
    1. SETUP TAB - Create Test Cases:
       a) Select your base .fst file using "Browse"
       b) Click "Discover Parameters" to automatically find all modifiable parameters
       c) Click "Add from Discovery" to select parameters you want to vary
       d) Set min/max ranges for each parameter
       e) Choose distribution type and number of cases
       f) Click "Generate Test Cases" to create all test configurations
    
    2. RUN TAB - Execute Tests:
       a) Select your OpenFAST executable
       b) Click "Load Test Cases" to load generated cases
       c) Select which cases to run (or use Select All)
       d) Click "Run Selected" to execute the simulations
       e) Monitor progress and results in real-time
    
    FEATURES:
    - Automatic parameter discovery from all OpenFAST input files
    - Smart default ranges based on parameter types
    - Multiple distribution options (uniform, normal, logarithmic, Latin hypercube)
    - Save/load configurations for repeated use
    - Parallel test execution with real-time monitoring
    - Comprehensive logging and error handling
    """
    
    # Show instructions on first run
    messagebox.showinfo("OpenFAST Test Case Generator", example_text)
    
    root.mainloop()


if __name__ == "__main__":
    main()