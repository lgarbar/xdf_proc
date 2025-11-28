# XDF Python Processing - MoBI XDF Extraction Tool

A comprehensive Python toolkit for extracting and processing XDF files collected in NKI's CBIN MoBILab. The main script, `extract_xdf.py`, extracts data for specified tasks and modalities from XDF files with support for both GUI and command-line interfaces.

## Overview

This package provides tools to process multi-modal XDF files from the MoBILab, handling:
- **Eyetracking data**: Extract gaze position and velocity
- **Audio**: Extract audio streams
- **Physiology**: Extract heart rate, respiration, and other vital signs
- **EEG**: Extract brain activity data with markers
- **Task Events**: Extract behavioral task-related events
- **Video**: Extract video streams
- **And more**: MindLogger data, behavioral data, LSL events

## Performance Note

For large-scale data processing, consider using the **Julia implementation** which provides **5-10x faster processing** compared to this Python version. See [../xdf_jl/README.md](../xdf_jl/README.md) for Julia setup.

## Installation

### Prerequisites

- **Python**: >= 3.10
- **Conda** or **Mamba**: Required for environment management (recommended)

If you don't have Conda installed, download [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Mamba](https://mamba.readthedocs.io/en/latest/installation.html).

### Setup Instructions

1. **Download the code**:
   ```bash
   # Option A: Clone from repository
   git clone https://github.com/lgarbar/xdf_proc.git
   cd xdf_proc/xdf_py
   
   # Option B: Or download the latest version and extract
   ```

2. **Create the conda environment** using the provided `requirements.yml`:
   ```bash
   conda create --name xdf_proc --file requirements.yml
   ```

3. **Activate the environment**:
   ```bash
   conda activate xdf_proc
   ```

### Linux Server Installation

If installing on a Linux-based server:

```bash
# Install Miniconda (if not already installed)
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -rf ~/miniconda3/miniconda.sh
~/miniconda3/bin/conda init bash
~/miniconda3/bin/conda init zsh

# Then create the environment
conda create --name xdf_proc --file requirements.yml
conda activate xdf_proc
```

## Dependencies

The project requires the following packages:

| Package   | Purpose |
|-----------|---------|
| `pyxdf`   | XDF file parsing and reading |
| `pandas`  | Data manipulation and formatting |
| `numpy`   | Numerical operations |
| `biosppy` | Physiological signal processing |
| `peakutils` | Peak detection in signal processing |

All are specified in `requirements.yml` and automatically installed when creating the environment.

## Usage

### Command-Line Interface

The main extraction script supports both command-line arguments and interactive GUI mode:

```bash
python extract_xdf.py [OPTIONS] source_folder task_name dest_folder
```

#### Required Arguments

| Argument | Description |
|----------|-------------|
| `source_folder` | Full path to folder containing XDF files |
| `task_name` | Task name to extract (e.g., `ravlt1`). **Case-sensitive** |
| `dest_folder` | Full path to folder for processed output |

#### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `-w, --max_workers` | 2 | Maximum number of parallel worker processes |
| `-m, --modalities` | interactive | Modalities to extract. See modality options below |
| `-h, --help` | — | Show help message |

#### Modality Options

Specify modalities using comma-separated list (no spaces):

```bash
python extract_xdf.py -m eyetracking,audio,physio -s /path/to/data -t task_name -d /path/to/output
```

Available modalities:
- `eyetracking`: Gaze position and velocity data
- `audio`: Audio streams
- `physio`: Physiological signals (heart rate, respiration, etc.)
- `eeg`: Electroencephalography data
- `eeg_markers`: EEG event markers
- `lsl_events`: Lab Streaming Layer events
- `raw_events`: Raw task events
- `behav`: Behavioral data
- `ml`: MindLogger data
- `all`: Extract all available modalities

### Examples

#### Interactive Mode (GUI)

Run without arguments to open an interactive GUI for folder and modality selection:

```bash
conda activate xdf_proc
python extract_xdf.py
```

This will prompt you to:
1. Select the input folder containing XDF files
2. Select the output folder for processed data
3. Enter the task name
4. Choose which modalities to extract (checkbox interface)

#### Command-Line Examples

Extract a single task with default settings:

```bash
python extract_xdf.py -s /data/raw_xdf -t ravlt1 -d /data/processed
```

Extract specific modalities with parallel processing:

```bash
python extract_xdf.py -s /data/raw_xdf -t ravlt1 -d /data/processed \
    -m eyetracking,eeg,physio --max_workers 4
```

Extract all modalities from current directory:

```bash
python extract_xdf.py -s $(pwd) -t stroop -d $(pwd)/output -m all
```

### Performance Recommendations

- **Number of Workers**: The number of worker processes should be chosen carefully:
  - XDF files are large; too many workers can overwhelm your machine
  - Start with 2-4 workers on personal computers
  - Use 4-8 workers on dedicated servers
  - Monitor system resources during processing

- **Server Processing**: For large batch processing, run on CBIN servers (tank, tensor, roxy, etc.)

- **Speed**: For significantly faster processing (5-10x), consider using the Julia implementation

### Output Structure

The script creates the following output structure:

```
dest_folder/
├── task_name_modality1.csv
├── task_name_modality2.csv
├── task_name_modality3.csv
└── process_log.csv    # Log of processed files
```

Each output file is a CSV containing the extracted time-series data with timestamps and labeled columns.

### Process Logging

A `process_log.csv` file is created in the source folder tracking:

| Column | Description |
|--------|-------------|
| `xdf_file` | Filename of processed XDF |
| `success` | Whether processing succeeded (True/False) |
| `date_processed` | Timestamp of processing |

Already-processed files are skipped in subsequent runs, allowing safe re-execution.

## Module Structure

### `xdf_processing.py`

Core data extraction and processing functions:
- `process_xdf_file()`: Full processing pipeline
- `process_xdf_modalities()`: Process specific modalities

### `MobiXDF.py`

MoBI-specific utilities and helper functions.

### `extract_xdf.py`

Main entry point with CLI/GUI interface and parallel processing orchestration.

## Troubleshooting

### Permission Errors

If you see permission errors during processing:
```
PermissionError: Do you have permission to write to [path]?
```

**Solution**: Ensure you have write permissions to both source and destination folders:
```bash
chmod u+w /path/to/source /path/to/destination
```

### Memory Issues

If processing fails due to memory constraints:
- Reduce `--max_workers` (e.g., use 1 or 2)
- Process fewer files at a time
- Close other applications
- Consider using Julia implementation for better memory efficiency

### XDF File Issues

If an XDF file fails to process:
- Check the `process_log.csv` for error details
- Verify the task name is correct and case-sensitive
- Ensure the XDF file is not corrupted

## Contributing

Contributions are welcome! Areas for enhancement include:
- Additional modality-specific processing
- Improved signal filtering and preprocessing
- Feature extraction utilities
- Performance optimizations

Please open an issue or submit a pull request.

## Citation & Attribution

This processing toolkit was originally developed for the MoBILab at NKI CBIN. The underlying XDF parsing is built upon the pyxdf library.

For the Julia implementation, see [../xdf_jl/README.md](../xdf_jl/README.md), which is forked from the original [XDF.jl](https://github.com/cbrnr/XDF.jl) by Clemens Brunner.

## License

This project is licensed under the MIT License.

```
MIT License

Copyright 2023 Stan Colcombe

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
```

## Support

For issues, questions, or suggestions:
- Check existing issues on the GitHub repository
- Open a new issue with detailed description and error messages
- Include relevant file paths and command-line arguments used
