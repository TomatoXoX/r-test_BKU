import os
import numpy as np
import matplotlib.pyplot as plt
import subprocess
import shutil
import glob
# --- openfast_toolbox library for I/O and post-processing ---
# Install with: pip install openfast-toolbox
try:
    # Correct imports based on the provided library source code
    from openfast_toolbox.openfast_toolbox.io import FASTInputFile
    from openfast_toolbox.openfast_toolbox.linearization import postproCampbell, plotCampbell
except ImportError as e:
    print("Error: openfast_toolbox not found or installed incorrectly.")
    print("Please install it using: pip install openfast-toolbox")
    raise e

# --- Script Configuration ---

# --- Path to your OpenFAST executable
# --- NOTE: Use an absolute path or ensure it's in your system's PATH
openfast_executable = 'openfast_x64_1.exe' 

# --- Path to the main OpenFAST input file (.fst) for your model
# --- The script will create a temporary directory to run simulations
fast_input_file = r'C:\Users\Admin\Documents\HK243\DACN_DHBK\Code\r-test\glue-codes\openfast\MinimalExample\Main.fst'

# --- Define the range of rotor speeds to analyze (in RPM)
rotor_speeds_rpm = np.linspace(0.1, 12.5, 15) # From 0.1 to 12.5 RPM, 15 steps
# Note: Starting from a very small non-zero RPM to avoid potential issues at 0.

# --- Number of blades (for plotting 1P, 3P, etc.)
num_blades = 3

# --- Temporary directory for running simulations
run_dir = '_temp_lin_runs'

# --- Main Function ---
def generate_campbell_data():
    """
    Runs OpenFAST linearization for a range of rotor speeds, collects the data,
    and generates the Campbell diagram.
    """
    if os.path.exists(run_dir):
        shutil.rmtree(run_dir)
    os.makedirs(run_dir)

    # The new workflow requires a list of the .fst files, one for each operating point.
    fst_files_generated = []

    print('--- Running OpenFAST Linearization for Campbell Diagram ---')
    for i, rpm in enumerate(rotor_speeds_rpm):
        print(f'Running case {i+1}/{len(rotor_speeds_rpm)}: Rotor Speed = {rpm:.2f} RPM')
        
        # Create a specific directory for this run
        case_dir = os.path.join(run_dir, f'case_{i:03d}')
        os.makedirs(case_dir)
        
        # Copy all necessary input files to the case directory
        source_dir = os.path.dirname(fast_input_file)
        if not source_dir:
            source_dir = '.'
            
        for f in os.listdir(source_dir):
            if os.path.isfile(os.path.join(source_dir, f)):
                shutil.copy(os.path.join(source_dir, f), case_dir)

        case_fast_file = os.path.join(case_dir, os.path.basename(fast_input_file))

        # --- Modify OpenFAST input files for this specific case ---
        # 1. Set Linearization to True in the main .fst file
        fst = FASTInputFile(case_fast_file)
        fst['Linearize'] = 'True'
        fst['NLinTimes'] = 1 # Number of linearizations per revolution
        fst['LinTimes'] = 1 # Time to linearize (ensure it's in steady state)
        fst.write()

        # 2. Set the initial rotor speed in the ElastoDyn file
        ed_file_path = os.path.join(case_dir, fst['EDFile'].strip('"'))
        ed = FASTInputFile(ed_file_path)
        ed['RotSpeed'] = rpm
        ed.write()

        # --- Run OpenFAST ---
        try:
            subprocess.run(
                [openfast_executable, os.path.basename(case_fast_file)],
                cwd=case_dir,
                capture_output=True,
                text=True,
                check=True,
                timeout=180
            )
            
            # --- START OF THE FIX: Verify that .lin files were created ---
            rootname = os.path.splitext(os.path.basename(case_fast_file))[0]
            # Search for any file matching the pattern <RootName>.*.lin
            lin_files_found = glob.glob(os.path.join(case_dir, f'{rootname}.*.lin'))
            
            if len(lin_files_found) > 0:
                # Only add the .fst file to the list if outputs were generated
                fst_files_generated.append(case_fast_file)
                print(f"  > Success: Found {len(lin_files_found)} linearization file(s).")
            else:
                # If no .lin files are found, print a warning and skip this case
                print(f"  > WARNING: OpenFAST ran but no .lin files were found for RPM = {rpm:.2f}. The simulation may have become unstable. Skipping this operating point.")
            # --- END OF THE FIX ---

        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            print(f"  > ERROR: An exception occurred while running OpenFAST for RPM = {rpm:.2f}.")
            if isinstance(e, FileNotFoundError):
                print(f"    '{openfast_executable}' not found. Please check the path.")
            elif isinstance(e, subprocess.TimeoutExpired):
                print("    OpenFAST run timed out.")
            else:
                print("    STDOUT:", e.stdout)
                print("    STDERR:", e.stderr)
            continue

    if not fst_files_generated:
        print("\nNo simulations produced valid linearization files. Aborting plot.")
        return

    # --- Post-process using openfast_toolbox ---
    print('\n--- Post-processing linearization files using postproCampbell ---')
    try:
        OP, Freq, Damp, UnMapped, ModeData, modeID_file = postproCampbell(fst_files_generated, removeTwrAzimuth=True)
        
        print(f"\nMode identification summary written to: {modeID_file}")
        print("[INFO] You can manually edit this CSV file to refine mode identification and re-run only the plotting step if needed.")

        # --- Plot the Campbell Diagram ---
        print('--- Plotting Campbell Diagram ---')
        fig, axes = plotCampbell(OP, Freq, Damp, sx='RotSpeed_[rpm]', UnMapped=UnMapped, ps=[1, num_blades, 2*num_blades])
        
        fig.suptitle('Campbell Diagram for WindPACT 5.0 MW Turbine', fontsize=16)
        plt.tight_layout(rect=[0, 0, 1, 0.95])
        plt.savefig('Campbell_Diagram.png', dpi=300)
        print("\nCampbell diagram saved to Campbell_Diagram.png")
        plt.show()

    except Exception as e:
        print(f"\nAn error occurred during post-processing with openfast_toolbox: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    if not os.path.exists(fast_input_file):
        print(f"Error: Main OpenFAST input file '{fast_input_file}' not found.")
        print("Please place it in the same directory as this script, or provide the full path.")
    else:
        generate_campbell_data()