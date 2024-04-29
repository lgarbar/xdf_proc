# MoBI XDF Processing

This app is designed to process a series of XDF files collected in NKI's CBIN MoBILab.

## Installation

Download the latest version of of the code (*.zip file or pull from git repository), and put it somewhere convenient (e.g. ~/python)

### The project has few dependencies

- python>=3.10
- pyxdf
- pip
- pip:
  - biosppy

To install the necessary dependencies for this application, you can install them yourself through the command line. Or, you can create a conda environment using the `conda_config.yml` file in the project directory.

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) or [Mamba](https://mamba.readthedocs.io/en/latest/installation.html) if you haven't already. If on the linux-based server, you can run:
```bash
mkdir -p ~/miniconda3
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ~/miniconda3/miniconda.sh
bash ~/miniconda3/miniconda.sh -b -u -p ~/miniconda3
rm -rf ~/miniconda3/miniconda.sh
~/miniconda3/bin/conda init bash
~/miniconda3/bin/conda init zsh
```

2. Open a terminal and navigate to the directory containing the `conda_config.yml` file.

3. Run the following command to create the conda environment:

4. Activate the newly created environment:

``` bash
conda activate xdf_proc
```

## Usage

``` bash
usage: extract_xdf.py [-h] [--max_workers MAX_WORKERS] source_folder task_name dest_folder

optional arguments:
  [-s] source_folder         full path to folder containing xdf files
  [-t] task_name             task name (e.g. ravlt1). note: the task name is case sensitive
  [-d] dest_folder           full path to folder to xdf derivatives
  
  If the parameters above are not input, a gui will open up to navigate your file system to select a source and destination folder, as well as type in the task name.

options:
  -h, --help            show this help message and exit
  -w, --max_workers MAX_WORKERS
                        maximum number of workers. default is 4
```

### e.g

``` bash
python ~/python/mobi-xdf_extract/extract_xdf.py -s `pwd` -t ravlt1 -d `pwd`/output --max_workers 2
```

The above will extract eyetracking, physio, task events, audio, etc. from the "ravlt1" task xdf files in the current working directory, and save the output to a folder named "output" in the current working directory. The code will use 2 worker processes (two independent processes) in parallel to process the ravlt1 files.
If the 'output' folder does not exist, it will be created.
*note:* Take care with the number of worker processes spawned. The XDF files are large and can easily overwhelm your local machine. If you are not just testing, run on a CBIN server (tank, tensor, roxy, etc.).

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## License

This project is licensed under the terms of the MIT license.
Copyright 2023 Stan Colcombe stans iphone at gmail com

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE
