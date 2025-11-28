# XDF.jl - Julia XDF Processing

A high-performance Julia implementation for reading and processing XDF (Extensible Data Format) files. This package provides 5-10x faster processing compared to Python implementations.

## Overview

XDF.jl is a Julia package designed to efficiently parse XDF files and provide convenient data processing utilities. It features:

- **Fast XDF Parsing**: Optimized binary reading and data parsing
- **Multi-Modal Support**: Handles numeric data types (int8, int16, int32, int64, float32, float64) and string data
- **Time Series Tools**: Extract and process time series data from XDF streams with automatic channel labeling
- **Clock Synchronization**: Automatic synchronization of clock offsets across streams

## Citation & Attribution

**This package is forked from the original [XDF.jl](https://github.com/cbrnr/XDF.jl) by Clemens Brunner**, licensed under the BSD 3-clause license.

**Key Enhancement**: This version has been modified to properly parse and handle string-type data in XDF files. The original implementation could not process channels containing string data; this version fully supports string arrays alongside numeric data types.

## Performance

Julia implementation provides **5-10x speed improvements** over Python implementations, making it ideal for:
- Processing large numbers of XDF files
- Real-time data streaming applications
- Large-scale batch processing workflows

## Installation

### Option 1: Add as a Package to Your Julia Environment

1. In your Julia REPL, enter the package manager mode by pressing `]`:
   ```julia
   julia> ]
   ```

2. Add the package from the repository. If the package is available on GitHub:
   ```julia
   pkg> add https://github.com/lgarbar/xdf_proc.git#main
   ```

   Or, if you have a local copy:
   ```julia
   pkg> add /path/to/xdf_jl/XDF_JL
   ```

3. Exit the package manager (press backspace) and the package will be available in your Julia environment:
   ```julia
   julia> using XDF_JL
   ```

### Option 2: Create as a Standalone Package

To create XDF_JL as a reusable standalone package for your Julia installations:

1. **Copy the package to Julia's default package location**:
   ```bash
   mkdir -p ~/.julia/dev
   cp -r /path/to/xdf_jl/XDF_JL ~/.julia/dev/XDF_JL
   ```

2. **Or, set up a development link** in your Julia REPL:
   ```julia
   julia> ]
   pkg> dev /path/to/xdf_jl/XDF_JL
   ```

3. Once added to the registry or development packages, you can use it:
   ```julia
   using XDF_JL
   ```

### Manual Installation (Without Package Management)

If you prefer to use the code without formal package installation:

1. Include the modules directly in your Julia script:
   ```julia
   include("/path/to/xdf_jl/XDF_JL/src/XDF.jl")
   include("/path/to/xdf_jl/XDF_JL/src/XDF_proc.jl")
   using .XDF
   using .XDF_proc
   ```

## Usage

### Reading XDF Files

```julia
using XDF_JL

# Read an XDF file with automatic clock synchronization (default)
xdf_data = read_xdf("data.xdf")

# Read an XDF file without clock synchronization
xdf_data = read_xdf("data.xdf", sync=false)

# Read a gzip-compressed XDF file
xdf_data = read_xdf("data.xdf.gz")
```

### Processing Time Series Data

The `XDF_proc` module provides convenient functions for extracting and formatting time-series data:

```julia
using XDF_JL, DataFrames

# Read XDF file
xdf_data = read_xdf("data.xdf")

# Get available channel names
channel_info = channels(xdf_data)
# Returns: Dict{String, Int} with channel names mapped to stream IDs

# Extract a specific channel as a DataFrame
# The resulting DataFrame includes time columns and channel data with proper labels
df = get_channel_timeseries(xdf_data, "EEG")

# The DataFrame includes three time representations:
# - lsl_timestamp: original LSL timestamps
# - time_sec: time in seconds since first sample
# - time_ms: time in milliseconds since first sample
# Plus labeled columns for each channel

# Extract all channels as a dictionary of DataFrames
all_timeseries = get_all_timeseries(xdf_data)
```

### Data Structure

After reading an XDF file, the data is returned as a dictionary where:
- Keys are stream IDs (integers)
- Values are dictionaries containing:
  - `"name"`: Stream name (string)
  - `"type"`: Stream type (string)
  - `"nchannels"`: Number of channels (integer)
  - `"srate"`: Sampling rate (float)
  - `"dtype"`: Data type of the stream
  - `"data"`: Array of channel data (size: samples × channels)
  - `"time"`: Array of timestamps for each sample
  - `"header"`: XML metadata string
  - `"footer"`: XML footer metadata (if present)

## Dependencies

- **CodecZlib**: For reading gzip-compressed XDF files
- **DataFrames**: For convenient time-series data formatting
- **EzXML**: For parsing XML metadata in stream headers

These are automatically installed when adding the package.

## Current Capabilities

The XDF_proc module currently includes:

- `read_xdf()`: Parse XDF files with optional clock synchronization
- `channels()`: List all available channels in the data
- `get_channel_timeseries()`: Extract a single channel as a formatted DataFrame
- `get_all_timeseries()`: Extract all channels as DataFrames

## Future Development

The Julia implementation is being actively developed to include all functionality from the Python processing pipeline. Planned features include:
- Modality-specific processing functions
- Advanced signal processing utilities
- Feature extraction capabilities
- Integration with signal analysis libraries

## Examples

### Complete Workflow Example

```julia
using XDF_JL, DataFrames, Plots

# Read the XDF file
xdf_data = read_xdf("experiment.xdf")

# Get all timeseries data
all_data = get_all_timeseries(xdf_data)

# Work with a specific modality
physio_df = all_data["Physio"]

# Plot time-series data
plot(physio_df.time_sec, physio_df.[:, 2:end], 
     label="", xlabel="Time (s)", ylabel="Signal")
```

### Batch Processing Multiple Files

```julia
using XDF_JL, Glob

# Process all XDF files in a directory
xdf_files = glob("*.xdf", "data_directory")

for file in xdf_files
    try
        xdf_data = read_xdf(file)
        all_data = get_all_timeseries(xdf_data)
        # Process your data here
        println("Processed: $file")
    catch e
        println("Error processing $file: $e")
    end
end
```

## License

This project is licensed under the BSD 3-clause license, maintaining compatibility with the original XDF.jl project.

## Contributing

Contributions are welcome! Areas for contribution include:
- Additional processing functions
- Performance optimizations
- Documentation improvements
- Bug reports and fixes

Please open an issue or submit a pull request to contribute.
