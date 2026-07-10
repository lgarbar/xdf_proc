module XDF_JL

# Include submodules
include("XDF.jl")
include("XDF_proc.jl")

# Load submodules
using .XDF
using .XDF_proc

# Re-export functions to be available at top-level of this module
export read_xdf, get_channel_timeseries, get_all_timeseries

# Assign top-level bindings to submodule functions
read_xdf = XDF.read_xdf
get_channel_timeseries = XDF_proc.get_channel_timeseries
get_all_timeseries = XDF_proc.get_all_timeseries

end