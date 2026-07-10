#!/usr/bin/env julia
# =============================================================================
# extract_xdf.jl — Command-line interface for the XDF_JL package
#
# Usage examples:
#   julia extract_xdf.jl -s /path/to/file.xdf.gz -d /path/to/dest -c physio,eeg
#   julia extract_xdf.jl -s /path/to/file.xdf.gz -d /path/to/dest -c lsl_events
#   julia extract_xdf.jl -s /path/to/recordings/ -d /path/to/dest -a -w 4
#
# Valid -c options:
#   eye         → Argus_Eye_Tracker or EyeLink          → _eyetrack.pqt
#   physio      → OpenSignals                           → _physio.pqt
#   eeg         → BrainVision RDA                       → _eeg.pqt
#   behav       → cpCST or MindLogger                   → _behav.csv
#   raw_events  → StimLabels (raw export)               → _events.csv
#   lsl_events  → StimLabels + sync-delay correction    → _events.csv
# =============================================================================

# ── Dependency bootstrap ──────────────────────────────────────────────────────
import Pkg

required  = ["ArgParse", "DataFrames", "CSV", "Parquet2", "EzXML", "CodecZlib"]
installed = keys(Pkg.project().dependencies)
to_install = filter(p -> p ∉ installed, required)
if !isempty(to_install)
    @info "Installing missing dependencies: $(join(to_install, ", "))"
    Pkg.add(to_install)
end

using ArgParse
using DataFrames
using CSV
using Parquet2
using EzXML
using Printf
using Distributed

# ── Include package files (expected in same directory as this script) ──────────
const SCRIPT_DIR = @__DIR__

include(joinpath(SCRIPT_DIR, "XDF_JL.jl"))

# Reference submodule functions directly via fully-qualified paths.
# using .XDF_JL is unreliable here because XDF_JL assigns functions as
# variable bindings rather than defining them, which breaks re-export.
const read_xdf               = XDF_JL.XDF.read_xdf
const get_channel_timeseries = XDF_JL.XDF_proc.get_channel_timeseries
const get_all_timeseries     = XDF_JL.XDF_proc.get_all_timeseries
const xdf_channels           = XDF_JL.XDF_proc.channels

# =============================================================================
# Stream name mapping
# Each logical option maps to a tuple of (candidate stream names, output suffix,
# output format).  The first candidate found in the XDF wins.
# =============================================================================

const STREAM_MAP = Dict(
    "eye"        => (["Argus_Eye_Tracker", "EyeLink"],          "eyetrack", :pqt),
    "physio"     => (["OpenSignals"],                            "physio",   :pqt),
    "eeg"        => (["BrainVision RDA"],                        "eeg",      :pqt),
    "behav"      => (["cpCST", "MindLogger"],                    "behav",    :csv),
    "raw_events" => (["StimLabels"],                             "events",   :csv),
    "lsl_events" => (["StimLabels"],                             "events",   :csv),
)

const VALID_OPTIONS = collect(keys(STREAM_MAP))

# Sync-delay fallback order for lsl_events (Audio / Video skipped for now,
# entries kept as placeholders so the logic is easy to extend later)
const SYNC_FALLBACKS = ["Audio"]  # extend with "FaceVideo" etc. when ready

# =============================================================================
# BIDS filename helpers
# =============================================================================

"""Strip _lsl suffix and .xdf/.xdf.gz extension → bare BIDS stem."""
function bids_stem(src_path::String)::String
    name = basename(src_path)
    name = endswith(name, ".gz")  ? name[1:end-3] : name
    name = endswith(name, ".xdf") ? name[1:end-4] : name
    name = replace(name, r"_lsl$"i => "")
    return name
end

"""Build the output filename from stem, suffix, and format symbol."""
function bids_filename(stem::String, suffix::String, fmt::Symbol)::String
    ext = fmt === :pqt ? ".pqt" : ".csv"
    return "$(stem)_$(suffix)$(ext)"
end

# =============================================================================
# Footer XML parsing  (mirrors how the header is parsed in XDF_proc.jl)
# =============================================================================

"""
Extract get_sync_delay equivalent from a stream dictionary.
Reads the first clock-offset time from the footer XML and subtracts
the stream's first timestamp, replicating the Python get_sync_delay logic.
Returns NaN on any failure.
"""
function get_sync_delay(stream::Dict)::Float64
    try
        footer_xml = stream["footer"]
        xml = EzXML.parsexml(footer_xml)

        # XPath targets:
        #   <clock_offsets><offset><time>…</time></offset></clock_offsets>
        time_nodes = EzXML.findall("//clock_offsets/offset/time", xml)
        isempty(time_nodes) && return NaN

        lsl_sync = parse(Float64, strip(EzXML.nodecontent(time_nodes[1])))

        fts_nodes = EzXML.findall("//first_timestamp", xml)
        isempty(fts_nodes) && return NaN

        fts = parse(Float64, strip(EzXML.nodecontent(fts_nodes[1])))

        return lsl_sync - fts
    catch
        return NaN
    end
end

# =============================================================================
# LSL events processing
# =============================================================================

"""Convert total seconds → "HH:MM:SS.mmm" string."""
function sec_to_hhmmss(s::Float64)::String
    s   = max(s, 0.0)
    h   = floor(Int, s / 3600)
    m   = floor(Int, (s % 3600) / 60)
    sec = s % 60
    return @sprintf("%02d:%02d:%06.3f", h, m, sec)
end

"""
Apply the sync-delay correction to a raw StimLabels DataFrame.
Mirrors the Python lsl_events logic:
  1. Compute stim_ext = sync_delay(StimLabels stream)
  2. Compute delay_ext from fallback streams (Audio, …) until non-NaN
  3. shift_ext = |stim_ext - delay_ext|
  4. ext_time  = time_sec + shift_ext
  5. hh_mm_ss  = sec_to_hhmmss(ext_time)
  6. Return only the required columns (those that exist in the DataFrame)
"""
function apply_lsl_sync(events::DataFrame, xdf_dict::Dict,
                         stim_stream::Dict)::DataFrame

    stim_ext  = get_sync_delay(stim_stream)
    delay_ext = NaN

    avail = xdf_channels(xdf_dict)

    for fallback in SYNC_FALLBACKS
        haskey(avail, fallback) || continue
        delay_ext = get_sync_delay(xdf_dict[avail[fallback]])
        isnan(delay_ext) || break
    end

    if isnan(delay_ext)
        @warn "No valid sync delay found — ext_time will equal time_sec."
        shift_ext = 0.0
    else
        shift_ext = abs(stim_ext - delay_ext)
    end

    events[!, "ext_time"] = events[!, "time_sec"] .+ shift_ext
    events[!, "hh_mm_ss"] = sec_to_hhmmss.(events[!, "ext_time"])

    # Select only the columns that are present (guards against missing cols)
    desired = ["StimMarkers_alpha", "timestamps", "lsl_timestamp",
               "ext_time", "hh_mm_ss"]
    present = filter(c -> c ∈ names(events), desired)
    return events[!, present]
end

# =============================================================================
# Save helper
# =============================================================================

function save_df(df::DataFrame, dest_dir::String, filename::String,
                  label::String, fmt::Symbol)
    mkpath(dest_dir)
    if nrow(df) == 0
        @warn "  Skipping '$label' — DataFrame is empty."
        return
    end
    out_path = joinpath(dest_dir, filename)
    if fmt === :pqt
        Parquet2.writefile(out_path, df)
        @info "  Saved parquet → $out_path"
    else
        CSV.write(out_path, df)
        @info "  Saved CSV     → $out_path"
    end
end

# =============================================================================
# Core file processor
# =============================================================================

"""
Process a single XDF file for one logical option (e.g. "eeg", "lsl_events").
Finds the first matching stream candidate, extracts, optionally transforms,
and saves with the correct BIDS-style filename.
"""
function process_option(xdf_dict::Dict, option::String,
                         src_path::String, dest_dir::String)

    candidates, suffix, fmt = STREAM_MAP[option]
    avail = xdf_channels(xdf_dict)  # Dict{String,Int}

    # Find the first candidate stream that exists in this file
    stream_name = nothing
    for c in candidates
        haskey(avail, c) && (stream_name = c; break)
    end

    if isnothing(stream_name)
        @warn "  [$option] None of $(candidates) found in $(basename(src_path)). Skipping."
        return
    end

    @info "  [$option] Using stream '$stream_name'"

    df = get_channel_timeseries(xdf_dict, stream_name)

    # lsl_events needs extra processing
    if option == "lsl_events"
        stream_idx = avail[stream_name]
        stim_stream = xdf_dict[stream_idx]
        df = apply_lsl_sync(df, xdf_dict, stim_stream)
    end

    stem  = bids_stem(src_path)
    fname = bids_filename(stem, suffix, fmt)
    save_df(df, dest_dir, fname, stream_name, fmt)
end

"""
Process a single XDF file across all requested options.
"""
function process_file(src_path::String, dest_dir::String,
                       options::Vector{String})
    @info "Processing: $src_path"

    local xdf_dict
    try
        xdf_dict = read_xdf(src_path)
    catch e
        @error "Failed to read '$src_path': $e"
        return
    end

    for opt in options
        try
            process_option(xdf_dict, opt, src_path, dest_dir)
        catch e
            @error "  [$opt] Failed: $e"
        end
    end
end

# =============================================================================
# Source file resolution
# =============================================================================

is_xdf(name::String) = endswith(name, ".xdf") || endswith(name, ".xdf.gz")

"""
Convert a shell-style glob string (with * wildcards anywhere in the path)
into a Regex that matches a full absolute path.
* matches any characters including path separators, so sub-* will match
sub-M10999168/cpCST/lsl/sub-M10999168... as expected.
"""
function glob_to_regex(pattern::String)::Regex
    # Escape all regex metacharacters except *, then replace * with .*
    escaped = replace(pattern, r"[.+^${}()|[\]\\]" => s -> "\\" * s)
    regstr  = replace(escaped, "*" => ".*")
    return Regex("^" * regstr * "\$")
end

"""
Find the deepest leading path component that contains no wildcard,
so we know where to start walking the filesystem.
"""
function glob_root(pattern::String)::String
    parts = splitpath(pattern)
    root_parts = String[]
    for p in parts
        occursin("*", p) && break
        push!(root_parts, p)
    end
    isempty(root_parts) && return "/"
    return joinpath(root_parts...)
end

function resolve_sources(source::String)::Vector{String}
    # Direct file — no wildcards
    if isfile(source) && is_xdf(source)
        return [source]
    end

    # Plain directory (no wildcards) → recurse for all XDF files
    if isdir(source)
        found = String[]
        for (root, _, files) in walkdir(source)
            for f in files
                is_xdf(f) && push!(found, joinpath(root, f))
            end
        end
        isempty(found) && @warn "No .xdf/.xdf.gz files found in: $source"
        return found
    end

    # Glob pattern — wildcards may appear anywhere in the path
    if occursin("*", source)
        # Resolve relative paths against cwd so regex matching works
        abs_pattern = isabspath(source) ? source : abspath(source)
        pat_re      = glob_to_regex(abs_pattern)
        walk_root   = glob_root(abs_pattern)

        isdir(walk_root) || error("Base directory for glob does not exist: $walk_root")

        found = String[]
        for (root, _, files) in walkdir(walk_root)
            for f in files
                if is_xdf(f)
                    full = joinpath(root, f)
                    occursin(pat_re, full) && push!(found, full)
                end
            end
        end
        isempty(found) && @warn "No XDF files matched pattern: $source"
        return found
    end

    error("Source path does not exist and is not a valid glob pattern: $source")
end

# =============================================================================
# Argument parsing
# =============================================================================

function parse_args_cli()
    s = ArgParseSettings(
        prog        = "extract_xdf.jl",
        description = "Extract and export timeseries data from XDF files.",
        epilog      = """
Valid -c options (comma-separated):
  eye         → Argus_Eye_Tracker or EyeLink       → <stem>_eyetrack.pqt
  physio      → OpenSignals                         → <stem>_physio.pqt
  eeg         → BrainVision RDA                     → <stem>_eeg.pqt
  behav       → cpCST or MindLogger                 → <stem>_behav.csv
  raw_events  → StimLabels (raw)                    → <stem>_events.csv
  lsl_events  → StimLabels + sync correction        → <stem>_events.csv

Examples:
  julia extract_xdf.jl -s recording.xdf.gz -d ./out -c physio,eeg,lsl_events
  julia extract_xdf.jl -s /data/session1/  -d ./out -a -w 4
""",
    )

    @add_arg_table! s begin
        "--source", "-s"
            help     = "XDF file, directory, or glob pattern."
            required = true
            arg_type = String

        "--dest", "-d"
            help     = "Destination directory for output files."
            required = true
            arg_type = String

        "--channels", "-c"
            help     = "Comma-separated extraction options: $(join(VALID_OPTIONS, ", "))"
            default  = ""
            arg_type = String

        "--all", "-a"
            help     = "Extract all supported channel types."
            action   = :store_true

        "--workers", "-w"
            help     = "Number of parallel workers (default: 1)."
            default  = 1
            arg_type = Int
    end

    return parse_args(s)
end

# =============================================================================
# Entry point
# =============================================================================

function main()
    args     = parse_args_cli()
    source   = args["source"]
    dest     = args["dest"]
    all_flag = args["all"]
    ch_arg   = args["channels"]
    nworkers = args["workers"]

    # Validate and resolve options
    if !all_flag && isempty(ch_arg)
        println(stderr, "ERROR: specify either --all (-a) or --channels (-c) <option1,option2,...>")
        println(stderr, "Valid options: $(join(VALID_OPTIONS, ", "))")
        exit(1)
    end
    if all_flag && !isempty(ch_arg)
        @warn "--all and --channels both specified; --all takes precedence."
    end

    options = if all_flag
        VALID_OPTIONS
    else
        requested = String.(strip.(split(ch_arg, ",")))
        invalid   = filter(o -> o ∉ VALID_OPTIONS, requested)
        if !isempty(invalid)
            println(stderr, "ERROR: unrecognised option(s): $(join(invalid, ", "))")
            println(stderr, "Valid options: $(join(VALID_OPTIONS, ", "))")
            exit(1)
        end
        # raw_events and lsl_events are mutually exclusive — lsl_events wins
        if "lsl_events" ∈ requested && "raw_events" ∈ requested
            @warn "Both raw_events and lsl_events requested — raw_events will be skipped."
            filter(o -> o != "raw_events", requested)
        else
            requested
        end
    end

    # Resolve source files
    src_files = resolve_sources(source)
    isempty(src_files) && (println(stderr, "ERROR: no XDF files found."); exit(1))

    @info "Found $(length(src_files)) XDF file(s). Options: $(join(options, ", ")). Destination: $dest"


    # Parallel or serial
    if nworkers > 1
        needed = nworkers - nprocs()
        needed > 0 && addprocs(needed)

        # Load the entire script on each worker so all functions are defined there.
        # We skip main() execution by setting a guard flag before including.
        script_path = joinpath(SCRIPT_DIR, "extract_xdf.jl")
        for pid in workers()
            remotecall_fetch(pid) do
                # Guard so main() doesn't run recursively on the worker
                Core.eval(Main, :(const _WORKER_MODE = true))
                include(script_path)
                nothing
            end
        end

        @info "Running in parallel with $(length(workers())) worker(s)."
        # Use fetch+@spawnat to call process_file by name on each worker,
        # avoiding closure serialization issues entirely.
        @sync for (i, f) in enumerate(src_files)
            pid = workers()[(i - 1) % length(workers()) + 1]
            @async fetch(@spawnat pid process_file(f, dest, options))
        end
    else
        for f in src_files
            process_file(f, dest, options)
        end
    end

    @info "Done."
end

# Guard: don't run main() when this script is loaded on a worker
if !@isdefined(_WORKER_MODE)
    main()
end
