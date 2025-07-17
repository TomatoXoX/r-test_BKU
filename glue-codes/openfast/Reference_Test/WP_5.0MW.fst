------- OpenFAST v4.1.0 INPUT FILE -------------------------------------------
WindPACT 5.0 MW Baseline Wind Turbine for OpenFAST.
---------------------- SIMULATION CONTROL --------------------------------------
True          Echo            - Echo input data to <RootName>.ech (flag)
"FATAL"       AbortLevel      - Error level when simulation should abort (string) {"WARNING", "SEVERE", "FATAL"}
600           TMax            - Total run time (s)
0.005         DT              - Recommended module time step (s)
1             InterpOrder     - Interpolation order for input/output time history (-) {1=linear, 2=quadratic}
0             NumCrctns       - Number of correction-prediction loops for time integration (-) {0=explicit, >0=implicit}
99999         DT_U_Out        - Time step for user-defined output files (s)
0             TStart          - Time to begin tabular output (s)
1             OutFileFmt      - Format for tabular output file(s) (1: text file [<RootName>.out], 2: binary file [<RootName>.outb], 3: both)
True          SumPrint        - Print summary data to <RootName>.sum (flag)
1             SttsTime        - Amount of time between screen status messages (s)
99999         ChkptTime       - Amount of time between creating checkpoint files for restart (s)
"DEFAULT"     DT_Out          - Time step for tabular output (s) (or "DEFAULT")
"DEFAULT"     TStart          - Time to begin tabular output (s) (or "DEFAULT")
"DEFAULT"     OutFmt          - Format for tabular output file (see OutFileFmt) (or "DEFAULT")

---------------------- FEATURE SWITCHES AND FLAGS ------------------------------
True          CompElast       - Compute structural dynamics (switch) [ElastoDyn]
True          CompInflow      - Compute inflow wind velocities (switch) [InflowWind]
True          CompAero        - Compute aerodynamic loads (switch) [AeroDyn]
True          CompServo       - Compute control and electrical-drive dynamics (switch) [ServoDyn]
False         CompHydro       - Compute hydrodynamic loads (switch) [HydroDyn]
False         CompSub         - Compute substructure dynamics (switch) [SubDyn]
False         CompMooring     - Compute mooring system (switch) [MAP++ or MoorDyn]
False         CompIce         - Compute ice loads (switch) [IceFloe or IceDyn]

---------------------- INPUT FILES ---------------------------------------------
"WindPACT_5MW_ServoDyn.dat"    ServoFile       - Name of file containing servo drive and control input parameters (quoted string)
"WindPACT_5MW_ElastoDyn.dat"   ElastoFile      - Name of file containing elastic structural dynamics input parameters (quoted string)
"WindPACT_5MW_InflowWind.dat"  InflowFile      - Name of file containing inflow wind input parameters (quoted string)
"WindPACT_5MW_AeroDyn.dat"     AeroFile        - Name of file containing aerodynamic input parameters (quoted string)
"unused"      HydroFile       - Name of file containing hydrodynamic input parameters (quoted string)
"unused"      SubFile         - Name of file containing substructure input parameters (quoted string)
"unused"      MooringFile     - Name of file containing mooring system input parameters (quoted string)
"unused"      IceFile         - Name of file containing ice input parameters (quoted string)

---------------------- OUTPUT --------------------------------------------------
True          SumPrint        - Print summary data to "<RootName>.sum" (flag)
1             SttsTime        - Time between screen status messages (s)
99999         ChkptTime       - Time between checkpoint files for restart (s)
0.025         DT_Out          - Time step for tabular output {or "default"}
0             TStart          - Time to begin tabular output (s)
1             OutFileFmt      - Format for tabular output file (1: text, 2: binary, 3: both)
True          TabDelim        - Use tab delimiters in text tabular output file? (flag)
"ES10.3E2"    OutFmt          - Format used for text tabular output (except time). Resulting field should be 10 characters. (quoted string)
---------------------- LINEARIZATION -----------------------------------------
False         Linearize       - Perform linearization? (flag)