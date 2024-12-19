import pandas as pd

itl_mapping = pd.read_csv('ITLmapping_2024.csv').set_index(['itl3', 'itl3name'])
mca_itl3_mapping = pd.read_csv('itl3-mca_mapping.csv').rename(columns={'CAUTH24CD': 'mca', 'CAUTH24NM':'mcaname', 'ITL321CD':'itl3', 'ITL321NM': 'itl3name'}).set_index(['itl3', 'itl3name'])

joined_mapping = itl_mapping.join(mca_itl3_mapping).reset_index().drop(columns=['Unnamed: 0']).set_index(['itl1', 'itl2', 'mca', 'itl3', 'itl1name', 'itl2name', 'mcaname', 'itl3name']).reset_index()

joined_mapping['mcaname'] += ' (MCA)'
print(joined_mapping)
joined_mapping.to_csv('ITLmapping_2024_with_MCA.csv')