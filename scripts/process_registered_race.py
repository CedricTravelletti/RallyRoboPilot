""" Process data from a registered race. 

This scipt automatically splits the data in laps. 

"""
import os 
import numpy as np 


def load_data(base_folder):
    commands = np.load(os.path.join(base_folder, "commands.npy"), allow_pickle=True)
    timestamps = np.load(os.path.join(base_folder, "timestamps.npy"), allow_pickle=True)
    lap_times = np.load(os.path.join(base_folder, "lap_times.npy"), allow_pickle=True)
    return commands, timestamps, lap_times

def split_laps(commands, timestamps, lap_times):
    current_lap_time = 0.
    i = 0
    all_laps_commands = []
    all_laps_timestamps = []
    current_lap_commands = []
    current_lap_timestamps = []
    for i in range(len(commands)):
        # If still same lap
        if np.abs(lap_times[i] - current_lap_time) < 1e-4:
            current_lap_commands.append(commands[i])
            current_lap_timestamps.append(timestamps[i])
        # Go to next lap.
        else:
            # Store processed lap.
            all_laps_commands.append(current_lap_commands)
            all_laps_timestamps.append(current_lap_timestamps)
            # Begin next lap.
            current_lap_time = lap_times[i]
            current_lap_commands = [commands[i]]
            current_lap_timestamps = [timestamps[i]]
    # By design, the last lap is not returned.
    # This is because usually we stop recording in the middle of a lap.
    lap_durations = [t[-1] - t[0] for t in all_laps_timestamps]
    # Do not return first lap (warm-up before first crossing the starting line).
    return all_laps_commands[1:], all_laps_timestamps[1:], lap_durations[1:]
