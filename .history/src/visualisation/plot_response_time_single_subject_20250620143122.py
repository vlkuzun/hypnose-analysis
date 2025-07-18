import os
import sys
import json
import argparse
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from datetime import datetime
import matplotlib.dates as mdates
import src.analyse.freerun_analyser
import src.analyse.response_time_analyser_single_session
from src.analysis import get_decision_accuracy, get_response_time, detect_stage
import src.utils as utils
import src.analyse
from src.analyse.response_time_analyser_single_session import analyze_session_folder

def plot_session_response_time(results_df, plot_file=None, subject_id=None):
    """
    Create a scatterplot of response time for each session.
    
    Args:
        results_df (DataFrame): Contains session_id, session_date, accuracy and response time data
        output_file (str): Path to save the plot, if provided
        subject_id (str): Subject ID to use in the plot title
    """    
    # Use trial IDs to find if trial is R1/R2 and correct/incorrect
    trial_id = np.array(results_df['all_trial_id'])

    # Remove non-rewarded [0, 0] trials, if any, from trial_id
    trial_id = trial_id[~np.all(trial_id == 0, axis=1)]

    # Create the plot
    fig, ax = plt.subplots(4, 1, sharex=True, figsize=(12,6))
    ax = ax.ravel()
        
    # Plot each response time type
    r1_correct_trials = np.where((trial_id[:, 0] == 1) & (trial_id[:, 1] == 1))[0]
    r2_correct_trials = np.where((trial_id[:, 0] == 2) & (trial_id[:, 1] == 2))[0]
    r1_incorrect_trials = np.where((trial_id[:, 0] == 1) & (trial_id[:, 1] == 2))[0]
    r2_incorrect_trials = np.where((trial_id[:, 0] == 2) & (trial_id[:, 1] == 1))[0]

    labels = ['R1 correct RT', 'R2 correct RT', 'R1 incorrect RT', 'R2 incorrect RT']
    ax[0].scatter(r1_correct_trials, results_df['all_r1_correct_rt'], s=10, label=labels[0], color='blue')
    ax[1].scatter(r2_correct_trials, results_df['all_r2_correct_rt'], s=10, label=labels[1], color='red')
    ax[2].scatter(r1_incorrect_trials, results_df['all_r1_incorrect_rt'], s=10, label=labels[2], color='green')
    ax[3].scatter(r2_incorrect_trials, results_df['all_r2_incorrect_rt'], s=10, label=labels[3], color='orange')

    # Add average response time and format the plot
    for i, axis in enumerate(ax):
        axis.plot(results_df['avg_response_time'], label='avg response time', color='black', linestyle='--', alpha=0.7)
        axis.spines['top'].set_visible(False)
        axis.spines['right'].set_visible(False)
        axis.set_ylabel('Response time (s)')
        axis.set_title(labels[i])
        axis.set_ylim(0, 20)  # Set visible range to 40 s, although sometime the response time is longer
    ax[3].set_xlabel('Trial')

    # Set title with subject ID if provided
    session_id = os.path.basename(results_df['session_folder'])
    if subject_id:
        plt.suptitle(f'Response time - sub-{subject_id} - session {session_id}')
    else:
        plt.suptitle(f'Response time - session {session_id}')
        
    plt.grid(False)    
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Save if requested
    if plot_file:
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {plot_file}")
    
    plt.tight_layout()
    plt.show()


def plot_response_time(results_df, plot_file=None, subject_id=None):
    """
    Create a scatterplot of response time across sessions.
    
    Args:
        results_df (DataFrame): Contains session_id, session_date, accuracy and response time data
        plot_file (str): Path to save the plot, if provided
        subject_id (str): Subject ID to use in the plot title
    """   

    # Convert date strings to datetime objects for better x-axis formatting
    results_df['date'] = pd.to_datetime(results_df['session_date'], format='%Y%m%d')
    results_df = results_df.sort_values('date')
    
    # Use trial IDs to find if trial is R1/R2 and correct/incorrect
    trial_id = np.array(results_df['total_trial_id'][0])

    # Remove non-rewarded [0, 0] trials, if any, from trial_id
    trial_id = trial_id[~np.all(trial_id == 0, axis=1)]
    
    # Find indices of trial types in each session 
    r1_correct_trials = []
    for session_idx, sublist in enumerate(trial_id):
        if not sublist:
            continue
        for trial_idx, pair in enumerate(sublist[0]):
            if pair[0] == 1.0 and pair[1] == 1.0:
                r1_correct_trials.append((session_idx, trial_idx))

    r2_correct_trials = []
    for session_idx, sublist in enumerate(trial_id):
        if not sublist:
            continue
        for trial_idx, pair in enumerate(sublist[0]):
            if pair[0] == 2.0 and pair[1] == 2.0:
                r2_correct_trials.append((session_idx, trial_idx))

    r1_incorrect_trials = []
    for session_idx, sublist in enumerate(trial_id):
        if not sublist:
            continue
        for trial_idx, pair in enumerate(sublist[0]):
            if pair[0] == 1.0 and pair[1] == 2.0:
                r1_incorrect_trials.append((session_idx, trial_idx))

    r2_incorrect_trials = []
    for session_idx, sublist in enumerate(trial_id):
        if not sublist:
            continue
        for trial_idx, pair in enumerate(sublist[0]):
            if pair[0] == 2.0 and pair[1] == 1.0:
                r2_incorrect_trials.append((session_idx, trial_idx))

    trials_per_session = [len(sublist[0]) if sublist else 0 for sublist in trial_id]
    offsets = np.cumsum([0] + trials_per_session[:-1])  # Starting index of each session in the flat array

    def flatten_index(session_idx, trial_idx, offsets):
        return offsets[session_idx] + trial_idx

    r1_correct_trials = [flatten_index(s, t, offsets) for s, t in r1_correct_trials]
    r2_correct_trials = [flatten_index(s, t, offsets) for s, t in r2_correct_trials]
    r1_incorrect_trials = [flatten_index(s, t, offsets) for s, t in r1_incorrect_trials]
    r2_incorrect_trials = [flatten_index(s, t, offsets) for s, t in r2_incorrect_trials]

    # Get the reaction times for these trials 
    r1_correct_rt = np.concatenate([results_df['total_r1_correct_rt'][session][0] \
                                    if results_df['total_r1_correct_rt'][session] else np.array([]) \
                                        for session in range(len(results_df['total_r1_correct_rt']))])
    r2_correct_rt = np.concatenate([results_df['total_r2_correct_rt'][session][0] \
                                    if results_df['total_r2_correct_rt'][session] else np.array([]) \
                                        for session in range(len(results_df['total_r2_correct_rt']))])
    r1_incorrect_rt = np.concatenate([results_df['total_r1_incorrect_rt'][session][0] \
                                    if results_df['total_r1_incorrect_rt'][session] else np.array([]) \
                                        for session in range(len(results_df['total_r1_incorrect_rt']))])
    r2_incorrect_rt = np.concatenate([results_df['total_r2_incorrect_rt'][session][0] \
                                    if results_df['total_r2_incorrect_rt'][session] else np.array([]) \
                                        for session in range(len(results_df['total_r2_incorrect_rt']))])

    all_avg_response_time = np.concatenate(results_df['avg_response_time'])

    # Create the plot
    fig, ax = plt.subplots(4, 1, sharex=True, figsize=(12,6))
    ax = ax.ravel()
        
    labels = ['R1 correct RT', 'R2 correct RT', 'R1 incorrect RT', 'R2 incorrect RT']
    ax[0].scatter(r1_correct_trials, r1_correct_rt, s=2, label=labels[0], color='blue')
    ax[1].scatter(r2_correct_trials, r2_correct_rt, s=2, label=labels[1], color='red')
    ax[2].scatter(r1_incorrect_trials, r1_incorrect_rt, s=2, label=labels[2], color='green')
    ax[3].scatter(r2_incorrect_trials, r2_incorrect_rt, s=2, label=labels[3], color='orange')

    # Add average response time and format the plot
    for i, axis in enumerate(ax):
        axis.plot(all_avg_response_time, label='avg response time', color='black', linestyle='--', alpha=0.7)
        axis.spines['top'].set_visible(False)
        axis.spines['right'].set_visible(False)
        axis.set_ylabel('Response time (s)')
        axis.set_title(labels[i])
        axis.set_ylim(0, 20)  # Set visible range to 40 s, although sometime the response time is longer
    ax[3].set_xlabel('Trial')

    # Add session boundaries 
    ax[0].vlines(x=offsets[1:], ymin=np.min(r1_correct_rt), ymax=np.max(r1_correct_rt), color='gray')
    ax[1].vlines(x=offsets[1:], ymin=np.min(r2_correct_rt), ymax=np.max(r2_correct_rt), color='gray')
    ax[2].vlines(x=offsets[1:], ymin=np.min(r1_incorrect_rt), ymax=np.max(r1_incorrect_rt), color='gray')
    ax[3].vlines(x=offsets[1:], ymin=np.min(r2_incorrect_rt), ymax=np.max(r2_incorrect_rt), color='gray')
    
    # Set title with subject ID if provided
    if subject_id:
        plt.suptitle(f'Response time - sub-{subject_id}')
    else:
        plt.suptitle(f'Response time')
        
    plt.grid(False)    
    plt.gca().spines['top'].set_visible(False)
    plt.gca().spines['right'].set_visible(False)
    
    # Save if requested
    if plot_file:
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {plot_file}")
    
    plt.tight_layout()
    plt.show()
    return 


def main(session_folder, across_sessions=True, stage=8, sessions=None, plot_file=None, subject_id=None):
    """
    Process a subject folder and calculate response time for a given session or across sessions.
    Combines results from multiple directories within the same session.
    Saves results to CSV file if output_file is provided.
    """    

    if across_sessions:
        subject_path = os.path.split(session_folder)[0]
        subject_path = Path(subject_path)
        print(f"Processing subject folder: {subject_path}")
        
        # Extract subject ID from the folder path
        subject_id = subject_path.name
        if 'sub-' in subject_id:
            subject_id = subject_id.split('sub-')[1]
        
        # Use utils.find_session_roots instead of the local function
        session_roots = utils.find_session_roots(subject_path)
           
        if not session_roots:
            print(f"No valid session directories found in {subject_path}")
            return
        
        # Group sessions by session_id and session_date
        grouped_sessions = {}
        for session_id, session_date, session_path in session_roots:
            if sessions is not None:
                if int(session_id) in sessions:
                    key = (session_id, session_date)
                    if key not in grouped_sessions:
                        grouped_sessions[key] = []
                    grouped_sessions[key].append(session_path)
            
        # Create a list to store combined results
        results = []
        
        # Process each grouped session
        for (session_id, session_date), session_paths in sorted(grouped_sessions.items()):
            print(f"\nProcessing Session ID: {session_id}, Date: {session_date}")
            print(f"Found {len(session_paths)} directories within this session")
            
            # Initialize combined metrics
            total_rt = []
            total_r1_correct_rt = []
            total_r2_correct_rt = []
            total_r1_incorrect_rt = []
            total_r2_incorrect_rt = []
            total_trial_id = []

            # Directory-specific results for detailed information
            dir_results = []
            
            # Process each directory within the session
            for session_path in session_paths:
                detected_stage = int(detect_stage(session_path))

                if stage is not None and detected_stage != stage:
                    print('Continue to next session...')
                    continue

                print(f"  Processing directory: {session_path.name}")
                try:
                    # Get response time data for this directory
                    response_time = get_response_time(session_path)
                    
                    if response_time and response_time != {
                        'rt': 0, 
                        'r1_correct_rt': 0,
                        'r1_incorrect_rt': 0,
                        'r1_avg_correct_rt': 0,
                        'r1_avg_incorrect_rt': 0,
                        'r1_avg_rt': 0,
                        'r2_correct_rt': 0,
                        'r2_incorrect_rt': 0,
                        'r2_avg_correct_rt': 0,
                        'r2_avg_incorrect_rt': 0,
                        'r2_avg_rt': 0,
                        'hit_rt': 0,
                        'false_alarm_rt': 0,
                        'trial_id': 0
                    }:
                        # Add to totals
                        total_rt.append(response_time['rt'])
                        total_r1_correct_rt.append(response_time['r1_correct_rt'])
                        total_r2_correct_rt.append(response_time['r2_correct_rt'])
                        total_r1_incorrect_rt.append(response_time['r1_incorrect_rt'])
                        total_r2_incorrect_rt.append(response_time['r2_incorrect_rt'])
                        total_trial_id.append(response_time['trial_id'].tolist())

                        dir_info = {
                            'directory': session_path.name,
                            'rt': response_time['rt'],
                            'r1_correct_rt': response_time['r1_correct_rt'],
                            'r2_correct_rt': response_time['r2_correct_rt'],
                            'r1_incorrect_rt': response_time['r1_incorrect_rt'],
                            'r2_incorrect_rt': response_time['r2_incorrect_rt'],
                            'trial_id': response_time['trial_id']
                        }
                        
                        dir_results.append(dir_info)
                    else:
                        print(f"    No valid response time data found")
                        
                except Exception as e:
                    print(f"    Error processing directory {session_path.name}: {str(e)}")
            
                # Calculate combined response time values for the session 
                total_rt = np.array(total_rt, dtype=float).flatten()  
                if total_rt.size != 0:
                    window_size = 10
                    avg_response_time = np.convolve(total_rt, np.ones(window_size)/window_size, mode='same')
                else:
                    avg_response_time = np.zeros(len(total_trial_id))

                # Store combined session results
                session_result = {
                    'session_id': session_id,
                    'session_date': session_date,
                    'total_rt': total_rt,
                    'total_r1_correct_rt': total_r1_correct_rt,
                    'total_r2_correct_rt': total_r2_correct_rt,
                    'total_r1_incorrect_rt': total_r1_incorrect_rt,
                    'total_r2_incorrect_rt': total_r2_incorrect_rt,
                    'total_trial_id': total_trial_id,
                    'avg_response_time': avg_response_time,
                    'directory_count': len(session_paths),
                    'directories': dir_results
                }
                 
                results.append(session_result)
            
        # Create DataFrame from combined results
        results_df = pd.DataFrame([{k: v for k, v in r.items() if k != 'directories'} for r in results])

        # Plot response time across sessions
        plot_response_time(results_df, plot_file, subject_id)

    else:
        # Detect stage 
        session_folder = Path(session_folder)
        behav_folder = session_folder / "behav"
        
        if not behav_folder.exists():
            print(f"No behavior folder found at {behav_folder}")
            return None
        
        # Collect all session directories
        session_dirs = [d for d in behav_folder.iterdir() if d.is_dir()]
        print(f"Found {len(session_dirs)} behavioral sessions in {behav_folder}")
        
        session_stage = []
        for s, session_dir in enumerate(sorted(session_dirs)):
            session_stage.append(detect_stage(session_dir))
            print(f"Detected stage: {session_stage[s]}")

        # Get the accuracy and response time data
        if all(stage <= 7 for stage in session_stage):
            results = src.analyse.response_time_analyser_single_session.analyze_session_folder(session_folder)
        elif all(stage > 7 for stage in session_stage):
            results = src.analyse.freerun_analyser.analyze_session_folder(session_folder)
        else:
            raise ValueError("Some subfolers were run on different stages.")
        
        # Plot response time for the session
        plot_session_response_time(results, plot_file, subject_id)

    return results
    

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv.append("/Volumes/harris/hypnose/rawdata/sub-020_id-072/ses-61_date-20250618")

    parser = argparse.ArgumentParser(description="Calculate and plot response time for a session or across sessions")
    parser.add_argument("session_folder", help="Path to the session folder containing data")
    parser.add_argument("--across_sessions", default=True, help="Whether to plot results for a single session or across sessions")
    parser.add_argument("--stage", "--s", default=8, help="Stage to be analysed.")
    parser.add_argument("--sessions", default=np.arange(55,63), help="List of session IDs (optional)") 
    parser.add_argument("--output", "-o", help="Path to save CSV output (optional)")  # TODO 
    parser.add_argument("--plot", "-p", help="Path to save plot image (optional)")
    args = parser.parse_args()
    
    main(args.session_folder, args.across_sessions, args.stage, args.sessions, args.output, args.plot)











































































































































































































