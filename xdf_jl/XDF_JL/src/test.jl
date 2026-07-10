### A Pluto.jl notebook ###
# v0.19.38

using Markdown
using InteractiveUtils

# ╔═╡ b858c054-0c3a-11f1-3333-f98109616502
begin
    using Pkg
    Pkg.activate()
    Pkg.develop(path="/Users/danielgarcia-barnett/Desktop/xdf_jl/XDF_JL")
    using XDF_JL
end

# ╔═╡ a0b400e7-762a-4fea-9dec-c53d48006f65
begin
    run_1 = "/Users/danielgarcia-barnett/Desktop/xdf/xdf_jl/XDF_JL/src/sub-M10999168_ses-MOBI2B_task-cstLITE_run-001_lsl.xdf.gz"
    run_1_dict = read_xdf(run_1)
	run_1_data = get_all_timeseries(run_1_dict)
end

# ╔═╡ 4ba86034-eebe-4964-899c-038139052b0d
keys(run_1_data)

# ╔═╡ 1f3702de-7e18-4851-8356-c8adb558e0da
run_1_data["StimLabels"]

# ╔═╡ Cell order:
# ╠═b858c054-0c3a-11f1-3333-f98109616502
# ╠═a0b400e7-762a-4fea-9dec-c53d48006f65
# ╠═4ba86034-eebe-4964-899c-038139052b0d
# ╠═1f3702de-7e18-4851-8356-c8adb558e0da
