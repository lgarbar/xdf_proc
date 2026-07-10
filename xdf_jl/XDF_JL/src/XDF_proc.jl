module XDF_proc

using DataFrames
using EzXML


function channels(xdf_dict::Dict)
    channel_dict = Dict{String, Int}()
    for (stream_key, stream_dict) in xdf_dict
        channel_dict[stream_dict["name"]] = stream_key
    end
    return channel_dict
end

function get_channel_timeseries(xdf_dict::Dict, channel::String)
    channel_idx = channels(xdf_dict)[channel]
    stream = xdf_dict[channel_idx]

    if !haskey(stream, "time") || !haskey(stream, "data")
        error("Stream dictionary missing required keys: 'time' and 'data'")
    end

    times = stream["time"]
    data = stream["data"]

    if isa(data, AbstractMatrix)
        nchannels = size(data, 2)
        df = DataFrame(time = times)
        for ch in 1:nchannels
            colname = Symbol("ch$(ch)")
            df[!, colname] = vec(data[:, ch])
        end
    elseif isa(data, AbstractVector)
        df = DataFrame(time = times, data = data)
    else
        error("Unexpected data format: $(typeof(data))")
    end

    labels = String[]
    if haskey(stream, "header")
        xml = EzXML.parsexml(stream["header"])
        for ch in EzXML.findall("//channel/label", xml)
            push!(labels, EzXML.nodecontent(ch))
        end
    end

    rename!(df, :time => :lsl_timestamp)
    channel_cols = filter(c -> String(c) != "lsl_timestamp", names(df))
    labels_to_use = length(labels) > length(channel_cols) ? labels[1:length(channel_cols)] :
                    length(labels) < length(channel_cols) ? vcat(labels, ["ch_$(i)" for i in (length(labels)+1):length(channel_cols)]) :
                    labels
    rename_pairs = Pair.(channel_cols, Symbol.(labels_to_use))
    rename!(df, rename_pairs...)

    # === Early return for empty streams ===
    if nrow(df) == 0
        @warn "Channel '$channel' has no data — returning empty DataFrame."
        df[!, "time_sec"] = Float64[]
        df[!, "time_ms"]  = Float64[]
        return df
    end

    df[!, "time_sec"] = round.(df[!, "lsl_timestamp"] .- df[!, "lsl_timestamp"][1], digits=6)
    df[!, "time_ms"]  = round.(df[!, "lsl_timestamp"] .* 1000 .- df[!, "lsl_timestamp"][1] * 1000, digits=6)

    return df
end

function get_all_timeseries(xdf_dict::Dict)
    ts_dict = Dict{String, DataFrame}()
    for (channel_name, channel_idx) in channels(xdf_dict)
        ts_dict[channel_name] = get_channel_timeseries(xdf_dict, channel_name)
    end
    return ts_dict
end

# -------------------------------
# Auto-export all functions
# -------------------------------
for name in names(@__MODULE__, all=true, imported=false)
    if !startswith(String(name), "_") && isa(getfield(@__MODULE__, name), Function)
        @eval export $(name)
    end
end
		
end # module XDF_proc