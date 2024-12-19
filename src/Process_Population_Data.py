import pandas as pd

# Read population data
dta_pop = pd.read_excel('population_data.xlsx', sheet_name='LI04', skiprows=[0,1,2,3])[['Geography Code', 'Population\naged 16 to 64\n 2021/2020\n(thousands)\n[note 1]']].rename(columns={'Geography Code': 'itl', 'Population\naged 16 to 64\n 2021/2020\n(thousands)\n[note 1]': 'Population'})
# Remove unecessary regions
dta_pop = dta_pop[dta_pop['itl'].str.len() <= 5]
dta_pop = dta_pop[~(dta_pop['itl'] == 'TLB')].set_index('itl')

# Import existing data set to be extended
existing_dta = pd.read_csv('Old_ITLdata_2024.csv').set_index(['level', 'itl'])

existing_dta = existing_dta.join(dta_pop).reset_index()

# Import ONS productivity data
prod_dta = pd.read_csv('ONS_productivity_updatedTAX20240906_hours_included.csv').set_index(['itl'])
# Calculate GVA
prod_dta['GVA'] = prod_dta['GVA/H current'] * prod_dta['hours'] * 52 / 1e6
# Import itl3-mca map
itl3_mca_mapping = pd.read_csv('itl3-mca_mapping.csv').rename(columns={'itl3': 'itl'}).set_index('itl')
#pd.set_option('display.max_rows', None)
# Add population data to productivity data
dta_mca = prod_dta.join(dta_pop)
# Aggregate ITL3 regions to MCA
dta_mca = itl3_mca_mapping.join(dta_mca).set_index(['year', 'mca', 'mcaname', 'itl3name', 'UK tax', 'ITL1 tax', 'parent'], append=True)
# Dummy GVA/H volume/ Change in GVA per hour whilst figuring out calculations
# Aggregate for gva and hours
dta_mca = dta_mca.groupby(['mca', 'year', 'mcaname']).sum()[['GVA', 'hours', 'Population']].reset_index().rename(columns={'GVA/H volume': 'Change in GVA per hour', 'mcaname': 'name', 'mca': 'itl'})
# Calculate GVA per Hour volume
dta_mca['GVA per Hour'] = dta_mca['GVA'] / dta_mca['hours'] / 52 * 1e6

# Calculate change in GVA per hour (volume)
dta_mca = dta_mca.sort_values(['itl', 'year'])  # Ensure correct order
# Step 1: Filter for 2019 and calculate GVA per hour for each region in 2019
gva_per_hour_2019 = dta_mca.loc[dta_mca['year'] == 2019, ['itl', 'GVA per Hour']].set_index('itl')['GVA per Hour']

# Map the 2019 values back to the main DataFrame
dta_mca['GVA per hour 2019'] = dta_mca['itl'].map(gva_per_hour_2019)

# Calculate the index relative to 2019
dta_mca['Change in GVA per hour'] = dta_mca['GVA per Hour'] / dta_mca['GVA per hour 2019'] * 100

# Add level column
dta_mca['level'] = 'MCA'
dta_mca['name'] += ' (MCA)'
# Order columns
dta_mca = dta_mca[['level', 'itl', 'name', 'year', 'GVA per Hour', 'Change in GVA per hour', 'Population']].set_index(['level', 'itl', 'name', 'year', 'GVA per Hour', 'Change in GVA per hour', 'Population']).reset_index()

dta = pd.concat([dta_mca, existing_dta]).sort_values(['level', 'year'])
dta_ratio = dta.loc[dta['itl'] == 'TLI']
dta_mca_2 = dta_ratio.loc[dta_ratio['level'] == 'MCA']
dta_itl1 = dta_ratio.loc[dta_ratio['level'] == 'ITL1']
# Merge dta_mca and dta_itl1 on 'itl' and 'year' to ensure matching rows
merged_data = pd.merge(dta_mca_2[['itl', 'year', 'Change in GVA per hour']], 
                       dta_itl1[['itl', 'year', 'Change in GVA per hour']], 
                       on=['itl', 'year'], 
                       suffixes=('_MCA', '_ITL1'))

# Calculate the ratio
merged_data['Ratio MCA to ITL1'] = merged_data['Change in GVA per hour_MCA'] / merged_data['Change in GVA per hour_ITL1']
merged_data = merged_data.drop(columns=['itl']).set_index('year')
# Print the result
dta_updated = dta.set_index('year').join(merged_data['Ratio MCA to ITL1']).reset_index()
dta_updated['Change in GVA per hour'] = dta_updated['Change in GVA per hour'] / dta_updated['Ratio MCA to ITL1']

dta = dta[dta['level'] != 'MCA']
dta_updated = dta_updated[dta_updated['level'] == 'MCA'].drop(columns=['Ratio MCA to ITL1'])

dta = pd.concat([dta, dta_updated]).sort_values(['level', 'year']).set_index(['level', 'itl', 'name', 'year'])['Population']

NI_dta = pd.read_excel('MYE23_AGE_BANDS.xlsx', sheet_name='Flat')[['area_name', 'year', 'sex', 'age_broad', 'MYE']]
# Filter for relevant data
NI_dta = NI_dta.loc[(NI_dta['year'] == 2021) &
                    (NI_dta['sex'] == 'All persons') &
                    ((NI_dta['age_broad'] == '16-39') |
                    (NI_dta['age_broad'] == '40-64'))][['area_name', 'MYE']]
print(NI_dta)
NI_dta = NI_dta.set_index('area_name').groupby('area_name').sum().rename(columns={'MYE': 'Population'})
NI_dta.index = NI_dta.index.set_names('name')
dta = dta.reset_index(['level', 'itl', 'year'])
dta.update(NI_dta)
dta = dta.reset_index()
dta = dta.set_index(['level', 'itl', 'name', 'year'])
dta.to_csv('ITL_population_2024.csv')

