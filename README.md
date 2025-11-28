# XDF Processing Toolkit

A comprehensive toolkit for processing XDF (Extensible Data Format) files with both Python and Julia implementations. This project provides efficient data extraction and processing capabilities for XDF files collected in neuroscience and behavioral research settings.

## Overview

XDF is a file format designed to store multi-modal time-series data, commonly used in brain-computer interface (BCI) research and neuroscience experiments. This toolkit offers two complementary implementations:

- **Python**: A full-featured extraction and processing pipeline with GUI support
- **Julia**: A high-performance implementation with 5-10x speed improvements over Python

## Key Features

- **Fast XDF Parsing**: Efficient reading of XDF files with support for multiple data types including numeric and string data
- **Multi-Modal Data Extraction**: Extract eyetracking, audio, physio, EEG, and other modalities from XDF files
- **Time-Series Processing**: Automatic channel labeling, time alignment, and DataFrame formatting
- **Flexible API**: Both command-line and programmatic interfaces available
- **Parallel Processing**: Process multiple XDF files concurrently (Python implementation)

## Performance

The Julia implementation provides **5-10x faster processing** compared to the Python implementation, making it ideal for large-scale data processing workflows.

## Project Structure

```
xdf/
├── xdf_py/                 # Python implementation
│   ├── extract_xdf.py      # Main extraction script with GUI
│   ├── requirements.yml    # Conda environment specification
│   └── xdf_proc/           # Processing module
│       ├── MobiXDF.py      # MoBI-specific utilities
│       └── xdf_processing.py # Core processing functions
│
└── xdf_jl/                 # Julia implementation
    └── XDF_JL/             # Julia package
        ├── Project.toml    # Package dependencies
        └── src/
            ├── XDF.jl      # Core XDF parsing
            └── XDF_proc.jl # Processing utilities
```

## Getting Started

### Using Python

For detailed Python setup and usage instructions, see [xdf_py/README.md](xdf_py/README.md).

### Using Julia

For Julia package setup and usage instructions, see [xdf_jl/README.md](xdf_jl/README.md).

## Citation & Attribution

**Important**: This project is forked from the original [XDF.jl](https://github.com/cbrnr/XDF.jl) repository by Clemens Brunner. The original implementation has been enhanced to properly handle string data types in XDF files, which the original version could not parse.

**Key modification**: Added support for parsing string-type channels in XDF files, enabling processing of text-based data streams that previously caused errors.

## License

This project is licensed under the MIT License. See individual README files for more details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## Roadmap

The Julia implementation is being actively developed to include all functionality from the Python processing pipeline. Key planned features include expanded modality-specific processing functions to match the full Python workflow.
