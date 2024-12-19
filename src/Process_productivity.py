#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  6 14:51:19 2023

@author: reitze
"""

#Import relevant libraries
# from IPython import get_ipython
# get_ipython().run_line_magic('reset', '-f') #Reset workspace, gets rid of existing variables in memory
#import the pandas library for the data manipulations, and OS library to gain acces to the operating system
import pandas as pd 
import os
import numpy as np

# Import ITL3-mca mapping
itl = pd.read_csv('Region_Mapping_2024.csv')
variables_mca = {'A3': 'GVA/H current', 'A5': 'GVA/H volume', 'Productivity Jobs': 'jobs', 'Productivity Hours': 'hours'}
ons_mca = pd.read_excel('labourproductivitycityregions.xlsx', sheet_name = list(variables_mca.keys()), skiprows=[0,1,2,4], index_col = [0,1])

#Create output data frame which will hold all reshaped data
dta_mca = pd.DataFrame()
for key, val in variables_mca.items():    
    #drop nan rows
    tmp = ons_mca[key].dropna(axis = 'rows', how = 'all')
    
    #Create a vertical file with all values in one column
    tmp = tmp.melt(ignore_index = False)
    tmp['variable'] = tmp['variable'].str[9:].astype(int) + 2003
    if val == 'jobs':
        tmp['variable'] = tmp['variable'] - 2
    #rename year column, add to index, keep only ITL codes as index
    tmp = tmp.rename(columns = {'variable': 'year', 'value': val}).reset_index()
    tmp = tmp.loc[tmp['level_0'].apply(lambda x: str(x).lower()) != 'not available']
    tmp = tmp.set_index(['level_0', 'level_1', 'year'])
    tmp = tmp.droplevel([1])
    # #Add the reshaped data to the output frame
    dta_mca = pd.concat([dta_mca, tmp], axis = 'columns')

# Extend data set with aggregated data

variables_agg = {'Table 1': 'GVA', 'Table 8': 'deflator'}
# Import data to be aggregated
ons_agg = pd.read_excel('regionalgrossdomesticproductgdpbyallitlregions.xlsx', sheet_name=['Table 1', 'Table 8'], skiprows=[0], index_col=[0, 1 ,2])
dta_agg = pd.DataFrame()
# Import hours
dta_itl = pd.read_csv('ONS_productivity_updatedTAX20240906_hours_included.csv').set_index(['itl', 'year'])
jobsandhours = dta_itl[['hours', 'jobs']]
for key, val in variables_agg.items():  
    # Drop nan rows
    tmp = ons_agg[key].dropna(axis = 'rows', how = 'all')
    # Create a vertical file with all values in one column
    tmp = tmp.melt(ignore_index = False)
    tmp['variable'] = tmp['variable'].astype(int)
    # Rename year column, add to index, keep only ITL codes as index
    tmp = tmp.rename(columns = {'variable': 'year', 'value': val})
    tmp = tmp.set_index('year', append = True)
    tmp = tmp.droplevel([0, 2])
    # Add the reshaped data to the output frame
    dta_agg = pd.concat([dta_agg, tmp], axis = 'columns')
# Select necessary itl3 data
dta_agg = dta_agg.loc[(list(itl['itl3'].unique()), list(range(2008, 2023))), :]
jobsandhours = jobsandhours.loc[list(itl['itl3'].unique())]
dta_agg.index = dta_agg.index.set_names(['itl', 'year'])
# Calculate GVA/H current and GVA/H volume
dta_agg = dta_agg.join(jobsandhours)
# Add MCA parent
mca_map = itl.rename(columns={'mca': 'parent', 'itl3': 'itl'})[['itl', 'parent']].set_index('itl')
dta_agg = dta_agg.join(mca_map).set_index('parent', append=True)
# Get Real GVA
dta_agg['RGVA'] = dta_agg['GVA'] / dta_agg['deflator']
# Aggregate data
dta_agg = dta_agg.groupby(['parent', 'year']).sum()
# Calculate Unchained GVA/H Volume
dta_agg['Unchained GVA/H Volume'] = dta_agg['RGVA'] / dta_agg['hours'] / 52 * 1e6
# Map the 2019 values to the 'parent' column for all rows
dta_agg = dta_agg.reset_index()
gva_2019 = dta_agg.loc[dta_agg['year'] == 2019, ['parent', 'Unchained GVA/H Volume']].set_index('parent')['Unchained GVA/H Volume']
dta_agg['Unchained GVA/H Volume 2019'] = dta_agg['parent'].map(gva_2019)
# Calculate GVA/H volume
dta_agg['GVA/H volume'] = dta_agg['Unchained GVA/H Volume'] / dta_agg['Unchained GVA/H Volume 2019'] * 100

# Calculate GVA/H unsmoothed
dta_agg['GVA/H current unsmoothed'] = dta_agg['GVA'] / dta_agg['hours'] / 52 * 1e6
# Smooth to get GVA/H current
# Calculate the centered moving average over 5 years with flexible edge handling
dta_agg['GVA/H current'] = dta_agg['GVA/H current unsmoothed'].rolling(window=5, center=True, min_periods=1).mean()
dta_agg = dta_agg[['parent', 'year', 'GVA/H current', 'GVA/H volume', 'jobs', 'hours']].rename(columns={'parent': 'itl'})
# Set GVA/H current and GVA/H volume to 1dp
dta_agg['GVA/H current'] = dta_agg['GVA/H current'].round(1)
dta_agg['GVA/H volume'] = dta_agg['GVA/H volume'].round(1)
dta_agg = dta_agg.set_index(['itl', 'year'])
#Set index names
dta_mca.index = dta_mca.index.set_names(['itl', 'year'])
#select data from 2008 onwards for relevant ITL regions
dta_uk = dta_mca.loc[('UKX', list(range(2008,2023))), :]
itl3_list = list(itl['mca'].dropna().unique())
missing_mca = ['E47000012', 'E47000013', 'E47000014']
for mca in missing_mca:
    itl3_list.remove(mca)
dta_mca = dta_mca.loc[(itl3_list, list(range(2008,2023))),:]
# Update aggregated data with actual data
dta_mca = dta_agg
dta_mca = pd.concat([dta_mca, dta_uk])
#add parent region
dta_mca = dta_mca.reset_index()
dta_mca['parent'] = 'MCA'
dta_mca = dta_mca.set_index(['year', 'parent', 'itl'])

variables = {'A3': 'GVA/H current', 'A5': 'GVA/H volume', 'Productivity Jobs': 'jobs', 'Productivity Hours': 'hours'}
ons = pd.read_excel('ONS_productivity_2024.xlsx', sheet_name = list(variables.keys()), skiprows=[0,1,2,4], index_col = [0,1,2])

#Create output data frame which will hold all reshaped data
dta = pd.DataFrame()
for key, val in variables.items():    
    #drop nan rows
    tmp = ons[key].dropna(axis = 'rows', how = 'all')
    
    #Create a vertical file with all values in one column
    tmp = tmp.melt(ignore_index = False)    
    tmp['variable'] = tmp['variable'].str[9:].astype(int) + 2001
    if val == 'jobs':
        tmp['variable'] = tmp['variable'] - 2
    #rename year column, add to index, keep only ITL codes as index
    tmp = tmp.rename(columns = {'variable': 'year', 'value': val})     
    tmp = tmp.set_index('year', append = True)
    tmp = tmp.droplevel([0,2])
       
    # #Add the reshaped data to the output frame
    dta = pd.concat([dta, tmp], axis = 'columns')

del key, val, tmp #clean workspace

#Set index names
dta.index = dta.index.set_names(['itl', 'year'])
#select data from 2008 onwards for relevant ITL regions
dta = dta.loc[(slice(None), list(range(2008,2023))),:]
#add parent region
dta = dta.reset_index()

dta['parent'] = dta['itl'].apply(lambda x: 'ITL' + str(len(x) - 2).lower())
dta.loc[dta['itl'] == 'UKX', 'parent'] = 'UK'
dta_mca = dta_mca.reset_index()
dta_mca = dta_mca[dta_mca['itl'] != 'UKX']

out = pd.concat([dta, dta_mca])[['parent', 'itl', 'year', 'GVA/H current', 'GVA/H volume']].rename(columns={'parent': 'level','GVA/H current': 'GVA per Hour', 'GVA/H volume': 'Change in GVA per hour'}).set_index(['level', 'year', 'itl'])
pop = pd.read_csv('ITL_population_2024.csv', index_col=[0,1,3])
out = out.join(pop).reset_index()
out.loc[out['itl'] == 'TLN0', 'name'] = out.loc[out['itl'] == 'TLN0', 'name'] + ' (ITL2)'
out.loc[out['itl'] == 'TLG3', 'name'] = out.loc[out['itl'] == 'TLG3', 'name'] + ' (ITL2)'
out = out.loc[out['itl'] != 'TLB'].set_index(['level', 'itl', 'name', 'year']).sort_index()
print(out)

out.to_csv('Input_Data.csv')