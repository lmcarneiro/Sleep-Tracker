#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May 15 16:33:18 2020

@author: lucas
"""

import glob
import pandas as pd
import datetime as d8
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.collections import LineCollection
import numpy as np
import os
import talib as ta
from statistics import mode, StatisticsError
import time


path_end = '_OXIRecord.csv'

def file_glob(dates, path_start, load_all=False):
    """Takes in dates given as integers and returns list of file names in
    the Sleep directory that correspond to that date."""
    
    all_files = sorted(glob.glob(path_start + '*'))
    
    if load_all is True:
        files = [sorted(glob.glob(path_start + "%d*.csv" %date)) for date in dates]
    
    else:
        files = [sorted(glob.glob(path_start + "%d*.csv" %date)) for date in dates]
    
    print("Latest file is: '%s'\n" %all_files[-1][28:])
    return files    

def load(dates, path_start, load_all=False, plotit=False):
    """Loads oximeter file based on dates given as a list of integers, 
    returns list of dataframes."""
    

    files = file_glob(dates, path_start, load_all)
    
    dates = [str(date) for date in dates]
    
    date_f = []
    i = 0
    if load_all is True:        
        for date in files:
            for file in date:                
                try:                    
                    date_f.append(pd.read_csv(file))
                    print("'%s'" %file[28:], "loaded!\n")   
                    i += 1
                except IndexError:
                    print("File not found for date: %s/%s/%s" %(dates[i][4:6],
                                                                dates[i][6:8],
                                                                dates[i][:4]))
    else:
        for date in files:
            try:
                date_f.append(pd.read_csv(date[0]))
                print("'%s'" %date[0][28:], "loaded!") 
                i += 1
            except IndexError:      
                print("File not found for date: %s/%s/%s" %(dates[i][4:6],
                                                            dates[i][6:8],
                                                            dates[i][:4]))
            
    if plotit is True:
        
        plot(date_f)
        
    return date_f

def combine_date(date, path_start):
    """Combine multiple oximeter files into one file. Used to combine
    separete files from the same day into one. Date must be in year-month-day.
    """
    
    if type(date) == list:
        dates = ['%s/%s/%s' %(date[:4], date[4:6], date[6:8]) for date in date]
        files = []
        
        for date in date:
            l = len(date)
            
            if l < 14:
                print(date, "Date is in wrong format")
                print("Date must be 'yearmoda")
                return
            
            file = path_start + date + path_end
            files.append(glob.glob(file)[0])
        
        num_files = len(files)
        first_file = files[0]
        
        combined_csv = pd.concat([pd.read_csv(f) for f in files])
        combined_csv.to_csv(first_file.replace('.csv', '_combined.csv'), index=False)
        
        print("Combined files for dates: %s and %s" %(dates[0], dates[1]))
        return
        
    if '-' not in date:
        print(date, "Date is in wrong format")
        print("Date must be year-month-day")
        return
    
    date = date.replace('-', '')
    file = path_start + date + '*' + path_end
    files = glob.glob(file)
    files_sorted = sorted(files)
    
    num_files = len(files_sorted)
    if num_files == 1:
        print("Only one file for this date")
        return
    
    elif num_files == 0:
        print("No files found for this date")
        return
    
    print("There are %d files!" %num_files)
    
    first_file = files_sorted[0]
    combined_csv = pd.concat([pd.read_csv(f) for f in files_sorted])
    combined_csv.to_csv(first_file.replace('.csv', '_combined.csv'), index=False)
    
    print("Combined files for date: %s/%s/%s" %(date[:4], date[4:6], date[6:8]))
    
    for file in files_sorted:
        os.remove(file)
    
    print("Removed individual files!")


def clean(files):
    """Cleans up oximeter files by converting dates from string to datetime
    objects. Also replaces broken SpO2 and pulse rate data with 99 and 60."""
    
    date_times = []
    for date in files:
        df = pd.read_csv(date)
        len_df = len(df) - 1
        try:
            first_time = int(df.Time[0][:8].replace(':',''))
            last_time = int(df.Time[len_df][:8].replace(':',''))
            date_times.append((first_time, last_time))
            dates = [d8.datetime.strptime(df.Time[i], "%H:%M:%S %b %d %Y")
                     for i in df.index]
            df["Time"] = dates
            df.replace([255, 65535], [99, 60], inplace=True)
            df.rename(columns={"SpO2(%)":"SpO2",
                               "Pulse Rate(bpm)":"PR",
                               "Motion":"Mov",
                               "Vibration": "Vib"}, inplace=True)
            df.to_csv(date, index=False)
            print("'%s' cleaned!" %date[28:])
            
            if len(date) == 2 and date_times[0][1] - date_times[1][0] <= 60:
                combine = input("'%s' and '%s' look like they can be combined, Y/N: "
                                %(date[0][28:], date[1][28:]))
        
                if combine in ['Y', 'y']:
                    year = date[0][35:39]
                    month = date[0][39:41]
                    day = date[0][41:43]
                    
                    combine_date("%s-%s-%s" %(year, month, day), path_start)
                    
                else:
                    print("'%s' and '%s' not combined." %(date[0],
                                                          date[1]))
            
        except ValueError:
            print("'%s' has already been cleaned." %date[28:])
            print("Moving to next date given for cleaning.\n")

def plot(df_list, smooth=False, tp=None, thresh=True):
    """Plots SpO2, heart rate, and movement on same plot. df must be a list.
    Can do multiple dates."""
    
    for df in df_list:
        
        datetimes = pd.to_datetime(df["Time"])
        date = datetimes[0].date()
        time = datetimes[0].time()
        
        if time.hour > 12 and time.hour < 24:
            pass
        else:
            date -= d8.timedelta(days=1)
            
        if thresh is True:
            fig, (ax1, ax2, ax3, ax4, ax5) = plt.subplots(5, sharex=True)
        else:
            fig, (ax1, ax2, ax3, ax4) = plt.subplots(4, sharex=True)
        fig.canvas.set_window_title('%d/%d/%s' 
                                    %(date.month, date.day, str(date.year)[2:]))
        
        ax1.set_title("Night of %d/%d/%s"
                    %(date.month, date.day, str(date.year)[2:]))
        
        ax1.plot(datetimes, df.SpO2, color='skyblue')
        ax1.set_ylabel('SpO2 (%)')
        
        ax2.plot(datetimes, df.PR, color='tomato')
        ax2.plot(datetimes, df.PR_SMA, color='black')         
        ax2.set_ylabel('Pulse Rate (bpm)')
        
        ax3.plot(datetimes, df.Mov, color='mediumseagreen')
        ax3.set_ylabel('Movement (AU)')
        
        if thresh is True:
            
            ax4.set_ylabel("P.R. - Average P.R. (AU)")
            ax4.plot(datetimes, [3]*len(df), color='black')
            ax4.plot(datetimes, df.PR_delta, color='gold')
            
            ax5.set_ylabel("Pulse Rate (bpm)")
            ax5.scatter(datetimes[df.Awake == 0], df.PR[df.Awake == 0], 
                        color='green', label='Sleep')
            ax5.scatter(datetimes[df.Awake == 1], df.PR[df.Awake == 1], 
                        color='red', label='Wake')
            
            ax5.xaxis.set_major_formatter(mdates.DateFormatter('%H-%M-%S'))
            ax5.set_xlabel('Time')
            ax5.legend()
        
        if smooth is True and thresh is False:
            
            ax4.scatter(datetimes[df.Awake == 0], df.PR[df.Awake == 0], 
                        color='green', label='Sleep')
            ax4.scatter(datetimes[df.Awake == 1], df.PR[df.Awake == 1],
                        color='red', label='Wake')
            
            ax4.set_ylabel("Pulse Rate (bpm)")
            ax4.xaxis.set_major_formatter(mdates.DateFormatter('%H-%M-%S'))
            ax4.set_xlabel('Time')
            ax4.legend()
        
    
    print("\nPlots finished!")

def time_asleep(dates, load_all=False, tp=None, plotit=False, threshold=0,
                average=False, who='Me', thresh=True):
    """
    Calculates time spent asleep based on HR and movement. -Mostly Done.
    Want to calculate the time spent in each stage too.
    """
    
    """First stage is light
       REM sleep usually happens about every 90-110 mins and lasts 15-20 mins.
       REM sleep duration lasts longer closer you get to morning.
       
       50-60% is usually light sleep
       15-20% is deep sleep
       20-25% is REM
       5% or less awake
       
       Usually HR decreases during apnea and increases after apnea
       
       People with apnea usually have 600 episodes per night each lasting 30-60s
       Apnea is 5 or more episodes per hour of sleep.
       
       HR drops during sleep to adapt to lower metabolic needs. 
       Consequently, HR drops even more from light sleep to deep sleep.
       During REM HR increases and variability also increases.
       HRV does seem to increase quite a bit in REM.
       I seem to wake up often right after REM.
       """
    path_start = '/home/lucas/Documents/Sleep/%s/O2Ring_' %who
    dates_df = load(dates, path_start, load_all)
    for df in dates_df:
        
        first_tp = pd.to_datetime(df.Time.iloc[0])
        last_tp = pd.to_datetime(df.Time.iloc[-1])
        tot_time = (last_tp - first_tp)
        
        df.loc[df.Mov < 3, 'Mov_lbl'] = 'light'
        df.loc[df.Mov >= 3, 'Mov_lbl'] = 'heavy'
        df.loc[df.Mov == 0, 'Mov_lbl'] = 'None'
        
        df["PR_SMA"] = ta.SMA(df.PR, timeperiod=tp)
        df["PR_SMA"] = df.PR_SMA.shift(periods=-int(tp/2))
        df['PR_delta'] = (df.PR - df.PR_SMA)
        df["PR_diff"] = df.PR.diff()
        df["Awake"] = 0
        
        if threshold > 0:
            df['PR_awake'] = df.PR_delta > 3
            
        if average is True:
            for i in df.PR.index:
                try:
                    PR_window = df.PR_diff.iloc[i:i+15]
                    Mov_window = df.Mov_lbl.iloc[i:i+15]

                    if (sum(PR_window) < 2 
                    and df.PR_diff.loc[i] == 0 
                    and Mov_window.str.contains("heavy").any()):
                        
                        df.loc[i, 'Awake'] = 1
                        
                    try:
                        if (abs(np.mean(PR_window)) > 0.133
                        and mode(PR_window) == 0  
                        and df.PR_diff.loc[i] == 0):
                           
                            df.loc[i, 'Awake'] = 1
                            
                    except StatisticsError:
                        df.loc[i, 'Awake'] = 0
                        
                except IndexError:
                    pass
                
        tot_t_str = str(tot_time)
        tot_sec = tot_time.total_seconds()
        
        thresh_t = time.gmtime(sum(df.PR_awake * 4))
        thresh_t_str = time.strftime('%H:%M:%S', thresh_t)
        
        avg_t = time.gmtime(sum(df.Awake * 4))
        avg_t_str = time.strftime('%H:%M:%S', avg_t)
        
        thresh_awake = time.gmtime(tot_sec - sum(df.PR_awake * 4))
        thresh_sleep = time.strftime('%H:%M:%S', thresh_awake)
        
        avg_awake = time.gmtime(tot_sec - sum(df.Awake * 4))
        avg_sleep = time.strftime('%H:%M:%S', avg_awake)
        
        datetimes = pd.to_datetime(df["Time"].iloc[0])
        date = datetimes.date()
        day, mo, yr = date.day, date.month, str(date.year)[2:]
        
        print("\n------------%d/%d/%s------------"%(mo, day, yr))
        print("Time awake threshold: %s" %thresh_t_str)
        print("Time asleep threshold: %s\n" %thresh_sleep)
        print("Time awake average: %s" %avg_t_str)
        print("Time asleep average: %s" %avg_sleep)
        print("\nTotal recording time: %s" %tot_t_str[7:])
        
        df['dpr'] = df.PR_SMA.diff()
        drop_dup = df.Mov.drop_duplicates()
        med_mov = np.median(drop_dup)
        
    if plotit is True:
        plot(dates_df, smooth=True, thresh=thresh)
    return dates_df