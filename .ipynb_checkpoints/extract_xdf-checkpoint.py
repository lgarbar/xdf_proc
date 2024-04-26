import glob
import os
from xdf_proc.MobiXDF import nowstr
import pandas as pd
from xdf_proc.xdf_processing import process_xdf_file, process_xdf_modalities
import argparse
import tkinter as tk
from tkinter import filedialog
from tkinter import simpledialog
from concurrent.futures import ProcessPoolExecutor

def init_folder(folder: str)->bool:
    """
    Initialize a new folder.

    Parameters:
    folder (str): The name of the folder to initialize.

    Returns:
    bool: True if the folder exists or was successfully created, False otherwise.
    """
    if not os.path.isdir(folder):
        os.makedirs(folder)
    return os.path.isdir(folder)

def init_log_file(source_folder: str)->bool:
    """
    Initialize a new log file in the source folder.

    Parameters:
    source_folder (str): The folder where the log file will be created.

    Returns:
    bool: True if the log file exists or was successfully created, False otherwise.
    """
    if not os.path.isfile(os.path.join(source_folder, "process_log.csv")):
        with open(os.path.join(source_folder, "process_log.csv"), 'w') as f:
            f.write("xdf_file,success,date_processed\n")
    return os.path.isfile(os.path.join(source_folder, "process_log.csv"))

def update_process_log(xdf_file: str, success:bool)->bool:
    """
    Update the process log with the status of a processed xdf file.

    Parameters:
    xdf_file (str): The name of the xdf file that was processed.
    success (bool): The status of the processing (True if successful, False otherwise).

    Returns:
    bool: Always returns True.
    """
    rowstr = f"{os.path.basename(xdf_file)},{success},{nowstr()}"
    source_folder = os.path.dirname(os.path.abspath(xdf_file))
    with open(os.path.join(source_folder, "process_log.csv"),'a') as f:
        f.write(f"{rowstr}\n")
    return True

def get_xdf_files(source_folder: str, task_name: str)->list:
    """
    Get a list of xdf files in the source folder that match the task name.

    Parameters:
    source_folder (str): The folder to search for xdf files.
    task_name (str): The task name to match in the xdf files.

    Returns:
    list: A list of xdf files that match the task name.
    """
    search_str = f"{source_folder}/*{task_name}*.xdf*"
    return glob.glob(search_str)

def process_xdf_file_and_update_log(xdf_file: str, dest_folder: str) -> None:
    """
    Process an xdf file and update the log with the status of the processing.

    Parameters:
    xdf_file (str): The name of the xdf file to process.
    dest_folder (str): The destination folder for the processed file.
    """
    print(f"Processing {xdf_file}")
    if all(x == 1 for x in args.modalities):
        res = process_xdf_file(xdf_file, dest_folder)
    else:
        process_xdf_modalities(args.modalities, xdf_file, dest_folder)
    
    update_process_log(xdf_file, isinstance(res, pd.DataFrame))

def process_xdf_list(xdf_list: list, dest_folder:str, max_workers:int=4):
    """
    Process a list of xdf files and update the log with the status of each processing.

    Parameters:
    xdf_list (list): The list of xdf files to process.
    dest_folder (str): The destination folder for the processed files.
    max_workers (int): The maximum number of workers to use for processing. Default is 4.
    """
    print('starting')
    with ProcessPoolExecutor(max_workers) as executor:
        executor.map(process_xdf_file_and_update_log, xdf_list, [dest_folder]*len(xdf_list))
        

def drop_processed_files(xdf_list:list, source_folder: str)->list:
    """
    Drop already processed files from the list of xdf files.

    Parameters:
    xdf_list (list): The list of xdf files to process.
    source_folder (str): The folder where the log file is located.

    Returns:
    list: A new list of xdf files that have not been processed yet.
    """
    df = pd.read_csv(os.path.join(source_folder, "process_log.csv"))
    new_list = [xdf_file for xdf_file in xdf_list if xdf_file not in df["xdf_file"].values]
    x = set(new_list)
    y = set(xdf_list)
    dropped = list(y.difference(x))
    if len(dropped) > 0:
        print(f"Dropping {len(dropped)} already-processed files:")
        print("\n".join(dropped))
    return new_list

def parse_args():
    parser = argparse.ArgumentParser(description="Your script description")

    # Add optional command-line arguments
    parser.add_argument("-s", "--source_folder", type=str, help="full path to folder containing xdf files")
    parser.add_argument("-d", "--dest_folder", type=str, help="full path to folder to xdf derivatives")
    parser.add_argument("-t", "--task_name", type=str, help="task name (e.g. ravlt1). note: the task name is case sensitive")
    parser.add_argument("-w", "--max_workers", type=int, default=2, help="maximum number of workers. default is 2.")
    parser.add_argument("-m", "--modalities", type=str, help="which modalities to extract. e.g. eyetracking, audio, video")

    args = parser.parse_args()

    # If arguments are not provided, show GUI for folder selection
    if not args.source_folder:
        args.source_folder = ask_folder("Select Input Folder")

    if not args.dest_folder:
        args.dest_folder = ask_folder("Select Output Folder")
        
    if not args.task_name:
        args.task_name = ask_task()
        
    if args.modalities == 'all':
        args.modalities = [1] * 8
    elif not args.modalities:
        root_checkbox, get_checkbox_states = create_checkbox_app()
        root_checkbox.mainloop()
        args.modalities = get_checkbox_states()
    else:
        mod_list = [mods.lower() for mods in args.modalities.split(',')]
        args.modalities = [0] * 8
        mods_opts = ['eyetracking', 'audio', 'lsl_events', 'raw_events', 'physio', 'eeg', 'eeg_markers', 'behav']
        for i in range(len(mods_opts)):
            if mods_opts[i] in mod_list:
                args.modalities[i] = 1

    return args

def ask_folder(title):
    root_folder = tk.Tk()
    root_folder.withdraw()  # Hide the main window

    folder_path = filedialog.askdirectory(title=title)

    root_folder.destroy()  # Close the hidden main window

    return folder_path

def ask_task():
    # Create a Tkinter root window (invisible)
    root_task = tk.Tk()
    root_task.withdraw()

    # Call the simple dialog box
    user_input = simpledialog.askstring("Input", "Which task do you want to extract (case-sensitive)?")
    
    root_task.destroy()

    # Return the user input as a string
    return user_input

def create_checkbox_app():
    def update_checkboxes():
        if all(var.get() == 1 for var in checkbox_vars):
            select_all_var.set(1)
        else:
            select_all_var.set(0)

    def update_select_all():
        state = select_all_var.get()
        for var in checkbox_vars:
            var.set(state)

    def submit():
        root_mod.destroy()

    root_mod = tk.Tk()
    root_mod.title("Checkbox Example")

    title_label = tk.Label(root_mod, text="Select Which Modalities to Extract", font=("Helvetica", 16))
    title_label.pack(pady=10)

    select_all_var = tk.IntVar()
    select_all = tk.Checkbutton(root_mod, text="Select All", variable=select_all_var, command=update_select_all, anchor='w')
    select_all.pack(fill='x', padx=10, pady=5)
    
    checkbox_texts = ["Eyetracking", "Audio", "LSL Events", "Raw Events", "Physio", "EEG", "EEG Markers", "Behavioral Data"]
    checkbox_vars = [tk.IntVar() for _ in range(len(checkbox_texts))]
    checkboxes = []

    for i, text in enumerate(checkbox_texts):
        checkbox = tk.Checkbutton(root_mod, text=text, variable=checkbox_vars[i], command=update_checkboxes, anchor='w')
        checkbox.pack(fill='x', padx=10, pady=5)
        checkboxes.append(checkbox)

    submit_button = tk.Button(root_mod, text="Submit", command=submit)
    submit_button.pack(pady=10)

    def get_checkbox_states():
        return [var.get() for var in checkbox_vars]

    return root_mod, get_checkbox_states

if __name__ == "__main__":
    args = parse_args()

    # Now you can use args.input_folder and args.output_folder in your script
    print("Input folder:", args.source_folder)
    print("Output folder:", args.dest_folder)
    print("Task:", args.task_name)
    
    if not init_folder(args.dest_folder) or not init_log_file(args.source_folder):
        print(f"Initialization failed. Do you have permission to write to {args.dest_folder} and {args.source_folder}?")
        exit()
    
    xdf_list = get_xdf_files(args.source_folder, args.task_name)
    
    process_xdf_list(xdf_list, args.dest_folder, args.max_workers)
    
    