------- OpenFAST EXAMPLE INPUT FILE -------------------------------------------
FAST Certification Test #23: NREL 5.0 MW Baseline Wind Turbine with MIT-NREL TLP Configuration, for use in offshore analysis
---------------------- SIMULATION CONTROL --------------------------------------
True         Echo            - Echo input data to <RootName>.ech (flag)
"FATAL"       AbortLevel      - Error level when simulation should abort (string) {"WARNING", "SEVERE", "FATAL"}
         15   TMax            - Total run time (s)
     0.0125   DT              - Recommended module time step (s)
          2   InterpOrder     - Interpolation order for input/output time history (-) {1=linear, 2=quadratic}
          0   NumCrctn        - Number of correction iterations (-) {0=explicit calculation, i.e., no corrections}
      99999   DT_UJac         - Time between calls to get Jacobians (s)
    1000000   UJacSclFact     - Scaling factor used in Jacobians (-)
---------------------- FEATURE SWITCHES AND FLAGS ------------------------------
          1   CompElast       - Compute structural dynamics (switch) {1=ElastoDyn; 2=ElastoDyn + BeamDyn for blades; 3=Simplified ElastoDyn}
          1   CompInflow      - Compute inflow wind velocities (switch) {0=still air; 1=InflowWind; 2=external from ExtInflow}
          2   CompAero        - Compute aerodynamic loads (switch) {0=None; 1=AeroDisk; 2=AeroDyn; 3=ExtLoads}
          1   CompServo       - Compute control and electrical-drive dynamics (switch) {0=None; 1=ServoDyn}
          1   CompSeaSt       - Compute sea state information (switch) {0=None; 1=SeaState}
          1   CompHydro       - Compute hydrodynamic loads (switch) {0=None; 1=HydroDyn}
          0   CompSub         - Compute sub-structural dynamics (switch) {0=None; 1=SubDyn; 2=External Platform MCKF}
          1   CompMooring     - Compute mooring system (switch) {0=None; 1=MAP++; 2=FEAMooring; 3=MoorDyn; 4=OrcaFlex}
          0   CompIce         - Compute ice loads (switch) {0=None; 1=IceFloe; 2=IceDyn}
          0   MHK             - MHK turbine type (switch) {0=Not an MHK turbine; 1=Fixed MHK turbine; 2=Floating MHK turbine}
---------------------- ENVIRONMENTAL CONDITIONS --------------------------------
    9.80665   Gravity         - Gravitational acceleration (m/s^2)
      1.225   AirDens         - Air density (kg/m^3)
       1025   WtrDens         - Water density (kg/m^3)
  1.464E-05   KinVisc         - Kinematic viscosity of working fluid (m^2/s)
        335   SpdSound        - Speed of sound in working fluid (m/s)
     103500   Patm            - Atmospheric pressure (Pa) [used only for an MHK turbine cavitation check]
       1700   Pvap            - Vapour pressure of working fluid (Pa) [used only for an MHK turbine cavitation check]
        200   WtrDpth         - Water depth (m)
          0   MSL2SWL         - Offset between still-water level and mean sea level (m) [positive upward]
---------------------- INPUT FILES ---------------------------------------------
"NRELOffshrBsline5MW_MIT_NREL_TLP_ElastoDyn.dat"    EDFile          - Name of file containing ElastoDyn input parameters (quoted string)
"../5MW_Baseline/NRELOffshrBsline5MW_BeamDyn.dat"    BDBldFile(1)    - Name of file containing BeamDyn input parameters for blade 1 (quoted string)
"../5MW_Baseline/NRELOffshrBsline5MW_BeamDyn.dat"    BDBldFile(2)    - Name of file containing BeamDyn input parameters for blade 2 (quoted string)
"../5MW_Baseline/NRELOffshrBsline5MW_BeamDyn.dat"    BDBldFile(3)    - Name of file containing BeamDyn input parameters for blade 3 (quoted string)
"../5MW_Baseline/NRELOffshrBsline5MW_InflowWind_12mps.dat"    InflowFile      - Name of file containing inflow wind input parameters (quoted string)
"NRELOffshrBsline5MW_Onshore_AeroDyn.dat"    AeroFile        - Name of file containing aerodynamic input parameters (quoted string)
"NRELOffshrBsline5MW_MIT_NREL_TLP_ServoDyn.dat"    ServoFile       - Name of file containing control and electrical-drive input parameters (quoted string)
"SeaState.dat"    SeaStFile       - Name of file containing sea state input parameters (quoted string)
"NRELOffshrBsline5MW_MIT_NREL_TLP_HydroDyn.dat"    HydroFile       - Name of file containing hydrodynamic input parameters (quoted string)
"unused"      SubFile         - Name of file containing sub-structural input parameters (quoted string)
"NRELOffshrBsline5MW_MIT_NREL_TLP_MAP.dat"    MooringFile     - Name of file containing mooring system input parameters (quoted string)
"unused"      IceFile         - Name of file containing ice input parameters (quoted string)
---------------------- OUTPUT --------------------------------------------------
False         SumPrint        - Print summary data to "<RootName>.sum" (flag)
          1   SttsTime        - Amount of time between screen status messages (s)
       1000   ChkptTime       - Amount of time between creating checkpoint files for potential restart (s)
     0.0125   DT_Out          - Time step for tabular output (s) (or "default")
          0   TStart          - Time to begin tabular output (s)
          3   OutFileFmt      - Format for tabular (time-marching) output file (switch) {1: text file [<RootName>.out], 2: binary file [<RootName>.outb], 3: both 1 and 2, 4: uncompressed binary [<RootName>.outb, 5: both 1 and 4}
True          TabDelim        - Use tab delimiters in text tabular output file? (flag) {uses spaces if false}
"ES15.7E2"    OutFmt          - Format used for text tabular output, excluding the time channel.  Resulting field should be 10 characters. (quoted string)
---------------------- LINEARIZATION -------------------------------------------
False         Linearize       - Linearization analysis (flag)
False         CalcSteady      - Calculate a steady-state periodic operating point before linearization? [unused if Linearize=False] (flag)
          3   TrimCase        - Controller parameter to be trimmed {1:yaw; 2:torque; 3:pitch} [used only if CalcSteady=True] (-)
      0.001   TrimTol         - Tolerance for the rotational speed convergence [used only if CalcSteady=True] (-)
       0.01   TrimGain        - Proportional gain for the rotational speed error (>0) [used only if CalcSteady=True] (rad/(rad/s) for yaw or pitch; Nm/(rad/s) for torque)
          0   Twr_Kdmp        - Damping factor for the tower [used only if CalcSteady=True] (N/(m/s))
          0   Bld_Kdmp        - Damping factor for the blades [used only if CalcSteady=True] (N/(m/s))
          2   NLinTimes       - Number of times to linearize (-) [>=1] [unused if Linearize=False]
         30,         60    LinTimes        - List of times at which to linearize (s) [1 to NLinTimes] [used only when Linearize=True and CalcSteady=False]
          1   LinInputs       - Inputs included in linearization (switch) {0=none; 1=standard; 2=all module inputs (debug)} [unused if Linearize=False]
          1   LinOutputs      - Outputs included in linearization (switch) {0=none; 1=from OutList(s); 2=all module outputs (debug)} [unused if Linearize=False]
False         LinOutJac       - Include full Jacobians in linearization output (for debug) (flag) [unused if Linearize=False; used only if LinInputs=LinOutputs=2]
False         LinOutMod       - Write module-level linearization output files in addition to output for full system? (flag) [unused if Linearize=False]
---------------------- VISUALIZATION ------------------------------------------
          2   WrVTK           - VTK visualization data output: (switch) {0=none; 1=initialization data only; 2=animation; 3=mode shapes}
          1   VTK_type        - Type of VTK visualization data: (switch) {1=surfaces; 2=basic meshes (lines/points); 3=all meshes (debug)} [unused if WrVTK=0]
false         VTK_fields      - Write mesh fields to VTK data files? (flag) {true/false} [unused if WrVTK=0]
         15   VTK_fps         - Frame rate for VTK output (frames per second){will use closest integer multiple of DT} [used only if WrVTK=2 or WrVTK=3]
---------------------- OUTPUT LIST ---------------------------------------------
OutList        - The next line(s) contains a list of output parameters.  See OutListParameters.xlsx for a listing of available output channels, (-)
"Time"          - Time

---------------------- BLADE LOADS AND MOMENTS --------------------------------
"RootFxb1"      - Blade 1 flapwise shear force at root
"RootFyb1"      - Blade 1 edgewise shear force at root
"RootFzb1"      - Blade 1 axial force at root
"RootMxb1"      - Blade 1 edgewise moment at root
"RootMyb1"      - Blade 1 flapwise moment at root
"RootMzb1"      - Blade 1 torsional moment at root
"RootFxb2"      - Blade 2 flapwise shear force at root
"RootFyb2"      - Blade 2 edgewise shear force at root
"RootFzb2"      - Blade 2 axial force at root
"RootMxb2"      - Blade 2 edgewise moment at root
"RootMyb2"      - Blade 2 flapwise moment at root
"RootMzb2"      - Blade 2 torsional moment at root
"RootFxb3"      - Blade 3 flapwise shear force at root
"RootFyb3"      - Blade 3 edgewise shear force at root
"RootFzb3"      - Blade 3 axial force at root
"RootMxb3"      - Blade 3 edgewise moment at root
"RootMyb3"      - Blade 3 flapwise moment at root
"RootMzb3"      - Blade 3 torsional moment at root

---------------------- HUB AND SHAFT LOADS ------------------------------------
"LSShftFxa"     - Low-speed shaft thrust force (x)
"LSShftFya"     - Low-speed shaft shear force (y)
"LSShftFza"     - Low-speed shaft shear force (z)
"LSShftMxa"     - Low-speed shaft torque
"LSSTipMya"     - Low-speed shaft bending moment (y)
"LSSTipMza"     - Low-speed shaft bending moment (z)
"RotThrust"     - Rotor thrust
"RotTorq"       - Rotor torque
"LSSGagMya"     - Low-speed shaft bending moment (y) at strain gage
"LSSGagMza"     - Low-speed shaft bending moment (z) at strain gage

---------------------- TOWER LOADS AND MOMENTS --------------------------------
"TwrBsFxt"      - Tower base fore-aft shear force
"TwrBsFyt"      - Tower base side-to-side shear force
"TwrBsFzt"      - Tower base axial force
"TwrBsMxt"      - Tower base roll moment
"TwrBsMyt"      - Tower base pitch moment
"TwrBsMzt"      - Tower base yaw moment
"YawBrFxp"      - Yaw bearing fore-aft shear force
"YawBrFyp"      - Yaw bearing side-to-side shear force
"YawBrFzp"      - Yaw bearing axial force
"YawBrMxp"      - Yaw bearing roll moment
"YawBrMyp"      - Yaw bearing pitch moment
"YawBrMzp"      - Yaw bearing yaw moment

---------------------- PLATFORM LOADS (FOR FLOATING) --------------------------
"PtfmFxt"       - Platform horizontal surge force
"PtfmFyt"       - Platform horizontal sway force
"PtfmFzt"       - Platform vertical heave force
"PtfmMxt"       - Platform roll moment
"PtfmMyt"       - Platform pitch moment
"PtfmMzt"       - Platform yaw moment

---------------------- MOORING LOADS ------------------------------------------
"Fair1Ten"      - Mooring line 1 tension at fairlead
"Fair2Ten"      - Mooring line 2 tension at fairlead
"Fair3Ten"      - Mooring line 3 tension at fairlead
"Fair4Ten"      - Mooring line 4 tension at fairlead
"Fair5Ten"      - Mooring line 5 tension at fairlead
"Fair6Ten"      - Mooring line 6 tension at fairlead
"Fair7Ten"      - Mooring line 7 tension at fairlead
"Fair8Ten"      - Mooring line 8 tension at fairlead

---------------------- DISPLACEMENTS AND ROTATIONS ----------------------------
"PtfmSurge"     - Platform surge displacement
"PtfmSway"      - Platform sway displacement
"PtfmHeave"     - Platform heave displacement
"PtfmRoll"      - Platform roll rotation
"PtfmPitch"     - Platform pitch rotation
"PtfmYaw"       - Platform yaw rotation
"TwrTpTDxi"     - Tower top fore-aft deflection
"TwrTpTDyi"     - Tower top side-to-side deflection
"TwrTpTDzi"     - Tower top axial deflection
"YawBrTDxt"     - Yaw bearing fore-aft deflection
"YawBrTDyt"     - Yaw bearing side-to-side deflection
"YawBrTDzt"     - Yaw bearing axial deflection

---------------------- ACCELERATIONS (FOR DYNAMIC ANALYSIS) -------------------
"PtfmTAxt"      - Platform translational acceleration (surge)
"PtfmTAyt"      - Platform translational acceleration (sway)
"PtfmTAzt"      - Platform translational acceleration (heave)
"PtfmRAxt"      - Platform rotational acceleration (roll)
"PtfmRAyt"      - Platform rotational acceleration (pitch)
"PtfmRAzt"      - Platform rotational acceleration (yaw)

---------------------- OPERATIONAL PARAMETERS ---------------------------------
"Wind1VelX"     - Wind velocity in X direction
"Wind1VelY"     - Wind velocity in Y direction
"Wind1VelZ"     - Wind velocity in Z direction
"RotSpeed"      - Rotor speed
"GenSpeed"      - Generator speed
"BldPitch1"     - Blade 1 pitch angle
"BldPitch2"     - Blade 2 pitch angle
"BldPitch3"     - Blade 3 pitch angle
"Azimuth"       - Rotor azimuth angle

---------------------- WAVE LOADS (FOR HYDRODYNAMIC ANALYSIS) ----------------
"Wave1Elev"     - Wave elevation at platform
"HydroFxt"      - Total hydrodynamic force in surge
"HydroFyt"      - Total hydrodynamic force in sway
"HydroFzt"      - Total hydrodynamic force in heave
"HydroMxt"      - Total hydrodynamic moment in roll
"HydroMyt"      - Total hydrodynamic moment in pitch
"HydroMzt"      - Total hydrodynamic moment in yaw

END of input file (the word "END" must appear in the first 3 columns of this last OutList line)
