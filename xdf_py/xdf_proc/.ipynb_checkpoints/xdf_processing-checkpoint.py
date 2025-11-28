from scipy.io.wavfile import write
import numpy as np
import pandas as pd
from os import path
import sys
from datetime import timedelta

sys.path.append(path.expanduser("~/python"))

from .MobiXDF import *

import warnings
warnings.filterwarnings('ignore')

AUDIO = "Audio"
OPEN_SIGNALS = "OpenSignals"
STIM_LABELS = "StimLabels"
MAX_INT16 = 32767

def audio_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_audio.wav"
    outpath = path.join(outfldr, fname)
    return outpath

def eyedat_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_eyetrack.pqt"
    outpath = path.join(outfldr, fname)
    return outpath

def numpy_to_wav(audio_data:np.array, filepath:str, sample_rate:int=44100)->bool:
    """Converts numpy array to wav file."""
    try:
        scaled_data = np.int16(audio_data / np.max(np.abs(audio_data)) * MAX_INT16)
        write(filepath, sample_rate, scaled_data)
        return True
    except Exception as e:
        msg = f"Failed to write {filepath}: {e}"
        print(msg)
        send_to_log(msg, prefix="audio")
        return False

def send_to_log(msg, prefix:str="physio"):
    with open(f"{prefix}_proc.log", "a") as f:
        f.write(f"{msg}\n")

def eyedat_to_pqt(xdf, filepath:str) -> bool:
    channel_lol = xdf.channels()
    eye_tracker = next((tracker for sublist in channel_lol for tracker in sublist if tracker in ['EyeLink', 'Argus_Eye_Tracker']), None)
    edf = xdf.get_channel_timeseries(eye_tracker)
    try:
        edf.to_parquet(filepath, index=False)
    except:
        msg = f"Failed to write {filepath}"
        print(msg)
        send_to_log(msg, prefix=eye_tracker)
        return False
    return True

def eeg_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_eeg.pqt"
    outpath = path.join(outfldr, fname)
    return outpath

def eeg_to_pqt(eeg_df: pd.DataFrame, filepath:str) -> bool:
    try:
        eeg_df.to_parquet(filepath, index=False)
    except:
        msg = f"Failed to write {filepath}"
        print(msg)
        send_to_log(msg, prefix=eye_tracker)
        return False
    return True

def eeg_markers_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_eeg_markers.csv"
    outpath = path.join(outfldr, fname)
    return outpath

def save_eeg_markers(evs: pd.DataFrame, outpath: str) -> bool:
    success = False
    if type(evs) is pd.DataFrame:
        evs.to_csv(outpath, index=False)
        success = True
    else:
        msg = f"Saving EEG markers failed for: {outpath}"
        print(msg)
        send_to_log(f"{msg}; {nowstr()}\n")
    return success

def behav_filepath(outfldr: str, fil: str) -> str:
    fname = path.basename(fil).split(".")[0]
    fname = f"{fname}_behav.csv"
    outpath = path.join(outfldr, fname)
    return outpath

def save_behav(behav_df: pd.DataFrame, filepath:str) -> bool:
    try:
        behav_df.to_csv(filepath, index=False)
    except:
        msg = f"Failed to write {filepath}"
        print(msg)
        send_to_log(msg, prefix=eye_tracker)
        return False
    return True

def get_sync_delay(mobi:MobiXDF, label:str)->float:
    """
    use lsl clock offset data to link the system time to the first lsl timestamp
    will use these to sync outputs that do not have an lsl timstamp embedded (e.g.
    audio / video). This shouldn't be a problem within the MoBI environment. Just 
    when we are exporting data from the XDF files.
    """
    try:
        idx = mobi._get_channel_idx(label)
        dat = mobi.data[idx]
        lsl_sync = float(dat["footer"]["info"]["clock_offsets"][0]["offset"][0]["time"][0])
        # ts_sync = float(dat["footer"]["info"]["clock_offsets"][0]["offset"][0]["value"][0])
        fts = float(dat["footer"]["info"]["first_timestamp"][0])
        
        sync_delay = lsl_sync - fts # delay between first lsl ts and the first clock offset check
        # remove that delay from the system time value at first clock offset
        # t0 = ts_sync - sync_delay # gives us the local system time value for the first LSL ts.
        # We will use this to link audio/video absolute times to the system time of the events file timestamps
        return(sync_delay)
    except:
        return np.nan
    
def sec_to_hhmmss(seconds:float):
    # Create a timedelta object with the given milliseconds
    duration = timedelta(seconds=seconds)
    # Extract hours, minutes, and seconds from the timedelta object
    hours = duration.seconds // 3600
    minutes = (duration.seconds % 3600) // 60
    seconds = duration.seconds % 60
    # Format the time as HH:MM:SS
    time_string = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return time_string

def process_xdf_modalities(checkbox_states: list, fil: str, outfldr: str):
    try:
        mobi = MobiXDF(fil)
        if checkbox_states[0] == 1: # Getting eyetracking
            try:
                print('Getting eyetracking')
                channel_lol = mobi.channels()
                eye_tracker = next((tracker for sublist in channel_lol for tracker in sublist if tracker in ['EyeLink', 'Argus_Eye_Tracker']), None)
                
                eyetrack = mobi.get_channel_timeseries(eye_tracker)
                if isinstance(eyetrack, pd.DataFrame):
                    delay_ext = np.nan
                    stim_ext = get_sync_delay(mobi, eye_tracker)
                    if np.isnan(delay_ext):
                        delay_ext = get_sync_delay(mobi, "Audio")
                    if np.isnan(delay_ext):
                        delay_ext = get_sync_delay(mobi, "Video")
                    if np.isnan(delay_ext):
                        send_to_log(f"{fil} has no sync delay\n{nowstr()}\n")
                    shift_ext = abs(stim_ext - delay_ext)
                    eyetrack["ext_time"] = eyetrack["time_sec"] + shift_ext
                    eyetrack["hh_mm_ss"] = eyetrack.ext_time.apply(lambda x:sec_to_hhmmss(x))
                    rawpath = eyedat_filepath(outfldr, fil)
                    eyetrack.to_parquet(rawpath) 
                else:
                    send_to_log(f"{fil} has no eyetracking\n{nowstr()}\n")
                send_to_log(f"    finished {fil}\n    at time:{nowstr()}\n")
            except Exception as e:
                print('Failed to get eyetracking: ', e)
            
        if checkbox_states[1] == 1: # Getting audio
            try:
                print('Getting audio')
                audio_idx = mobi._get_channel_idx("Audio")
                audio = mobi.data[audio_idx]["time_series"]
                aud_path = audio_filepath(outfldr, fil)
                success = numpy_to_wav(audio, aud_path)
            except Exception as e:
                print('Failed to get audio: ', e)
            
        if checkbox_states[2] == 1: # Getting LSL events
            try:
                print('Getting LSL events')
                events = mobi.get_channel_timeseries(STIM_LABELS)
                if isinstance(events, pd.DataFrame):
                    delay_ext = np.nan
                    rawpath = raw_event_filepath(outfldr, fil)
                    stim_ext = get_sync_delay(mobi, "StimLabels")
                    if np.isnan(delay_ext):
                        delay_ext = get_sync_delay(mobi, "Audio")
                    if np.isnan(delay_ext):
                        delay_ext = get_sync_delay(mobi, "Video")
                    if np.isnan(delay_ext):
                        send_to_log(f"{fil} has no sync delay\n{nowstr()}\n")
                    shift_ext = abs(stim_ext - delay_ext)
                    events["ext_time"] = events["time_sec"] + shift_ext
                    events["hh_mm_ss"] = events.ext_time.apply(lambda x:sec_to_hhmmss(x))    
                    events = events["StimMarkers_alpha,timestamps,lsl_timestamp,ext_time,hh_mm_ss".split(',')]
                    eventpath = event_filepath(outfldr, fil)
                    save_events(events, eventpath)
                else:
                    send_to_log(f"{fil} has no events\n{nowstr()}\n")
            except Exception as e:
                print('Failed to get LSL events: ', e)
                
        if checkbox_states[3] == 1: # Getting raw events
            try:
                print('Getting raw events')
                events = mobi.get_channel_timeseries(STIM_LABELS)
                if isinstance(events, pd.DataFrame):
                    delay_ext = np.nan
                    rawpath = raw_event_filepath(outfldr, fil)
                    save_events(events, rawpath)
            except Exception as e:
                print('Failed to get raw events: ', e)
                
        if checkbox_states[4] == 1: # Getting Physio
            try:
                print('Getting physio')
                if ['OpenSignals'] not in mobi.channels():
                    send_to_log(f"{fil} has no physio\n{nowstr()}\n")
                else:
                    df = mobi.get_channel_timeseries(OPEN_SIGNALS)
                    if isinstance(df, pd.DataFrame):
                        physiopath = physio_filepath(outfldr, fil)
                        has_physio = save_physio(df, physiopath)
                        filt = -1
                        filt = preproc_physio_df(df)
                        if has_physio and isinstance(filt, pd.DataFrame):
                            eventpath = raw_event_filepath(outfldr, fil)
                            save_events(filt, eventpath)
                        else:
                            send_to_log(f"{fil} physio preprocessing failed:\n{nowstr()}\n")
                    else:
                        send_to_log(f"{fil} has no physio\n{nowstr()}\n")
            except Exception as e:
                print('Failed to get physio: ', e)
                
        if checkbox_states[5] == 1: # Getting EEG
            try:
                print('Getting EEG')
                eeg = mobi.get_channel_timeseries('BrainVision RDA')
                if isinstance(eeg, pd.DataFrame):
                    delay_ext = np.nan
                    stim_ext = get_sync_delay(mobi, "BrainVision RDA")
                    if np.isnan(delay_ext):
                        delay_ext = get_sync_delay(mobi, "Audio")
                    if np.isnan(delay_ext):
                        delay_ext = get_sync_delay(mobi, "Video")
                    if np.isnan(delay_ext):
                        send_to_log(f"{fil} has no sync delay\n{nowstr()}\n")
                    shift_ext = abs(stim_ext - delay_ext)
                    eeg["ext_time"] = eeg["time_sec"] + shift_ext
                    eeg["hh_mm_ss"] = eeg.ext_time.apply(lambda x:sec_to_hhmmss(x))    
                    eegpath = eeg_filepath(outfldr, fil)
                    eeg_to_pqt(eeg, eegpath)
                else:
                    send_to_log(f"{fil} has no eeg\n{nowstr()}\n")
            except Exception as e:
                print('Failed to get EEG: ', e)
                
        if checkbox_states[6] == 1: # Getting EEG markers
            try:
                print('Getting EEG markers')
                markers = mobi.get_channel_timeseries('BrainVision RDA Markers')
                if isinstance(markers, pd.DataFrame):
                    rawpath = eeg_markers_filepath(outfldr, fil)
                    save_eeg_markers(markers, rawpath)
            except Exception as e:
                print('Failed to get EEG markers: ', e)
        
        if checkbox_states[7] == 1:
            try:
                print('Getting Behavioral data')
                if 'cpCST' in [mod[0] for mod in mobi.channels()]:
                    behav = mobi.get_channel_timeseries('cpCST')
                    if isinstance(behav, pd.DataFrame):
                        delay_ext = np.nan
                        stim_ext = get_sync_delay(mobi, 'cpCST')
                        if np.isnan(delay_ext):
                            delay_ext = get_sync_delay(mobi, "Audio")
                        if np.isnan(delay_ext):
                            delay_ext = get_sync_delay(mobi, "Video")
                        if np.isnan(delay_ext):
                            send_to_log(f"{fil} has no sync delay\n{nowstr()}\n")
                        shift_ext = abs(stim_ext - delay_ext)
                        behav["ext_time"] = behav["time_sec"] + shift_ext
                        rawpath = behav_filepath(outfldr, fil)
                        save_behav(behav, rawpath)
                else:
                    print('XDF has no cpCST data')
            except Exception as e:
                print('Failed to get Behavioral data: ', e)
                
        if checkbox_states[8] == 1:
            try:
                print('Getting MindLogger data')
                if 'MindLogger' in [mod[0] for mod in mobi.channels()]:
                    ml = mobi.get_channel_timeseries('MindLogger')
                    if isinstance(ml, pd.DataFrame):
                        delay_ext = np.nan
                        stim_ext = get_sync_delay(mobi, 'MindLogger')
                        if np.isnan(delay_ext):
                            delay_ext = get_sync_delay(mobi, "Audio")
                        if np.isnan(delay_ext):
                            delay_ext = get_sync_delay(mobi, "Video")
                        if np.isnan(delay_ext):
                            send_to_log(f"{fil} has no sync delay\n{nowstr()}\n")
                        shift_ext = abs(stim_ext - delay_ext)
                        ml["ext_time"] = ml["time_sec"] + shift_ext
                        rawpath = behav_filepath(outfldr, fil)
                        save_behav(ml, rawpath)
                else:
                    print('XDF has no MindLogger data')
            except Exception as e:
                print('Failed to get MindLogger data: ', e)
                
    except Exception as e:
        print(e)
        send_to_log(f"{fil} failed:\n{e}\n{nowstr()}\n")

def process_xdf_file(fil: str, outfldr: str) -> pd.DataFrame:
    """
    Read in a xdf file, extract physio and event info.
    Save raw physio and event info as pqt and csv files.
    Return filtered dataFrame.
    """
    success = True
    try:
        mobi = MobiXDF(fil)
        df = mobi.get_channel_timeseries(OPEN_SIGNALS)
        if isinstance(df, pd.DataFrame):
            physiopath = physio_filepath(outfldr, fil)
            has_physio = save_physio(df, physiopath)
            filt = -1
            filt = preproc_physio_df(df)
            if has_physio and isinstance(filt, pd.DataFrame):
                eventpath = raw_event_filepath(outfldr, fil)
                save_events(filt, eventpath)
            else:
                send_to_log(f"{fil} physio preprocessing failed:\n{nowstr()}\n")
        else:
            send_to_log(f"{fil} has no physio\n{nowstr()}\n")

        events = mobi.get_channel_timeseries(STIM_LABELS)
        if isinstance(events, pd.DataFrame):
            # TODO: Consider splitting this out into separate function(s)
            # TODO: Currently just using first timepoint as anchor, but do not account
            #       for drift. Leverage clock offsets as basis for interpolation.

            delay_ext = np.nan
            rawpath = raw_event_filepath(outfldr, fil)
            save_events(events, rawpath)
            stim_ext = get_sync_delay(mobi, "StimLabels")
            if np.isnan(delay_ext):
                delay_ext = get_sync_delay(mobi, "Audio")
            if np.isnan(delay_ext):
                delay_ext = get_sync_delay(mobi, "Video")
            if np.isnan(delay_ext):
                send_to_log(f"{fil} has no sync delay\n{nowstr()}\n")
            shift_ext = abs(stim_ext - delay_ext)
            events["ext_time"] = events["time_sec"] + shift_ext
            events["hh_mm_ss"] = events.ext_time.apply(lambda x:sec_to_hhmmss(x))    
            events = events["StimMarkers_alpha,timestamps,lsl_timestamp,ext_time,hh_mm_ss".split(',')]
            eventpath = event_filepath(outfldr, fil)
            save_events(events, eventpath)
        else:
            send_to_log(f"{fil} has no events\n{nowstr()}\n")
            
        # directly extracts and converts audio for xdf file
        
#         mobi  = MobiXDF(filename)
        audio_idx = mobi._get_channel_idx("Audio")
        audio = mobi.data[audio_idx]["time_series"]
        aud_path = audio_filepath(outfldr, fil)
        success = numpy_to_wav(audio, aud_path)
        
        channel_lol = mobi.channels()
        eye_tracker = next((tracker for sublist in channel_lol for tracker in sublist if tracker in ['EyeLink', 'Argus_Eye_Tracker']), None)
        
        eyetrack = mobi.get_channel_timeseries(eye_tracker)
        if isinstance(eyetrack, pd.DataFrame):
            delay_ext = np.nan
            stim_ext = get_sync_delay(mobi, eye_tracker)
            if np.isnan(delay_ext):
                delay_ext = get_sync_delay(mobi, "Audio")
            if np.isnan(delay_ext):
                delay_ext = get_sync_delay(mobi, "Video")
            if np.isnan(delay_ext):
                send_to_log(f"{fil} has no sync delay\n{nowstr()}\n")
            shift_ext = abs(stim_ext - delay_ext)
            eyetrack["ext_time"] = eyetrack["time_sec"] + shift_ext
            eyetrack["hh_mm_ss"] = eyetrack.ext_time.apply(lambda x:sec_to_hhmmss(x))
            rawpath = eyedat_filepath(outfldr, fil)
            eyetrack.to_parquet(rawpath) 
        else:
            send_to_log(f"{fil} has no eyetracking\n{nowstr()}\n")
            
        send_to_log(f"    finished {fil}\n    at time:{nowstr()}\n")
        
        return filt
    except Exception as e:
        print(e)
        send_to_log(f"{fil} failed:\n{e}\n{nowstr()}\n")
        return None
    
