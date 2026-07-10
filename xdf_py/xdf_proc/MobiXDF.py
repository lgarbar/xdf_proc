import numpy as np
import pandas as pd
import pyxdf
import datetime as dt
import sys
from os import path
import biosppy as bp

# Constants
TIMESTAMPS = "timestamps"
TIME_MS = "time_ms"
TIME_SEC = "time_sec"
MS_FACTOR = 1000


zscale = lambda x: (x - x.mean()) / x.std()
ursi = lambda x: x.split("/")[-1].split("_")[0].split("-")[-1]

sys.path.append(path.expanduser("~/python"))

class MobiXDF(object):
    """Class to handle MobiXDF data."""
    def __init__(self, filename: str, load_on_create: bool = True):
        self.filename = filename
        self.base = filename.split("/")[-1].split(".")[0]
        if load_on_create:
            self.load_xdf(self.filename)

    def load_xdf(self, filename: str):
        self.data, self.header = pyxdf.load_xdf(filename)

    def _get_channel_idx(self, channel_name: str) -> int:
        ch = -1
        for k, d in enumerate(self.data):
            if channel_name in d["info"]["name"]:
                return k
        return ch

    def channels(self) -> list:
        """
        Returns a list of channel names from all data streams.
        Each element is the channel name as a string.
        """
        channels = [d["info"]["name"] for d in self.data]
        return channels

    def events_channel(self) -> int:
        ch = -1
        for k, d in enumerate(self.data):
            if "StimLabels" in d["info"]["name"]:
                return k
        return ch

    def channel_labels(self, idx):
        channels = self.data[idx]["info"]["desc"][0]["channels"][0]["channel"]
        labels = [c["label"][0] for c in channels]
        return labels

    def get_channel_timeseries(self, channel_name: str) -> pd.DataFrame:
        """
        Returns a pandas dataframe of the raw timeseries for a given channel
        Note that the channel may contain multiple signals
        :param channel_name: string denoting the name of the channel
        :return: pandas dataframe
        """
        try:
            idx = self._get_channel_idx(channel_name)
            series = self.data[idx]["time_series"]
            try:
                channels = self.data[idx]["info"]["desc"][0]["channels"][0]["channel"]
            except:
                channels = [{'label': [channel_name.replace(' ', '_')], 'unit': ['none'], 'type': [channel_name.replace(' ', '_')]}]
            # return(channels)
            time_ms = self.data[idx]["time_stamps"] - self.data[idx]["time_stamps"][0]
            labels = [c["label"][0] for c in channels]
            series = self.data[idx]["time_series"]
            time_sec = self.data[idx]["time_stamps"] - self.data[idx]["time_stamps"][0]
            time_ms = time_sec * 1000
            time_ms = np.round(time_ms, 4)
            pDF = pd.DataFrame(columns=labels, data=series)
            pDF["timestamps"] = self.data[idx]["time_stamps"]
            pDF["time_ms"] = time_ms
            pDF["time_sec"] = time_sec
            # First LSL stamp is stored in footer for some reason.
            # TODO: Check on the source code saving the event data for veridicality
            if channel_name == "StimLabels" or "Argus_Eye_Tracker" or "Eyelink":
                first_lsl = float(self.data[idx]['footer']['info']['clock_offsets'][0]["offset"][0]["time"][0])
                lsl_timestamp = time_sec + first_lsl
                pDF["lsl_timestamp"] = lsl_timestamp

            return pDF
        
        except Exception as e:
            print(f"Error getting channel timeseries: {e}")
            return []

def abs_motion_change(dat: pd.DataFrame, show: bool = False) -> np.array:
    """ Computes absolute motion change for motion data."""
    avec = [c for c in dat.columns if "XYZ" in c]
    vals = np.zeros(dat.XYZ5.values.shape)
    for v in avec:
        vals += np.abs(np.gradient(zscale(dat[v].values)))

    return {"filtered": vals}


def find_closest(val, in_list) -> dict:
    """
    parameters:
        val:     target numeric value to find in list/array
        in_list: a list/array of numeric values
    returns:
        closest: dict
            'value':    value closest to target within in_list
            'location': index of that value within in_list
    """
    closest = {}
    loc = (np.abs(np.asarray(in_list) - val)).argmin()
    val = in_list[loc]
    closest["value"] = val
    closest["location"] = loc
    return closest


def physio_channel(dat: list) -> int:
    """Which one was the physio channel?"""
    physio = -1
    for k, d in enumerate(dat):
        if "OpenSignals" in d["info"]["name"]:
            return k
    return physio


def events_channel(dat: list) -> int:
    """Which one was the events channel?"""
    physio = -1
    for k, d in enumerate(dat):
        if "StimLabels" in d["info"]["name"]:
            return k
    return physio


def extract_physio(data: list) -> pd.DataFrame:
    """Extract physio channel data and return a dataframe"""
    phys_ch = physio_channel(data)
    if phys_ch < 0:
        return -1
    channels = data[phys_ch]["info"]["desc"][0]["channels"][0]["channel"]
    labels = [c["label"][0] for c in channels]
    series = data[phys_ch]["time_series"]
    time_ms = data[phys_ch]["time_stamps"] - data[phys_ch]["time_stamps"][0]
    time_ms *= 1000
    time_ms = np.round(time_ms, 2)
    pDF = pd.DataFrame(columns=labels, data=series)
    pDF["timestamps"] = data[phys_ch]["time_stamps"]
    pDF["time_ms"] = time_ms
    pDF["time_sec"] = time_ms / 1000
    return pDF


def get_events(data: list) -> pd.DataFrame:
    res = 0
    try:
        events_ch = events_channel(data)
        labels = [d[0] for d in data[events_ch]["time_series"]]
        res = pd.DataFrame()
        res["event"] = labels
        res["timestamps"] = data[events_ch]["time_stamps"]
        return res
    except:
        return res

def task_name(filpath: str) -> str:
    fname = filpath.split("/")[-1].split(".")[0]
    return fname


def get_physio_locs(events: pd.DataFrame, data: list) -> pd.DataFrame:
    physio_ch = physio_channel(data)
    timestamps = data[physio_ch]["time_stamps"]
    EV = events.copy()
    EV["phys_locs"] = np.nan
    for k, row in EV.iterrows():
        dct = find_closest(row.timestamps, timestamps)
        EV["phys_locs"][k] = dct["location"]
    EV = EV.astype({"phys_locs": "int64"})
    return EV


def send_to_log(msg: str):
    with open(f"physio_proc.log", "a") as f:
        f.write(f"{msg}\n")


def nowstr() -> str:
    ns = dt.datetime.now().strftime("%D@%H:%M:%S")
    return ns


def save_physio(df: pd.DataFrame, outpath: str) -> bool:
    """Saves the physio data to a file."""
    if isinstance(df, pd.DataFrame):
        df.to_parquet(outpath, index=False)
        send_to_log(f"     saved {outpath}\n    at time:{nowstr()}\n")
        return True
    else:
        msg = f"No Physio!"
        print(msg)
        send_to_log(f"{msg}; {nowstr()}\n")
        return False


def save_events(evs: pd.DataFrame, outpath: str) -> bool:
    success = False
    if type(evs) is pd.DataFrame:
        evs.to_csv(outpath, index=False)
        success = True
    else:
        msg = f"Saving events failed for: {outpath}"
        print(msg)
        send_to_log(f"{msg}; {nowstr()}\n")
    return success


def filtered_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_physio.pqt"
    outpath = path.join(outfldr, fname)
    return outpath


def physio_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_physio.pqt"
    outpath = path.join(outfldr, fname)
    return outpath

def audio_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_audio.wav"
    outpath = path.join(outfldr, fname)
    return outpath

def event_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_events.csv"
    outpath = path.join(outfldr, fname)
    return outpath

def raw_event_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_raw_events.csv"
    outpath = path.join(outfldr, fname)
    return outpath

def preproc_physio_df(phys: pd.DataFrame) -> pd.DataFrame:
    keep_cols = ["nSeq", "timestamps", "time_ms", "time_sec"]
    if "lsl_timestamp" in phys.columns:
        keep_cols.append("lsl_timestamp")
    
    proc_map = {}
    try:
        if len([col for col in phys.columns if 'ECG' in col]) > 0:
            ECG = [col for col in phys.columns if 'ECG' in col][0]
            proc_map["ecg"] = {"col": ECG, "proc": bp.signals.ecg.ecg}
    except Exception as e:
        print(f'ECG Error: {e}')
        
    try:
        if len([col for col in phys.columns if 'EDA' in col]) > 0:
            EDA = [col for col in phys.columns if 'EDA' in col][0]
            proc_map["eda"] = {"col": EDA, "proc": bp.signals.eda.eda}
    except Exception as e:
        print(f'EDA Error: {e}')
        
    try:
        if len([col for col in phys.columns if 'RESPIRATION' in col]) > 0:
            RESP = [col for col in phys.columns if 'RESPIRATION' in col][0]
            proc_map["resp"] = {"col": RESP, "proc": bp.signals.resp.resp}
    except Exception as e:
        print(f'RESP Error: {e}')

    try:
        if len([col for col in phys.columns if 'XYZ' in col]) > 0:
            XYZ = [col for col in phys.columns if 'XYZ' in col]
            proc_map["abs_motion"] = {
                "col": sorted(XYZ),
                "proc": abs_motion_change,}
    except Exception as e:
        print(f'XYZ Error: {e}')
    
    try:
        if len([col for col in phys.columns if 'EMG' in col]) > 0:
            EMG = [col for col in phys.columns if 'EMG' in col]
            EMG.sort()
            proc_map["emg1"] = {"col": EMG[0], "proc": bp.signals.emg.emg}
            try:
                proc_map["emg2"] = {"col": EMG[1], "proc": bp.signals.emg.emg}
            except:
                print('Only one EMG channel')
    except Exception as e:
        print(f'EMG Error: {e}')
        
    has_problem = False
    res_dict = {}
    try:
        for k in proc_map.keys():
            func = proc_map[k]["proc"]
            dat = phys[proc_map[k]["col"]]
            res = func(dat, show=False)
            res_dict[k] = res

        filt = pd.DataFrame()
        # Add metadata columns
        for k in keep_cols:
            filt[k] = phys[k]
        
        # Add raw sensor columns
        for col in phys.columns:
            if col not in keep_cols and col not in ["filtered"]:
                filt[col] = phys[col]

        # Add processed columns
        for key in proc_map.keys():
            filt[key] = res_dict[key]["filtered"]
        return filt
    except Exception as e:
        print(f"Error preprocessing physio data: {e}\n")
        return None