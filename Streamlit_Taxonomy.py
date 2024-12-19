import streamlit as st
# import streamlit_antd_components as sac
# #Check out additional options, also for data display: https://nicedouble-streamlitantdcomponentsdemo-app-middmy.streamlit.app/
import pandas as pd
import graphs
import numpy as np
import textwrap
# import plotly.io as pio
import io
import time
# Streamlit-app

@st.cache_data
def load_data():
    t0 = time.time()
    data = pd.read_csv('src/Input_Data.csv', index_col = [0,1,2,3])
    itlmapping = pd.read_csv('src/Region_Mapping_2024.csv')

    print("Runtime loading data: " + str(int((time.time() - t0)*1000)) + " miliseconds")
    return data, itlmapping

@st.cache_data
def process_data(data, itlmapping, start, year, levels, region, customregion):

    t0 = time.time()

    period =  list(range(start,year+1))
    volume = 'Change in GVA per hour' #Use data in constant prices
    nominal = 'GVA per Hour' #Nominal 2019 data used by Bart is smoothed GVA per hour worked



    # '''Do this more efficienty, essentially create a new dataframe with 3 columns:
    #     start year volume, end year volume and end year nominal,
    #     divide the end year volume by start year volume and subtract 1.
    #     This gives the data we need, no need for aggregation or natural logs,
    #     perhaps no need for numpy either.
    #     See if we can combine all data in 1 dataframe, including UK average
    #     '''

    #Select productivity data from the output frame
    dta = data.loc[(slice(None), slice(None), slice(None), period), [volume, 'Population']]



    #Create a new column with the log growth of the productivity level
    dta['Log percentage change'] = np.log(dta[volume]).groupby(['level', 'itl', 'name']).diff()
    median_population = dta['Population'].median()
    dta['Population'] = dta['Population'].fillna(median_population)
     #finally calculate the growth average over the period
    #create new dataframe for the aggregates over the period
    dtaAgg = pd.DataFrame()
    dtaAgg['Population'] = dta['Population']
    dtaAgg['Average Annual log percentage change'] = dta['Log percentage change'].groupby(['level', 'itl', 'name']).mean()
    #Calculate the total growth over the period and add in new column
    dtaAgg['Log percentage change'] = dta['Log percentage change'].groupby(['level', 'itl', 'name']).sum()
    #Calculate regular percentage growth
    dtaAgg['Average Annual percentage change'] = (np.exp(dtaAgg['Average Annual log percentage change']) - 1)
    dtaAgg['Percentage change'] = (np.exp(dtaAgg['Log percentage change']) - 1)

    #Add the nominal data
    dtaAgg['GVA per hour'] = data.loc[(slice(None), slice(None), slice(None), year), nominal].droplevel('year', axis = 'index')

    #Select data to plot
    selected = itlmapping.loc[itlmapping['itl1name'].isin(region), :]
    all_selected_values = [item for level in levels for item in selected[level.lower() + 'name'].unique()]
    # Remove empty for ITL3s with no MCA parent
    all_selected_values = [x for x in all_selected_values if x == x and x is not None]
    dtaselected = pd.DataFrame()
    for level in levels:
        temp = dtaAgg.loc[(level, slice(None), all_selected_values, year),:]
        dtaselected = pd.concat([dtaselected, temp])

    #Add names names for aggregate regions and scorecard data:
    itl_dropset = {'mca': ['itl2', 'itl2name', 'itl3', 'itl3name'], 
                   'itl1': ['itl2', 'itl2name', 'itl3', 'itl3name'], 
                   'itl2': ['itl3', 'itl3name'], 
                   'itl3': []}

    levels = [level.lower() for level in levels]
    dtaselected = dtaselected.reset_index()
    concatenated_df = pd.DataFrame()
    for level in levels:
        temp = dtaselected.copy()
        itlmapping_itl = itlmapping.drop(itl_dropset[level], axis = 'columns').drop_duplicates()
        temp = temp.join(itlmapping_itl.set_index(level), on = 'itl')

        concatenated_df = pd.concat([concatenated_df, temp], ignore_index=True)
        
    dtaselected = concatenated_df
    dtaselected = dtaselected.set_index(['level', 'itl', 'name', 'year'])


    #Check custom selection of regions, and update selected data accordingly
    if customregion != None and len(customregion) > 1:
        #print(customregion)
        dtaselected = dtaselected.loc[(slice(None), slice(None), customregion, year), :]

    #Sort values according to ITL1 region
    sorter = ['Scotland', 'North East', 'North West', 'Northern Ireland', 'Yorkshire and The Humber', 'Wales', 'West Midlands', 'East Midlands', 'East', 'South West', 'South East', 'London']
    for i, v in enumerate(sorter):
        dtaselected.loc[dtaselected['itl1name'] == v, 'sorter'] = i
    del i, v, sorter

    #Sort data by the indicator for the bubble size (in this case population)
    # dtaselected = dtaselected.sort_values(by = 'pop', ascending = False)
    dtaselected = dtaselected.sort_values(by = 'sorter', ascending = True)

    #Break region names
    dtaselected = dtaselected.reset_index('name')
    dtaselected['name'] = ['<br>'.join(textwrap.wrap(x, width = 15)) for x in dtaselected['name']]
    dtaselected = dtaselected.set_index('name', append = True)

    dtaselected = dtaselected.drop(columns=['Unnamed: 0'])
    dtaselected = dtaselected.drop_duplicates()

    dtaselected = dtaselected.droplevel('year')
    dtaAgg = dtaAgg.droplevel('year')

    print("Runtime data processing: " + str(int((time.time() - t0)*1000)) + " miliseconds")
    return dtaAgg, dtaselected

def main():
    st.set_page_config(layout="wide")
    data, itlmapping = load_data()

    t0 = time.time()

    #Define sidebar

    #Sidebar logo 
    #Embed the logo as HTML. This allows the logo to also be a link, and stops Streamlit showing the 'enlarge image' icon 
    st.sidebar.html("<a href='https://lab.productivity.ac.uk' alt='The Productivity Lab'><img src='app/static/TPI_Lab_transp.png' width='200'></a>")

    #Back button
    #Embed the button as styled HTML. This stops the link opening in a new tab (like st.link_button enforces)
    st.markdown("""
        <style>
            a.btn {
                color: rgb(49, 51, 63);
                border: 1px solid rgba(49, 51, 63, 0.2);
                background-color: rgb(249, 249, 251);
                border-radius: 6px;
                padding: 8px 12px;
                text-decoration: none;
            }
            a.btn:hover {
                color: rgb(255, 75, 75);
                border: 1px solid rgb(255, 75, 75);
            }
        </style>
        """, unsafe_allow_html=True)

    st.sidebar.html("<a class='btn' href='https://lab.productivity.ac.uk/tools/uk-regional-productivity-growth/'>Back to the Productivity Lab</a>")

    #Alternative logo
    # Add an app logo. This is the new 'official' way to add logos. The logo still appears when the sidebar is collapsed (you can use 'icon_image' to specify a smaller version, if preferred). 
    # I created a rough example logo (static/logo.png) as an illustration
    # Must be 24px x 240px max and 10:1 aspect ratio
  
    st.logo("static/logo.png", link="https://lab.productivity.ac.uk/", icon_image=None)

    #Data selection tools
    st.sidebar.divider()
    st.sidebar.subheader('Select data to plot')
    year = st.sidebar.slider('Time Period:', 2008, max_value=int(max(data.index.unique(level='year'))),
        value=[2008, int(max(data.index.unique(level='year')))])
    if year[0] == year[1]:
        year = [year[0], year[0] + 1] if year[0] < int(max(data.index.unique(level='year'))) else [year[0] - 1, year[0]]
    
    color_mapping = {
        'ITL3': '#d63f3f',
        'ITL2': '#3F7CD6',
        'ITL1': '#713AB7',
        'MCA': '#3FB9B1'
    }

    # Inject custom CSS to style the selected tags
    st.markdown(f"""
        <style>
        /* Style tags for selected options */
        span[data-baseweb="tag"][aria-label*="ITL3"] {{
            background-color: {color_mapping['ITL3']} !important;
            color: white !important;
        }}
        span[data-baseweb="tag"][aria-label*="ITL2"] {{
            background-color: {color_mapping['ITL2']} !important;
            color: white !important;
        }}
        span[data-baseweb="tag"][aria-label*="ITL1"] {{
            background-color: {color_mapping['ITL1']} !important;
            color: white !important;
        }}
        span[data-baseweb="tag"][aria-label*="MCA"] {{
            background-color: {color_mapping['MCA']} !important;
            color: white !important;
        }}
        </style>
    """, unsafe_allow_html=True)

    level_options_mapping = {
    'ITL3': ['ITL1', 'ITL2', 'ITL3', 'MCA'],
    'ITL2': ['ITL1', 'ITL2', 'MCA'],
    'ITL1': ['ITL1'],
    'MCA': ['ITL1', 'MCA']
}

    # Multiselect box
    levels = st.sidebar.multiselect(
        'Geographical Aggregation Level:',
        options=['ITL3', 'ITL2', 'ITL1', 'MCA'],
        default='ITL3'
    )

    selected_regions = st.sidebar.multiselect('Select ITL1 region(s):', options = list(itlmapping['itl1name'].unique()) + ['All'], default = 'All')

    # Get unique colour options from selected levels
    available_color_levels = set(level_options_mapping[levels[0]])
    for level in levels[1:]:
        available_color_levels &= set(level_options_mapping[level])

    color_level = st.sidebar.selectbox('Select colour level:', options=sorted(available_color_levels))

    if 'All' in selected_regions or selected_regions == []:
        selected_regions = list(itlmapping['itl1name'].unique())

    if levels == []:
        levels = ['ITL3']
    
    regs = []
    for level in levels:
        regs.extend(itlmapping.loc[itlmapping['itl1name'].isin(selected_regions), level.lower() + 'name'].unique())
    # Remove empty for ITL3s with no MCA parent
    regs = [x for x in regs if x == x and x is not None]
    css = ""
    for level, name in data.reset_index()[['level', 'name']].drop_duplicates().values:
        if level not in levels:
            continue
        # Create a CSS selector for each combination of level and name
        css += f"""
        span[data-baseweb="tag"][aria-label="{name}, close by backspace"] {{
            background-color: {color_mapping[level]} !important;
            color: white !important;
        }}
        """

    # Inject the custom CSS into Streamlit
    st.markdown(f"""
        <style>
        /* Dynamic styling based on region levels and names */
        {css}
        </style>
    """, unsafe_allow_html=True)

    custom_regions = st.sidebar.multiselect('Customize selection of regions (optional):', options = regs, default = None)


    #Figure formatting tools
    st.sidebar.divider()
    st.sidebar.subheader('Configure layout')
    size = st.sidebar.slider('Figure size', min_value=0.65, max_value = 2.0, value = 0.75)
    legend = st.sidebar.toggle(label='Show legend', value=True)
    showtrend = st.sidebar.toggle(label='Show trendline', value=False)
    showlabel = st.sidebar.toggle(label='Show labels', value=False)
    population = st.sidebar.toggle(label='Toggle population bubbles', value=False)

    # download = st.sidebar.toggle(label="Enable PDF download *(slower app)*", value=False)


    # print(custom_regions)
    if custom_regions != []:
        highlight = st.sidebar.multiselect('Add label for selected regions:', options = custom_regions, default = None)
    else:
        highlight = st.sidebar.multiselect('Add label for selected regions:', options = regs, default = None)

    fixaxes = st.sidebar.toggle(label='Set axes manually', value=False)

    if fixaxes:
        xrange = st.sidebar.slider('Set X-axis range for productivity per hour', min_value=0, max_value=100,
            value=[15, 75], format = "£%d") 
        yrange = st.sidebar.slider('Set Y-axis range for productivity change', -20, max_value=20,
            value=[-3, 3], format = "%f %%") 
    else:
        xrange = None
        yrange = None

    interpolation_steps = st.sidebar.slider('Set number of frames in transitions', min_value=0, max_value=60,
            value=0, format = "%d")
    delay = st.sidebar.slider('Set delay between transitions', min_value=0, max_value=30,
            value=3, format = "%d seconds")

    #Define main content --> change header to something smaller like st.header...
    st.header('TPI Visualisation tool for UK regional productivity growth')
    # for the [ONS dataset](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/labourproductivity/datasets/subregionalproductivitylabourproductivitygvaperhourworkedandgvaperfilledjobindicesbyuknuts2andnuts3subregions) on UK regional productivity growth'


    with st.expander(label="**About this tool**", expanded=False):

        st.markdown(
            """

            ###### Developed by the [TPI Productivity Lab](https://www.productivity.ac.uk/the-productivity-lab/), this tool facilitates dynamic visualizations of regional productivity in the United Kingdom, allowing for visual comparisons of productivity across different time periods and geographic areas. Data is sourced from the June 2024 release of the [ONS dataset on sub-regional productivity](https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/labourproductivity/datasets/subregionalproductivitylabourproductivitygvaperhourworkedandgvaperfilledjobindicesbyuknuts2andnuts3subregions), which provides information on annual labour productivity. Labour productivity is measured as gross value added (GVA) per hour worked for regions in the UK, defined according to the [International Territorial Level (ITL)](https://www.ons.gov.uk/methodology/geography/ukgeographies/eurostat) definitions. The Lab has written a blog on potential applications of this tool and a demo analysis on …. *[include link to the blog, and info on the example analysis]*. For questions about this tool please send an email to tpilab@manchester.ac.uk *[Check support address]*.

            #### Interpreting the Figure: Taxonomy and Convergence

            The figure generated using this tool serves as a visual representation of regional productivity, where each point on the scatterplot represents a specific region in relation to the UK national average. The X-axis reflects labour productivity in a chosen year, measured as Gross Value Added (GVA) per hour worked. The Y-axis represents the change in productivity, adjusted for changes in prices, from a selected start year to the chosen year on the X-axis.
            Using this framework, the figure provides insights into how different regions in the UK are performing relative to the national average in terms of their productivity level and growth. Taking the UK as a reference point, each region can be categorized according to the following productivity taxonomy, based on the work of Zymek and Jones (2020):
            - **Falling Behind:** Both the region's current year productivity and its productivity growth are below the UK average.
            - **Catching Up:** The region's current year productivity is below the UK average, but its productivity growth is above the UK average.
            - **Losing Ground:** The region's current year productivity is above the UK average, but its productivity growth is below the UK average.
            - **Steaming Ahead:** Both the region's current year productivity and its productivity growth are above the UK average.

            In addition, the optional trendline provides information on whether the selected regions are converging (negative slope), or diverging (positive slope) in terms of their productivity performance.

            #### Options for Data Selection

            The top section of the left-hand side panel of the tool offers several options to customize the data plotted in the visualization. These options provide users with flexibility in defining the scope of their analysis, enabling them to focus on specific time periods, geographical areas, and levels of detail according to their research or analytical needs. The following options for data selection are available:

            **Time Period:** Users can specify the start and end years for the data they want to analyze. This allows for the exploration of productivity trends for a specific timeframe.

            **Geographical Aggregation Level (ITL):** Users can choose the level of geographical aggregation for the data. There are three ITL levels available:
            - **ITL Level 1:** This is the highest level of aggregation, encompassing the 12 English Regions and Devolved Nations of the United Kingdom.
            - **ITL Level 2:** This level offers the intermediate level of geographic aggregation with 41 regions covering the UK.
            - **ITL Level 3:** This is the lowest level of aggregation, comprising 179 regions covering the UK in more detail.

            **Select ITL1 Region(s):** Users can narrow down their analysis by selecting specific ITL1 regions. Upon selecting an ITL1 region, all underlying regions associated with that ITL1 region will be automatically included in the analysis, according to the previously chosen geographical aggregation level.

            **Customize selection of regions (optional) *requires a minimum of two regions*:** The dropdown box allows users to choose regions from a list. This list includes only those regions that can be derived from the previously chosen geographical aggregation level and the selected ITL1 regions. This ensures that users are presented with relevant options based on their previous selections.

            #### Configure Layout Options

            The bottom section of the left-hand side panel provides the following options to changes elements of the scatterplot’s layout:

            **Figure size:** Increase or decrease the size of the figure to fit your screen. This also affects the size of the PDF export.

            **Show legend:** Shows or hides the legend for the graph. The legend gives the colour coding of the aggregate ITL1 regions of which the selected regions are a part. The legend is shown by default.

            **Show trendline:** Shows or hides the OLS trendline. The trendline can be included to gauge convergence or divergence of regional productivity. The trendline is hidden by default.

            **Show labels:** Shows or hides the names for each of the selected regions. The names are hidden by default.

            **Add label for selected regions:** The names for selected regions can be added to the graph.

            **Set axes manually:** This option allows users to manually set the range for nominal productivity per hour worked on the x-axis, as well as the range for productivity growth on the y-axis. By default this option is disabled, and the axes automatically rescale dependent on the selection of the data. Manually setting the axes can be used to remove outliers from view or prevent the axes from automatically rescaling during animation.


            #### Additional Options

            The data tool shows four buttons to the right of the figure:
            - **Animate start year:** Creates a time-lapse of the figure, by incrementing the start year, leaving the end year unchanged.
            - **Animate end year:** Creates a time-lapse of the figure, by incrementing the end year, leaving the start year unchanged.
            - **Animate period:** Creates a time-lapse of the figure, by keeping the interval for productivity change constant, and incrementing both the start and end year.
            - **Download PDF:** Downloads a PDF file of the current graph.

            It is also possible to interact directly with the figure. Hover over individual data points to show the information for that region or zoom in on a specific clusters of scatter points by drawing a rectangle with the mouse. In addition, when hovering over the figure a menu the top right will appear. From this menu it is possible to select additional options such as *panning, zooming,* or *enlarging* the figure to fill the screen. Lastly, from this menu it is possible to save the figure, including the manual changes, as a png image.

            On the top-right of the application window there is an additional menu to rerun the application, change the appearance of the application (dependent on your system settings), print the current view of the application, record a screencast, and get technical information on this application.


            """
            )
    print("Runtime constructing frame: " + str(int((time.time() - t0)*1000)) + " miliseconds")


    #Experiment with buttons side by side to improve layout when the download button is visible and when we add
    #more buttons (animate start year and animate end year)


    #test this: https://nicedouble-streamlitantdcomponentsdemo-app-middmy.streamlit.app/

    # test = sac.buttons([
    #
    #         sac.ButtonsItem(label='Download PDF', icon='download'),
    #
    #         sac.ButtonsItem(label='Annimate start year', icon='film'),
    #         sac.ButtonsItem(label='Annimate end year', icon='film'),
    #         sac.ButtonsItem(label='Annimate period', icon='film'),
    #
    #
    #     ], align='center', variant='filled')
    #
    #
    # print('test is ' + test)

    col1, col2 = st.columns([6,1])


    #Add play animation button
    # with col2:  st.divider()
    with col2:  st.write("#")
    with col2:  st.write("#")
    with col2: play_start = st.button(label = 'Animate start year', type="primary", use_container_width=True)
    with col2: play_end = st.button(label = 'Animate end year', type="primary", use_container_width=True)
    with col2: play_period = st.button(label = 'Animate period', type="primary", use_container_width=True)
    with col2: download_pdf = st.button(label="Export to PDF", type="primary", use_container_width=True)

    #Create placeholder for the figure, which can be overwritten, but we need to use the container for that
    with col1: figure = st.empty()
    if play_start:
        with col1:
            progress = st.progress(0, "Period: " + str(year[0]) + " - " + str(year[1]))
        # Process and store data for each full year
        yearly_data = []
        for i in range(year[0], year[1] + 1):
            dtaAgg, dtaselected = process_data(
                data=data,
                itlmapping=itlmapping,
                start=i,
                year=year[1],
                levels=levels,
                region=selected_regions,
                customregion = custom_regions,
            )
            if i == year[1]:
                break
            yearly_data.append((dtaAgg, dtaselected))
        
        # Loop through each year to create interpolated frames
        for i in range(len(yearly_data) - 1):
            # Get the data for the current and next year
            dtaAgg_current, dtaselected_current = yearly_data[i]
            dtaAgg_next, dtaselected_next = yearly_data[i + 1]

            # Select only numeric columns for interpolation
            numeric_cols_current = dtaselected_current.select_dtypes(include=np.number)
            numeric_cols_next = dtaselected_next.select_dtypes(include=np.number)

            # Handle non-numeric columns by carrying them forward as-is
            non_numeric_cols = dtaselected_current.select_dtypes(exclude=np.number)

            for step in range(interpolation_steps):
                # Interpolation factor
                t = step / interpolation_steps

                # Interpolate only numeric columns
                dtaselected_interpolated_numeric = (1 - t) * numeric_cols_current + t * numeric_cols_next 
                # Combine back non-numeric columns with interpolated numeric columns
                dtaselected_interpolated = pd.concat([dtaselected_interpolated_numeric, non_numeric_cols], axis=1)

                # Interpolate dtaAgg similarly if needed
                dtaAgg_interpolated = (1 - t) * dtaAgg_current + t * dtaAgg_next

                # Generate the figure with interpolated data
                fig = graphs.scatter(
                    dtaAgg=dtaAgg_interpolated,
                    dtaselected=dtaselected_interpolated,
                    size=size,
                    start=year[0] + i,
                    year=year[1],
                    levels=levels,
                    highlight=highlight,
                    legend=legend,
                    showlabel=showlabel,
                    showtrend=showtrend,
                    color_level=color_level,
                    population=population,
                    xrange=xrange,
                    yrange=yrange,
                )

                # Display the interpolated frame in Streamlit
                figure.plotly_chart(fig, use_container_width=True, key=f"plot_{year[0] + i}_{step}")

                # Update progress bar
                progress.progress(((i + t) / (len(yearly_data) - 1)), f"Period: {year[0] + i} - {year[1]}")
                
                # Adjust delay for smoother transitions
                #time.sleep(delay / interpolation_steps)
            dtaAgg_current, dtaselected_current = yearly_data[i + 1]
            fig = graphs.scatter(
                    dtaAgg=dtaAgg_current, 
                    dtaselected=dtaselected_current,
                    size=size,
                    start=year[0] + i + 1,
                    year=year[1],
                    levels=levels,
                    highlight=highlight,
                    legend=legend,
                    showlabel=showlabel,
                    showtrend=showtrend,
                    color_level=color_level,
                    population=population,
                    xrange=xrange,
                    yrange=yrange,
                )
            
            figure.plotly_chart(fig, use_container_width=True, key=f"plot_{year[0] + i}")
            progress.progress(((i + 1) / (len(yearly_data) - 1)), f"Period: {year[0] + i + 1} - {year[1]}")
            time.sleep(delay)

        # Clear progress bar when done
        progress.empty()
        year = (year[1] - 1, year[1])

    elif play_end:
        with col1: progress = st.progress(0, "Period: " + str(year[0]) + " - " + str(year[1]))
        yearly_data = []
        for i in range(year[1], int(max(data.index.unique(level='year'))) + 1):
            dtaAgg, dtaselected = process_data(
                        data = data,
                        itlmapping = itlmapping,
                        start = year[0],
                        year = i,
                        levels = levels,
                        region = selected_regions,
                        customregion = custom_regions,
                        )
            yearly_data.append((dtaAgg, dtaselected))

        for i in range(len(yearly_data) - 1):
            # Get the data for the current and next year
            # Update progress bar
            #progress.progress(((i) / (len(yearly_data) - 1)), f"Period: {year[0]} - {year[1] + i}")
            dtaAgg_current, dtaselected_current = yearly_data[i]
            dtaAgg_next, dtaselected_next = yearly_data[i + 1]

            # Select only numeric columns for interpolation
            numeric_cols_current = dtaselected_current.select_dtypes(include=np.number)
            numeric_cols_next = dtaselected_next.select_dtypes(include=np.number)
            
            # Handle non-numeric columns by carrying them forward as-is
            non_numeric_cols = dtaselected_current.select_dtypes(exclude=np.number)

            for step in range(interpolation_steps):
                # Interpolation factor
                t = step / interpolation_steps

                # Interpolate only numeric columns
                dtaselected_interpolated_numeric = (1 - t) * numeric_cols_current + t * numeric_cols_next

                # Combine back non-numeric columns with interpolated numeric columns
                dtaselected_interpolated = pd.concat([dtaselected_interpolated_numeric, non_numeric_cols], axis=1)

                # Interpolate dtaAgg similarly if needed
                dtaAgg_interpolated = (1 - t) * dtaAgg_current + t * dtaAgg_next

                # Generate the figure with interpolated data
                fig = graphs.scatter(
                    dtaAgg=dtaAgg_interpolated,
                    dtaselected=dtaselected_interpolated,
                    size=size,
                    start=year[0],
                    year=year[1] + i,
                    levels=levels,
                    highlight=highlight,
                    legend=legend,
                    showlabel=showlabel,
                    showtrend=showtrend,
                    color_level=color_level,
                    population=population,
                    xrange=xrange,
                    yrange=yrange,
                )

                # Display the interpolated frame in Streamlit
                figure.plotly_chart(fig, use_container_width=True, key=f"plot_{year[1] + i}_{step}")

                # Update progress bar
                progress.progress(((i + t) / (len(yearly_data) - 1)), f"Period: {year[0]} - {year[1] + i}")
                
                # Adjust delay for smoother transitions
                #time.sleep(delay / interpolation_steps)
            dtaAgg_current, dtaselected_current = yearly_data[i + 1]
            fig = graphs.scatter(
                    dtaAgg=dtaAgg_current,
                    dtaselected=dtaselected_current,
                    size=size,
                    start=year[0],
                    year=year[1] + i + 1,
                    levels=levels,
                    highlight=highlight,
                    legend=legend,
                    showlabel=showlabel,
                    showtrend=showtrend,
                    color_level=color_level,
                    population=population,
                    xrange=xrange,
                    yrange=yrange,
                )
            
            figure.plotly_chart(fig, use_container_width=True, key=f"plot_{year[1] + i + 1}")
            progress.progress(((i + 1) / (len(yearly_data) - 1)), f"Period: {year[0]} - {year[1] + i + 1}")
            time.sleep(delay)

        # Clear progress bar when done
        progress.empty()
        year = (year[0], 2022)

    
    elif play_period and int(max(data.index.unique(level='year')) - year[1]) > 0:
        with col1: progress = st.progress(0, "Period: " + str(year[0]) + " - " + str(year[1]))
        yearly_data = []
        for i in range(0, int(max(data.index.unique(level='year')) - year[1]) + 1):
            dtaAgg, dtaselected = process_data(
                        data = data,
                        itlmapping = itlmapping,
                        start = year[0] + i,
                        year = year[1] + i,
                        levels = levels,
                        region = selected_regions,
                        customregion = custom_regions,
                        )
            yearly_data.append((dtaAgg, dtaselected))
        for i in range(len(yearly_data) - 1):
            # Get the data for the current and next year
            dtaAgg_current, dtaselected_current = yearly_data[i]
            dtaAgg_next, dtaselected_next = yearly_data[i + 1]

            # Select only numeric columns for interpolation
            numeric_cols_current = dtaselected_current.select_dtypes(include=np.number)
            numeric_cols_next = dtaselected_next.select_dtypes(include=np.number)
            
            # Handle non-numeric columns by carrying them forward as-is
            non_numeric_cols = dtaselected_current.select_dtypes(exclude=np.number)

            for step in range(interpolation_steps):
                # Interpolation factor
                t = step / interpolation_steps

                # Interpolate only numeric columns
                dtaselected_interpolated_numeric = (1 - t) * numeric_cols_current + t * numeric_cols_next

                # Combine back non-numeric columns with interpolated numeric columns
                dtaselected_interpolated = pd.concat([dtaselected_interpolated_numeric, non_numeric_cols], axis=1)

                # Interpolate dtaAgg similarly if needed
                dtaAgg_interpolated = (1 - t) * dtaAgg_current + t * dtaAgg_next

                # Generate the figure with interpolated data
                fig = graphs.scatter(
                    dtaAgg=dtaAgg_interpolated,
                    dtaselected=dtaselected_interpolated,
                    size=size,
                    start=year[0] + i,
                    year=year[1] + i,
                    levels=levels,
                    highlight=highlight,
                    legend=legend,
                    showlabel=showlabel,
                    showtrend=showtrend,
                    color_level=color_level,
                    population=population,
                    xrange=xrange,
                    yrange=yrange,
                )

                # Display the interpolated frame in Streamlit
                figure.plotly_chart(fig, use_container_width=True, key=f"plot_{year[0] + i}_{step}")

                # Update progress bar
                progress.progress(((i + t) / (len(yearly_data) - 1)), f"Period: {year[0] + i} - {year[1] + i}")
                
                # Adjust delay for smoother transitions
                #time.sleep(delay / interpolation_steps)
            dtaAgg_current, dtaselected_current = yearly_data[i + 1]
            fig = graphs.scatter(
                    dtaAgg=dtaAgg_current,
                    dtaselected=dtaselected_current,
                    size=size,
                    start=year[0] + i + 1,
                    year=year[1] + i + 1,
                    levels=levels,
                    highlight=highlight,
                    legend=legend,
                    showlabel=showlabel,
                    showtrend=showtrend,
                    color_level=color_level,
                    population=population,
                    xrange=xrange,
                    yrange=yrange,
                )
            figure.plotly_chart(fig, use_container_width=True, key=f"plot_{year[0] + i}")
            progress.progress(((i + 1) / (len(yearly_data) - 1)), f"Period: {year[0] + i + 1} - {year[1] + i + 1}")
            time.sleep(delay)

        progress.empty()
        year = (year[0] + int(max(data.index.unique(level='year')) - year[1]), year[1] + int(max(data.index.unique(level='year')) - year[1]))
    # else:
    with figure.container():
        dtaAgg, dtaselected = process_data(
                data = data,
                itlmapping = itlmapping,
                start = year[0],
                year = year[1],
                levels = levels,
                region = selected_regions,
                customregion = custom_regions,
                )

        t0 = time.time()

        fig = graphs.scatter(dtaAgg = dtaAgg,
                        dtaselected = dtaselected,
                        size = size,
                        start = year[0],
                        year = year[1],
                        levels = levels,
                        highlight = highlight,
                        legend = legend,
                        showlabel = showlabel,
                        showtrend = showtrend,
                        color_level = color_level,
                        population = population,
                        xrange = xrange,
                        yrange = yrange,
                        )

        st.plotly_chart(fig, use_container_width=True)
        print("Runtime constructing figure: " + str(int((time.time() - t0)*1000)) + " miliseconds")

    if download_pdf:
        t0 = time.time()
        # Create an in-memory buffer
        buffer = io.BytesIO()
    
        try:
            print('Saving fig')
            # Save the figure as a PDF to the buffer
            fig.write_image(file=buffer, format="pdf")
            print('Saved')
            # Reset buffer position to the start
            buffer.seek(0)
            # Provide the PDF file for download
            st.download_button(
                label="Click here to download your plot as PDF",
                data=buffer,
                file_name="figure.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
            print("PDF generated successfully!")
            
        except Exception as e:
            print(f"An error occurred: {e}")
        
        finally:
            buffer.close()  # Ensure the buffer is properly closed
        print("Runtime pdf buffering: " + str(int((time.time() - t0)*1000)) + " miliseconds")




    print(" ")

if __name__ == '__main__':
    main()
