"""
Central configuration for the REFIT Data Cleaning and Appliance Disaggregation project.
All paths are relative to PROJECT_ROOT by default, with REFIT_DATA_DIR environment variable override.
"""
import os
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("REFIT_DATA_DIR", PROJECT_ROOT.parent))
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
FIGURES_DIR = PROJECT_ROOT / "figures"
RESULTS_DIR = PROJECT_ROOT / "results"

# Ensure runtime directories exist
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
FIGURES_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Channel mappings from CLEAN_READ_ME_081116.txt
CHANNEL_NAMES = {
    1: {
        'Aggregate': 'Aggregate',
        'Appliance1': 'Fridge (Hotpoint RLA50P)',
        'Appliance2': 'Freezer 1 (Beko CF393APW)',
        'Appliance3': 'Freezer 2',
        'Appliance4': 'Tumble Dryer (Creda T522VW)',  # Note: Listed as Washer Dryer in readme, but Creda T522VW is a vented tumble dryer
        'Appliance5': 'Washing Machine (Beko WMC6140)',
        'Appliance6': 'Dishwasher (Bosch)',
        'Appliance7': 'Computer (Lenovo H520s)',
        'Appliance8': 'Television Site (Toshiba 32BL502b)',
        'Appliance9': 'Electric Heater (GLEN 2172)'
    },
    2: {
        'Aggregate': 'Aggregate',
        'Appliance1': 'Fridge-Freezer',
        'Appliance2': 'Washing Machine (LG F1289TD)',
        'Appliance3': 'Dishwasher',
        'Appliance4': 'Television Site',
        'Appliance5': 'Microwave',
        'Appliance6': 'Toaster',
        'Appliance7': 'Hi-Fi',
        'Appliance8': 'Kettle',
        'Appliance9': 'Overhead Fan'
    },
    3: {
        'Aggregate': 'Aggregate',
        'Appliance1': 'Toaster (Dualit DPP2)',
        'Appliance2': 'Fridge-Freezer (Whirlpool ARC7612)',
        'Appliance3': 'Freezer (Frigidaire)',
        'Appliance4': 'Tumble Dryer',
        'Appliance5': 'Dishwasher (Bosch Exxcel)',
        'Appliance6': 'Washing Machine',
        'Appliance7': 'Television Site (Samsung)',
        'Appliance8': 'Microwave (Panasonic)',
        'Appliance9': 'Kettle (Dualit)'
    },
    4: {
        'Aggregate': 'Aggregate',
        'Appliance1': 'Fridge (Neff)',
        'Appliance2': 'Freezer (Ocean)',
        'Appliance3': 'Fridge-Freezer (Ariston)',
        'Appliance4': 'Washing Machine 1 (Servis 6065)',
        'Appliance5': 'Washing Machine 2 (Zanussi Z917)',
        'Appliance6': 'Desktop Computer',
        'Appliance7': 'Television Site (Sony)',
        'Appliance8': 'Microwave (Matsui)',
        'Appliance9': 'Kettle (Swan)'
    },
    5: {
        'Aggregate': 'Aggregate',
        'Appliance1': 'Fridge-Freezer (Fisher & Paykel)',
        'Appliance2': 'Tumble Dryer',
        'Appliance3': 'Washing Machine (AEG L99695HWD)',
        'Appliance4': 'Dishwasher',
        'Appliance5': 'Desktop Computer',
        'Appliance6': 'Television Site',
        'Appliance7': 'Microwave',
        'Appliance8': 'Kettle (Logik)',
        'Appliance9': 'Toaster (Breville)'
    }
}

# Dedicated washing machine channel column for each house
WM_COLUMNS = {
    1: 'Appliance5',
    2: 'Appliance2',
    3: 'Appliance6',
    4: 'Appliance4', # WM1 (WM2 is Appliance5)
    5: 'Appliance3'
}

# Standard column data types for memory efficiency
RAW_DTYPES = {
    'Unix': 'int64',
    'Aggregate': 'float32',
    'Appliance1': 'float32',
    'Appliance2': 'float32',
    'Appliance3': 'float32',
    'Appliance4': 'float32',
    'Appliance5': 'float32',
    'Appliance6': 'float32',
    'Appliance7': 'float32',
    'Appliance8': 'float32',
    'Appliance9': 'float32'
}

CLEAN_DTYPES = {
    **RAW_DTYPES,
    'Issues': 'int8'
}
