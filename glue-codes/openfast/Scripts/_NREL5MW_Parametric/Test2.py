""" Example to run a set of OpenFAST simulations (parametric study)

This script uses a reference directory (`ref_dir`) which contains a reference input file (.fst)
1) The reference directory is copied to a working directory (`work_dir`).
2) All the fast input files are generated in this directory based on a list of dictionaries (`PARAMS`).
For each dictionary in this list:
   - The keys are "path" to a input parameter, e.g. `EDFile|RotSpeed`  or `FAST|TMax`.
     These should correspond to the variables used in the FAST inputs files.
   - The values are the values corresponding to this parameter
For instance:
     PARAMS[0]['EDFile|RotSpeed']       = 5
     PARAMS[0]['InflowFile|HWindSpeed'] = 10

3) The simulations are run, successively distributed on `nCores` CPUs.
4) The output files are read, and averaged based on a method (e.g. average over a set of periods,
    see averagePostPro in postpro for the different averaging methods).
   A pandas DataFrame is returned

"""
import numpy as np
import os
import openfast_toolbox.openfast_toolbox.case_generation.case_gen as case_gen
import openfast_toolbox.openfast_toolbox.case_generation.runner as runner
import openfast_toolbox.openfast_toolbox.postpro as postpro
from openfast_toolbox.openfast_toolbox.io.fast_input_file import FASTInputFile
# Get current directory so this script can be called from any location
scriptDir=os.path.dirname(__file__)

# --- Parameters for this script
FAST_EXE  = os.path.join(scriptDir, r'C:\Users\Admin\Documents\HK243\DACN_DHBK\Code\EXE\openfast_x64_1.exe') # Location of a FAST exe (and dll)
ref_dir   = os.path.join(scriptDir, r'C:\Users\Admin\Documents\HK243\DACN_DHBK\Code\r-test\glue-codes\openfast\5MW_Land_Linear_Aero')  # Folder where the fast input files are located (will be copied)
main_file = '5MW_Land_Linear_Aero.fst'  # Main file in ref_dir, used as a template
work_dir  = '_NREL5MW_Parametric/'     # Output folder (will be created)


# --- Reading some reference files/tables to be able to modify tables
# BDBld_ref = FASTInputFile('BeamDyn_Blade_ref.dat')
# print(BDBld_ref.keys())
# BP_ref = BDBld_ref['BeamProperties']
#
# HD_ref = FASTInputFile('HD_ref.dat')
# print(HD_ref.keys())
# SmplProp_ref = HD_ref['SmplProp'] 

# --- Defining the parametric study  (list of dictionnaries with keys as FAST parameters)
WS    = [4   , 5   , 10   , 12   , 14  , 16]
RPM   = [2.5 , 7.5 , 11.3 , 12.1 , 12.1, 12.1]
PITCH = [0   , 0   , 0    , 0    , 8.7 , 10.4]
BaseDict = {'TMax': 10, 'DT': 0.01, 'DT_Out': 0.1}
BaseDict = case_gen.paramsNoController(BaseDict)   # Remove the controller
#BaseDict = case_gen.paramsControllerDLL(BaseDict) # Activate the controller
#BaseDict = case_gen.paramsStiff(BaseDict)         # Make the turbine stiff (except generator)
#BaseDict = case_gen.paramsNoGen(BaseDict)         # Remove the Generator DOF
PARAMS=[]
for i,(wsp,rpm,pitch) in enumerate(zip(WS,RPM,PITCH)): # NOTE: same length of WS and RPM otherwise do multiple for loops
    p=BaseDict.copy()

    # --- Changing typical parameters (operating ocnditions)
    p['EDFile|RotSpeed']       = rpm
    p['EDFile|BlPitch(1)']     = pitch
    p['EDFile|BlPitch(2)']     = pitch
    p['EDFile|BlPitch(3)']     = pitch
    p['InflowFile|HWindSpeed'] = wsp
    p['InflowFile|WindType']   = 1 # Setting steady wind
    # Defining name for .fst file
    p['__name__']='{:03d}_ws{:04.1f}_om{:04.2f}'.format(i,p['InflowFile|HWindSpeed'],p['EDFile|RotSpeed'])
    
    # --- Examples to change other parameters
    #  p['AeroFile|TwrAero']       = True
    #  p['EDFile|BldFile(1)|AdjBlMs'] =1.1
    #  p['EDFile|BldFile(2)|AdjBlMs'] =1.1
    #  p['EDFile|BldFile(3)|AdjBlMs'] =1.1
    # Changing BeamDyn properties
    #  BP     = BP_ref.copy() # Make a copy to be safe
    #  BP['K']= BP['K']*i   # Modify stiffness
    #  p['BDBldFile(1)|BldFile|BeamProperties'] = BP # Use the updated stiffness for this case
    # Changing HydroDyn properties
    #  SmplProp = SmplProp_ref.copy() # Make a copy to be safe
    #  SmplProp[0,0] = Cd[i]  # Change Cd value
    #  p['HDFile|SmplProp'] = SmplProp # Use the updated table for this case,s

    PARAMS.append(p)

# --- Generating all files in a workdir
fastFiles=case_gen.templateReplace(PARAMS, ref_dir, outputDir=work_dir, removeRefSubFiles=True, main_file=main_file, oneSimPerDir=False)
print('Main input files:')
print(fastFiles)

# --- Creating a batch script just in case
runner.writeBatch(os.path.join(work_dir,'_RUN_ALL.bat'),fastFiles,fastExe=FAST_EXE)

if __name__=='__main__':
    # --- Running the simulations
    runner.run_fastfiles(fastFiles, fastExe=FAST_EXE, parallel=True, showOutputs=False, nCores=4)

    # --- Simple Postprocessing ---
    # MODIFICATION: Construct full, absolute paths to the output files.
    
    outFiles = []
    for p in PARAMS:
        # Get the base name (e.g., "000_ws04.0_om2.50")
        base_name = p['__name__']
        # Construct the full path to the .outb file inside the work_dir
        outfile_path = os.path.join(work_dir, base_name + '.outb')
        outFiles.append(outfile_path)

    # --- Diagnostic Print ---
    # This will show you the exact paths being sent to the post-processor
    # and confirm whether the files actually exist at those paths.
    print("\n--- Attempting to read the following output files: ---")
    all_files_found = True
    for f in outFiles:
        if not os.path.exists(f):
            all_files_found = False
        print(f"  - Path: {os.path.abspath(f)}")
        print(f"    Exists: {os.path.exists(f)}")
    print("----------------------------------------------------")

    if not all_files_found:
        print("\nERROR: One or more .outb files were not found. The OpenFAST simulations may have failed.")
        print("Please check the output above and the contents of the '{}' directory.".format(work_dir))
    else:
        print("\nAll .outb files found. Proceeding with post-processing...")
        avg_results = postpro.averagePostPro(outFiles,avgMethod='periods',avgParam=1, ColMap = {'WS_[m/s]':'Wind1VelX_[m/s]'},ColSort='WS_[m/s]')
        print('>> Average results:')
        print(avg_results)

        import matplotlib.pyplot as plt
        plt.plot(avg_results['WS_[m/s]'], avg_results['RtAeroCp_[-]'])
        plt.xlabel('Wind speed [m/s]')
        plt.ylabel('Power coefficient [-]')
        plt.show()

if __name__=='__test__':
    # Need openfast.exe, not running
    import shutil
    shutil.rmtree(work_dir)
