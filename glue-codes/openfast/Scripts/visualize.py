import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import re

def read_fast_out_file(filepath):
    """
    Reads a text-based OpenFAST .out file into a pandas DataFrame.
    It intelligently finds the header and unit lines to build proper column names.

    Args:
        filepath (str): The full path to the .out file.

    Returns:
        pandas.DataFrame: A DataFrame containing the time-series data, or an
                          empty DataFrame if the file cannot be parsed.
    """
    try:
        with open(filepath, 'r') as f:
            lines = f.readlines()

        # Find the header line (contains channel names) and the unit line
        header_line_index = -1
        for i, line in enumerate(lines):
            if line.strip().startswith("Time") and len(line.strip().split()) > 2:
                header_line_index = i
                break
        
        if header_line_index == -1:
            print(f"  > ERROR: Could not find the header line in {os.path.basename(filepath)}")
            return pd.DataFrame()

        unit_line_index = header_line_index + 1
        data_start_index = unit_line_index + 1

        col_names_raw = lines[header_line_index].strip().split()
        col_units_raw = lines[unit_line_index].strip().replace('(', '').replace(')', '').split()
        clean_columns = [f"{name}_[{unit}]" for name, unit in zip(col_names_raw, col_units_raw)]

        df = pd.read_csv(
            filepath,
            sep=r'\s+',
            skiprows=data_start_index,
            names=clean_columns,
            engine='python'
        )
        return df

    except Exception as e:
        print(f"  > ERROR: Failed to parse file {os.path.basename(filepath)}: {e}")
        return pd.DataFrame()


def process_results_directory(directory_path):
    """
    Reads all .out files in a given directory, calculates summary statistics,
    and returns a pandas DataFrame.
    """
    search_pattern = os.path.join(directory_path, '*.out')
    file_list = glob.glob(search_pattern)

    if not file_list:
        print(f"Error: No .out files found in the directory: {directory_path}")
        return pd.DataFrame()

    print(f"Found {len(file_list)} files to process.")
    results = []

    for filepath in file_list:
        basename = os.path.basename(filepath)
        print(f"Processing: {basename}")
        
        try:
            ws_part = next(part for part in basename.split('_') if part.startswith('ws'))
            wind_speed = float(ws_part.replace('ws', ''))
        except (StopIteration, ValueError):
            print(f"  > WARNING: Could not determine wind speed from filename '{basename}'. Skipping.")
            continue

        df = read_fast_out_file(filepath)
        if df.empty:
            continue

        time = df['Time_[s]']
        start_time_for_avg = time.iloc[-1] / 2
        df_steady = df[time > start_time_for_avg]
        
        required_cols = ['RtAeroCp_[-]', 'RotSpeed_[rpm]', 'BldPitch1_[deg]']
        if not all(col in df_steady.columns for col in required_cols):
            # Check for GenPwr if RtAeroCp is missing
            if 'GenPwr_[kW]' in df_steady.columns:
                 print(f"  > INFO: 'RtAeroCp_[-]' not found. You can add it to the OutList in ElastoDyn for a Cp plot.")
            else:
                print(f"  > WARNING: One or more required columns not found in {basename}. Skipping stats.")
                continue

        # Calculate stats for available columns
        stats = {'WindSpeed_[m/s]': wind_speed, 'FileName': basename}
        if 'RtAeroCp_[-]' in df_steady.columns:
            stats['Mean_Cp_[-]'] = df_steady['RtAeroCp_[-]'].mean()
        if 'RotSpeed_[rpm]' in df_steady.columns:
            stats['Mean_RPM_[rpm]'] = df_steady['RotSpeed_[rpm]'].mean()
        if 'BldPitch1_[deg]' in df_steady.columns:
            stats['Mean_Pitch_[deg]'] = df_steady['BldPitch1_[deg]'].mean()
        
        results.append(stats)

    if not results:
        print("No data was successfully processed.")
        return pd.DataFrame()
        
    results_df = pd.DataFrame(results)
    results_df.sort_values(by='WindSpeed_[m/s]', inplace=True)
    results_df.reset_index(drop=True, inplace=True)
    
    return results_df


if __name__ == "__main__":
    target_dir = '_NREL5MW_Parametric'
    summary_df = process_results_directory(target_dir)

    if not summary_df.empty:
        print("\n--- Summary of Results ---")
        print(summary_df)

        # --- Visualize the results ---
        # Determine how many plots are needed based on available data
        plot_cols = [col for col in ['Mean_Cp_[-]', 'Mean_RPM_[rpm]', 'Mean_Pitch_[deg]'] if col in summary_df.columns]
        num_plots = len(plot_cols)

        if num_plots > 0:
            fig, axes = plt.subplots(num_plots, 1, figsize=(10, 4 * num_plots), sharex=True)
            if num_plots == 1:
                axes = [axes] # Make it iterable if there's only one plot
            fig.suptitle('Parametric Study Results (from .out files)', fontsize=16)
            
            # Create a dictionary to hold plot properties
            plot_map = {
                'Mean_Cp_[-]':      {'ax_idx': 0, 'label': 'Mean Power Coefficient [-]', 'color': 'b'},
                'Mean_RPM_[rpm]':   {'ax_idx': 1, 'label': 'Mean Rotor Speed [rpm]',   'color': 'r'},
                'Mean_Pitch_[deg]': {'ax_idx': 2, 'label': 'Mean Blade Pitch [deg]',   'color': 'g'}
            }
            
            current_ax_index = 0
            for col, props in plot_map.items():
                if col in summary_df.columns:
                    ax = axes[current_ax_index]
                    ax.plot(summary_df['WindSpeed_[m/s]'], summary_df[col], 'o-', color=props['color'])
                    ax.set_ylabel(props['label'])
                    ax.grid(True)
                    current_ax_index += 1

            # Set a common x-label on the bottom-most plot
            axes[-1].set_xlabel('Wind Speed [m/s]')
            
            plt.tight_layout(rect=[0, 0, 1, 0.96])
            plt.show()