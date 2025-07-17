import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np
import json
import os
import shutil
from pathlib import Path
from datetime import datetime
import re

class OpenFASTTestCaseGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenFAST Test Case Generator")
        self.root.geometry("900x700")
        
        # Style configuration
        style = ttk.Style()
        style.theme_use('clam')
        
        # Main container with padding
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Variables
        self.base_fst_path = tk.StringVar()
        self.output_dir = tk.StringVar(value="test_cases")
        self.num_cases = tk.IntVar(value=5)
        self.parameter_entries = []
        self.available_parameters = self.get_available_parameters()
        
        # GUI sections
        self.create_file_selection_section(main_frame)
        self.create_test_config_section(main_frame)
        self.create_parameter_section(main_frame)
        self.create_action_section(main_frame)
        self.create_log_section(main_frame)
        
    def get_available_parameters(self):
        """Define available parameters that can be modified"""
        return {
            'ElastoDyn': {
                'TipRad': {'description': 'Blade tip radius (m)', 'type': 'float', 'default_min': 50, 'default_max': 80},
                'HubRad': {'description': 'Hub radius (m)', 'type': 'float', 'default_min': 1, 'default_max': 3},
                'TowerHt': {'description': 'Tower height (m)', 'type': 'float', 'default_min': 70, 'default_max': 100},
                'ShftTilt': {'description': 'Shaft tilt angle (deg)', 'type': 'float', 'default_min': 0, 'default_max': 10},
                'PreCone(1)': {'description': 'Blade precone angle (deg)', 'type': 'float', 'default_min': -5, 'default_max': 0},
                'OverHang': {'description': 'Rotor overhang (m)', 'type': 'float', 'default_min': -10, 'default_max': 0},
            },
            'InflowWind': {
                'WindType': {'description': 'Wind type', 'type': 'int', 'default_min': 1, 'default_max': 4},
                'RefHt': {'description': 'Reference height (m)', 'type': 'float', 'default_min': 50, 'default_max': 150},
                'URef': {'description': 'Reference wind speed (m/s)', 'type': 'float', 'default_min': 5, 'default_max': 25},
            },
            'HydroDyn': {
                'WtrDens': {'description': 'Water density (kg/m³)', 'type': 'float', 'default_min': 1020, 'default_max': 1030},
                'WtrDpth': {'description': 'Water depth (m)', 'type': 'float', 'default_min': 50, 'default_max': 500},
                'MSL2SWL': {'description': 'MSL to SWL offset (m)', 'type': 'float', 'default_min': -1, 'default_max': 1},
            },
            'ServoDyn': {
                'PCMode': {'description': 'Pitch control mode', 'type': 'int', 'default_min': 0, 'default_max': 5},
                'VS_RtGnSp': {'description': 'Rated generator speed (rpm)', 'type': 'float', 'default_min': 1000, 'default_max': 1500},
                'VS_RtTq': {'description': 'Rated generator torque (Nm)', 'type': 'float', 'default_min': 40000, 'default_max': 50000},
            },
            'Main FST': {
                'TMax': {'description': 'Simulation time (s)', 'type': 'float', 'default_min': 100, 'default_max': 1000},
                'DT': {'description': 'Time step (s)', 'type': 'float', 'default_min': 0.001, 'default_max': 0.01},
            }
        }
        
    def create_file_selection_section(self, parent):
        """Create file selection section"""
        frame = ttk.LabelFrame(parent, text="File Selection", padding="10")
        frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(frame, text="Base FST File:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Entry(frame, textvariable=self.base_fst_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Browse", command=self.browse_fst_file).grid(row=0, column=2, padx=5)
        
        ttk.Label(frame, text="Output Directory:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(frame, textvariable=self.output_dir, width=50).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(frame, text="Browse", command=self.browse_output_dir).grid(row=1, column=2, padx=5, pady=5)
        
    def create_test_config_section(self, parent):
        """Create test configuration section"""
        frame = ttk.LabelFrame(parent, text="Test Configuration", padding="10")
        frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(frame, text="Number of Test Cases:").grid(row=0, column=0, sticky=tk.W, padx=5)
        spinbox = ttk.Spinbox(frame, from_=2, to=100, textvariable=self.num_cases, width=10)
        spinbox.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(frame, text="Distribution Type:").grid(row=0, column=2, sticky=tk.W, padx=20)
        self.distribution_var = tk.StringVar(value="uniform")
        dist_combo = ttk.Combobox(frame, textvariable=self.distribution_var, 
                                  values=["uniform", "normal", "logarithmic"], width=15)
        dist_combo.grid(row=0, column=3, sticky=tk.W, padx=5)
        
    def create_parameter_section(self, parent):
        """Create parameter configuration section"""
        frame = ttk.LabelFrame(parent, text="Parameter Configuration", padding="10")
        frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        parent.rowconfigure(2, weight=1)
        
        # Create scrollable frame
        canvas = tk.Canvas(frame, height=300)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add parameter button
        ttk.Button(frame, text="Add Parameter", command=self.add_parameter).grid(row=0, column=0, sticky=tk.W, pady=5)
        
        # Parameter list frame
        self.param_list_frame = scrollable_frame
        
        canvas.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)
        
        # Add a default parameter
        self.add_parameter()
        
    def create_action_section(self, parent):
        """Create action buttons section"""
        frame = ttk.Frame(parent)
        frame.grid(row=3, column=0, columnspan=2, pady=10)
        
        ttk.Button(frame, text="Generate Test Cases", command=self.generate_test_cases,
                  style="Accent.TButton").grid(row=0, column=0, padx=5)
        ttk.Button(frame, text="Load Configuration", command=self.load_config).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Save Configuration", command=self.save_config).grid(row=0, column=2, padx=5)
        ttk.Button(frame, text="Clear All", command=self.clear_all).grid(row=0, column=3, padx=5)
        
    def create_log_section(self, parent):
        """Create log output section"""
        frame = ttk.LabelFrame(parent, text="Output Log", padding="10")
        frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        parent.rowconfigure(4, weight=1)
        
        self.log_text = tk.Text(frame, height=8, width=80)
        log_scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        
    def add_parameter(self):
        """Add a new parameter configuration row"""
        row_frame = ttk.Frame(self.param_list_frame)
        row_frame.grid(sticky=(tk.W, tk.E), pady=2)
        
        # Parameter selection
        param_var = tk.StringVar()
        param_combo = ttk.Combobox(row_frame, textvariable=param_var, width=30)
        
        # Build parameter list with categories
        param_list = []
        for category, params in self.available_parameters.items():
            for param_name, param_info in params.items():
                param_list.append(f"{category} - {param_name}")
        
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
        
        # Update min/max when parameter is selected
        def on_param_select(event):
            selection = param_var.get()
            if ' - ' in selection:
                category, param = selection.split(' - ')
                param_info = self.available_parameters[category][param]
                min_var.set(param_info['default_min'])
                max_var.set(param_info['default_max'])
        
        param_combo.bind('<<ComboboxSelected>>', on_param_select)
        
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
        # Find and remove from parameter_entries
        self.parameter_entries = [entry for entry in self.parameter_entries 
                                 if entry['frame'] != frame]
        frame.destroy()
        
    def browse_fst_file(self):
        """Browse for FST file"""
        filename = filedialog.askopenfilename(
            title="Select FST file",
            filetypes=[("FST files", "*.fst"), ("All files", "*.*")]
        )
        if filename:
            self.base_fst_path.set(filename)
            self.log("Selected FST file: " + filename)
            
    def browse_output_dir(self):
        """Browse for output directory"""
        dirname = filedialog.askdirectory(title="Select Output Directory")
        if dirname:
            self.output_dir.set(dirname)
            self.log("Selected output directory: " + dirname)
            
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.root.update()
        
    def generate_test_cases(self):
        """Generate test cases based on configuration"""
        # Validate inputs
        if not self.base_fst_path.get():
            messagebox.showerror("Error", "Please select a base FST file")
            return
            
        if not os.path.exists(self.base_fst_path.get()):
            messagebox.showerror("Error", "Base FST file does not exist")
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
            
            # Parse base files
            base_fst_path = Path(self.base_fst_path.get())
            base_dir = base_fst_path.parent
            
            # Read main FST file to get associated files
            fst_files = self.parse_fst_file(base_fst_path)
            
            # Generate parameter values
            num_cases = self.num_cases.get()
            parameter_values = self.generate_parameter_values(num_cases)
            
            # Create test cases
            test_summary = []
            
            for i in range(num_cases):
                case_name = f"case_{i+1:03d}"
                case_dir = output_path / case_name
                case_dir.mkdir(exist_ok=True)
                
                self.log(f"Creating test case {i+1}/{num_cases}: {case_name}")
                
                # Copy all files to case directory
                self.copy_base_files(base_dir, case_dir, fst_files)
                
                # Modify parameters for this case
                case_params = {}
                for j, param_entry in enumerate(self.parameter_entries):
                    param_str = param_entry['param_var'].get()
                    if ' - ' in param_str:
                        category, param_name = param_str.split(' - ')
                        value = parameter_values[j][i]
                        case_params[f"{category}/{param_name}"] = value
                        
                        # Apply parameter modification
                        self.modify_parameter(case_dir, category, param_name, value, fst_files)
                
                # Save case summary
                case_info = {
                    'case_name': case_name,
                    'parameters': case_params,
                    'base_file': base_fst_path.name
                }
                test_summary.append(case_info)
            
            # Save overall summary
            summary_file = output_path / "test_cases_summary.json"
            with open(summary_file, 'w') as f:
                json.dump({
                    'generation_date': datetime.now().isoformat(),
                    'base_fst_file': str(base_fst_path),
                    'num_cases': num_cases,
                    'distribution': self.distribution_var.get(),
                    'test_cases': test_summary
                }, f, indent=4)
            
            self.log(f"Successfully generated {num_cases} test cases")
            self.log(f"Summary saved to: {summary_file}")
            
            messagebox.showinfo("Success", f"Generated {num_cases} test cases in {output_path}")
            
        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", f"Failed to generate test cases: {str(e)}")
            
    def parse_fst_file(self, fst_path):
        """Parse FST file to get associated files"""
        files = {'fst': fst_path.name}
        
        with open(fst_path, 'r') as f:
            for line in f:
                if 'EDFile' in line and '"' in line:
                    files['ElastoDyn'] = line.split('"')[1]
                elif 'InflowFile' in line and '"' in line:
                    files['InflowWind'] = line.split('"')[1]
                elif 'ServoFile' in line and '"' in line:
                    files['ServoDyn'] = line.split('"')[1]
                elif 'HydroFile' in line and '"' in line:
                    files['HydroDyn'] = line.split('"')[1]
                    
        return files
        
    def copy_base_files(self, source_dir, dest_dir, fst_files):
        """Copy all base files to test case directory"""
        # Copy main FST file
        shutil.copy2(source_dir / fst_files['fst'], dest_dir / fst_files['fst'])
        
        # Copy associated files
        for file_type, filename in fst_files.items():
            if file_type != 'fst' and filename:
                source_file = source_dir / filename
                if source_file.exists():
                    shutil.copy2(source_file, dest_dir / filename)
                    
        # Copy any additional files in the directory (e.g., blade files, tower files)
        for file in source_dir.glob("*"):
            if file.is_file() and file.name not in [f for f in fst_files.values()]:
                dest_file = dest_dir / file.name
                if not dest_file.exists():
                    shutil.copy2(file, dest_file)
                    
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
                std = (max_val - min_val) / 6  # 99.7% within range
                values = np.random.normal(mean, std, num_cases)
                values = np.clip(values, min_val, max_val)
            elif self.distribution_var.get() == "logarithmic":
                if min_val <= 0:
                    values = np.linspace(min_val, max_val, num_cases)
                else:
                    values = np.logspace(np.log10(min_val), np.log10(max_val), num_cases)
                    
            parameter_values.append(values)
            
        return parameter_values
        
    def modify_parameter(self, case_dir, category, param_name, value, fst_files):
        """Modify a specific parameter in the appropriate file"""
        if category == "Main FST":
            file_path = case_dir / fst_files['fst']
        elif category in fst_files:
            file_path = case_dir / fst_files[category]
        else:
            self.log(f"Warning: Category {category} not found in files")
            return
            
        if not file_path.exists():
            self.log(f"Warning: File {file_path} not found")
            return
            
        # Read file
        with open(file_path, 'r') as f:
            lines = f.readlines()
            
        # Modify parameter
        modified = False
        for i, line in enumerate(lines):
            if param_name in line and not line.strip().startswith('!'):
                # Extract the comment part if exists
                comment_start = line.find('!')
                if comment_start > 0:
                    comment = line[comment_start:]
                else:
                    comment = ''
                    
                # Format the new value
                param_info = self.available_parameters[category][param_name]
                if param_info['type'] == 'int':
                    new_value = str(int(value))
                else:
                    new_value = f"{value:.6f}"
                    
                # Reconstruct the line
                lines[i] = f"{new_value:<20} {comment if comment else '! ' + param_name}\n"
                modified = True
                break
                
        if modified:
            # Write modified file
            with open(file_path, 'w') as f:
                f.writelines(lines)
        else:
            self.log(f"Warning: Parameter {param_name} not found in {file_path.name}")
            
    def save_config(self):
        """Save current configuration to file"""
        config = {
            'base_fst_path': self.base_fst_path.get(),
            'output_dir': self.output_dir.get(),
            'num_cases': self.num_cases.get(),
            'distribution': self.distribution_var.get(),
            'parameters': []
        }
        
        for param_entry in self.parameter_entries:
            config['parameters'].append({
                'parameter': param_entry['param_var'].get(),
                'min': param_entry['min_var'].get(),
                'max': param_entry['max_var'].get()
            })
            
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
                    self.add_parameter()
                    entry = self.parameter_entries[-1]
                    entry['param_var'].set(param_config['parameter'])
                    entry['min_var'].set(param_config['min'])
                    entry['max_var'].set(param_config['max'])
                    
                self.log(f"Configuration loaded from: {filename}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load configuration: {str(e)}")
                
    def clear_parameters(self):
        """Clear all parameter entries"""
        for entry in self.parameter_entries:
            entry['frame'].destroy()
        self.parameter_entries = []
        
    def clear_all(self):
        """Clear all inputs"""
        self.base_fst_path.set('')
        self.output_dir.set('test_cases')
        self.num_cases.set(5)
        self.distribution_var.set('uniform')
        self.clear_parameters()
        self.log_text.delete(1.0, tk.END)
        self.log("All inputs cleared")


def main():
    root = tk.Tk()
    app = OpenFASTTestCaseGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()