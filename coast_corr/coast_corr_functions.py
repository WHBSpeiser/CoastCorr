import glob
import pandas as pd
import os
import folium
import dataretrieval.nwis as nwis
import requests
import geopandas as gpd
import rioxarray

def catalogue_csv(input_fold):

    os.chdir(input_fold)
    band=input_fold.split("/")[len(input_fold.split("/"))-1]
    path_parent = os.path.dirname(input_fold)
    csv_fold=path_parent+'/coastcorr_csv'
    res_out=csv_fold+'/'+band+"_combined_csv.csv"
    if not os.path.exists(csv_fold): os.makedirs(csv_fold)

    if not os.path.exists(res_out):
        print('combined csv not located, combining csv files') 
        #create list of files in folder
        extension = 'csv'
        all_filenames = [i for i in glob.glob('*.{}'.format(extension))]

        #combine all files in the list
        combined_csv = pd.concat([pd.read_csv(f) for f in all_filenames ])

        res = combined_csv.pivot_table(index=['Date'], columns='geometry',
                         values='data', aggfunc='first').reset_index()

        print('csv files combined')
        res.to_csv(res_out)
        print('saved to file')
    print('Done')
    
    


def get_data(envin,station_name,csv_folder):
    if envin == 'River Discharge':
        collector='USGS'
        site_path=os.path.dirname(os.path.dirname(os.path.dirname(csv_folder)))
        env_fold=site_path+'/environmental_data_csv'
        collec_fold=env_fold+'/'+collector
        file_out= collec_fold+"/"+station_name+'.csv'

        print('checking to see if data already downloaded')
        if not os.path.exists(env_fold): os.makedirs(env_fold)
        if not os.path.exists(collec_fold): os.makedirs(collec_fold)
        if not os.path.exists(file_out): 
            print('data not downloaded, downloading data')
            files = os.listdir(csv_folder)
            sorted_files = sorted(files)
            start=sorted_files[0].split(".")[0]
            end=sorted_files[(len(sorted_files)-1)].split(".")[0]
            env_df=nwis.get_record(sites=station_name, service='iv', start=start, end=end)
            env_df= env_df.reset_index()
            env_df.to_csv(file_out)
            print('USGS Gauge:', station_name, 'Data Pulled')
        
        if envin == 'Modeled Wave Energy':
            collector='CDIP'
            site_path=os.path.dirname(os.path.dirname(os.path.dirname(csv_folder)))
            env_fold=site_path+'/environmental_data_csv'
            collec_fold=env_fold+'/'+collector
            file_out= collec_fold+"/"+station_name+'.csv'

            print('checking to see if data already downloaded')
            if not os.path.exists(env_fold): os.makedirs(env_fold)
            if not os.path.exists(collec_fold): os.makedirs(collec_fold)
            if not os.path.exists(file_out): 
                print('data not downloaded, downloading data')
                files = os.listdir(csv_folder)
                sorted_files = sorted(files)
                start=sorted_files[0]
                end=sorted_files[(len(sorted_files)-1)]
                env_df=nwis.get_record(sites=station_name, service='iv', start=start, end=end)
                env_df= env_df.reset_index()
                env_df.to_csv(file_out)
                print('USGS Gauge:', station_name, 'Data Pulled')

    

def data_binner(env_df, sr_df, binval, station_name, csv_folder, sat, envin):
    if envin == 'River Discharge':
        if sat in ['MODIS Aqua','MODIS Terra']:
            freq=binval+'h'
            collector='USGS'
            site_path=os.path.dirname(os.path.dirname(os.path.dirname(csv_folder)))
            env_fold=site_path+'/environmental_data_csv'
            collec_fold=env_fold+'/'+collector
            file_out= collec_fold+"/"+station_name+'_'+freq+'.csv'
            if not os.path.exists(file_out):
                df_sr=sr_df
                df_env=env_df
                df_env['datetime']=pd.to_datetime(df_env['datetime'], utc=True)

                #convert usgs data from pdt and pst to utc
                df_env['datetime']=df_env['datetime'].dt.tz_convert('ETC/UTC')
                df_env['datetime'] = pd.to_datetime(df_env['datetime'], errors='coerce', format='%Y-%m-%d %H:%M:%S')
                df_env['Time'] = pd.to_datetime(df_env['datetime'], format='%H:%M:%S')
                df_env['Hour'] = df_env['Time'].dt.hour
                print('Data Time Zone Converted')
                #convert discharge to cms
                df_env['Q']=df_env['00060']*0.028316847
                df_env=df_env.drop(columns='Time')
                df_env=df_env.drop(columns='00060')
                df_env=df_env.drop(columns='00060_cd')
                df_env=df_env.drop(columns='site_no')
                df_env=df_env.drop(columns='00065')
                df_env=df_env.drop(columns='00065_cd')
                df_env.index=df_env['datetime']
                df_env=df_env.resample('H').mean() #convert to hourly averages
                df_env=df_env.resample('H').mean()
                df_env=df_env.groupby(pd.Grouper(level=0, base=20, freq=freq)).mean()
                df_env=df_env.reset_index()
                df_env['Date']=df_env['datetime'].dt.date 
                df_env=df_env.drop(columns='datetime')
                df_env['Q'] = df_env.Q.shift(1)
                print('Data Binned to Overpass Time')
                lwrbnd=df_env['Q'].quantile(float(int0.value))
                upperbnd=df_env['Q'].quantile(float(int1.value))
                #subset environmental dataframe with percentiles
                df_env=df_env[df_env['Q']>lwrbnd]
                df_env=df_env[df_env['Q']<=upperbnd]
                #merge sr dataframe and environmental dataframe
                df_sr['Date']=pd.to_datetime(df_sr['Date'], errors='coerce', format='%Y-%m-%d')
                df_env['Date']=pd.to_datetime(df_sr['Date'], errors='coerce', format='%Y-%m-%d')
                df_sub=pd.merge(df_env, df_sr, on='Date')
                df_sub.to_csv(file_out)

