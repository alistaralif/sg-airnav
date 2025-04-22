import math
import base64
import dash
import pandas as pd
from dash import dcc, html, Input, Output, State
import plotly.graph_objects as go
from matplotlib.colors import to_rgba


#region Functions

def parse_coordinates(coordinates):
    latitudes, longitudes = [], []
    for lat_str, lon_str in coordinates:
        lat_str_clean = lat_str[:-1]
        lon_str_clean = lon_str[:-1]
        
        lat_deg = int(lat_str_clean[:2])
        lat_min = int(lat_str_clean[2:4])
        lat_sec = int(lat_str_clean[4:6])
        
        lon_deg = int(lon_str_clean[:3])
        lon_min = int(lon_str_clean[3:5])
        lon_sec = int(lon_str_clean[5:7])
        
        lat = lat_deg + lat_min / 60 + lat_sec / 3600
        lon = lon_deg + lon_min / 60 + lon_sec / 3600
        
        if lat_str.endswith('S'):
            lat *= -1
        if lon_str.endswith('W'):
            lon *= -1
        
        latitudes.append(round(lat, 6))
        longitudes.append(round(lon, 6))
    
    return latitudes, longitudes


def round_latlon(latitude, longitude):
    """Rounds decimal degrees latitude and longitude to 5 decimal places. """
    return round(latitude, 5), round(longitude, 5)

def decimal_to_dms_str(lat, lon):
    def to_dms(val, is_lat):
        direction = 'N' if is_lat else 'E'
        if val < 0:
            direction = 'S' if is_lat else 'W'
        val = abs(val)
        deg = int(val)
        minutes_float = (val - deg) * 60
        minutes = int(minutes_float)
        seconds = int(round((minutes_float - minutes) * 60))

        # Correct rollover
        if seconds == 60:
            seconds = 0
            minutes += 1
            if minutes == 60:
                minutes = 0
                deg += 1

        return f"{deg:02d}{minutes:02d}{seconds:02d}{direction}"

    return f"({to_dms(lat, True)}, {to_dms(lon, False)})"

def css_to_rgba(color: str, opacity: float) -> str:
    """
    Converts a CSS color name (e.g. 'skyblue') or hex string to an rgba() string with the given opacity.

    Parameters:
    - color: CSS color name or hex (e.g. 'orange', '#ffcc00')
    - opacity: Float between 0.0 and 1.0

    Returns:
    - 'rgba(R, G, B, A)' formatted string
    """
    r, g, b, _ = to_rgba(color)
    r, g, b = int(r * 255), int(g * 255), int(b * 255)
    return f'rgba({r}, {g}, {b}, {opacity})'

def add_sector(fig, name, coordinates, fillcolor, linecolor, opacity=0.3, linewidth=1, 
               legendgroup=None, legendgrouptitle_text=None, legendrank=None, showlegend=True):
    """
    Adds an airspace sector polygon to a Plotly map.

    Parameters:
    - fig: Plotly figure object
    - name: Legend label
    - coordinates: List of (lat_dms, lon_dms) tuples (e.g., '013112N', '1035936E')
    - fillcolor: CSS color name or rgba() string
    - linecolor: Polygon outline color
    - opacity: Polygon fill transparency (0.0 - 1.0)
    - linewidth: Outline thickness
    - showlegend: Whether to show in legend
    - legendgroup: Optional legend group
    - legendrank: Controls order in legend (lower = higher up)
    - legendgrouptitle_text: Optional group title for legend section
    """

    # Convert DMS to decimal degrees
    lat_list, lon_list = parse_coordinates(coordinates)

    # Round coordinates
    lat_list = [round_latlon(lat, lon)[0] for lat, lon in zip(lat_list, lon_list)]
    lon_list = [round_latlon(lat, lon)[1] for lat, lon in zip(lat_list, lon_list)]

    hovertext = [
        f"{name}<br>{decimal_to_dms_str(lat, lon)}<br>#{i}"
        for i, (lat, lon) in enumerate(zip(lat_list, lon_list))
    ]

    # Convert CSS color to rgba if needed
    if ',' not in fillcolor and not fillcolor.startswith('rgba'):
        fillcolor = css_to_rgba(fillcolor, opacity)

    # Add the sector polygon trace
    fig.add_trace(go.Scattermap(
        lat=lat_list,
        lon=lon_list,
        mode='lines',
        fill='toself',
        fillcolor=fillcolor,
        line=dict(color=linecolor, width=linewidth),
        name=name,
        legendgroup=legendgroup,
        legendgrouptitle_text=legendgrouptitle_text,
        legendrank=legendrank,
        text=hovertext,
        hoverinfo='none',
        hovertemplate='%{fullData.name}<extra></extra>',     #text
        showlegend=showlegend,
        customdata=['SECTOR']
    ))

def image_to_html_img_tag(filepath, width=160):
    """
    Converts a PNG image into an HTML <img> tag encoded in base64.

    Parameters:
    - filepath: Path to the PNG file
    - width: Width of the displayed image in pixels

    Returns:
    - HTML string of the <img> tag
    """
    with open(filepath, 'rb') as f:
        encoded = base64.b64encode(f.read()).decode()
    return f'<img src="data:image/png;base64,{encoded}" width="{width}"/>'


def add_rectangle_with_label(fig, center_lat, center_lon, width_km, height_km, text, fontsize=12,line_color='black', fill_color='rgba(255,255,255,1)', text_color='black'):
    """
    Adds a rectangle and text label at its center to a Plotly map.

    Parameters:
    - fig: The Plotly figure object
    - center_lat, center_lon: Center of the rectangle (in degrees)
    - width_km, height_km: Width and height of the rectangle (in kilometers)
    - text: Label to display inside the rectangle
    - line_color: Border color of the rectangle
    - fill_color: Fill color of the rectangle (transparent recommended)
    - text_color: Text font color
    """

    # Approximate degree offsets
    deg_per_km_lat = 1 / 110.574  # constant
    deg_per_km_lon = 1 / (111.320 * math.cos(math.radians(center_lat)))  # varies with latitude

    dlat = height_km * deg_per_km_lat / 2
    dlon = width_km * deg_per_km_lon / 2

    # Rectangle corners (clockwise)
    lats = [
        center_lat + dlat,
        center_lat + dlat,
        center_lat - dlat,
        center_lat - dlat,
        center_lat + dlat  # close the loop
    ]
    lons = [
        center_lon - dlon,
        center_lon + dlon,
        center_lon + dlon,
        center_lon - dlon,
        center_lon - dlon
    ]

    # Add rectangle polygon
    fig.add_trace(go.Scattermap(
        lat=lats,
        lon=lons,
        mode='lines',
        fill='toself',
        fillcolor=fill_color,
        line=dict(color=line_color, width=2),
        name='',
        hoverinfo='skip',
        showlegend=False,
        customdata=['FIR']
    ))

    # Add center label
    fig.add_trace(go.Scattermap(
        lat=[center_lat],
        lon=[center_lon],
        mode='text',
        text=[text],
        name='',
        textfont=dict(size=fontsize, color=text_color, family='Open Sans Bold, Verdana Bold, Arial Black, sans-serif'),
        textposition='middle center',
        showlegend=False,
        hoverinfo='skip',
        customdata=['FIR']
    ))


def add_FIR(fig, name, coordinates, linecolor='black', linewidth=1.5, legendgroup="FIR", legendrank=1, showlegend=True, legendgrouptitle_text="FIR", label=True, label_lat=None, label_lon=None):
    """
    Adds an FIR (Flight Information Region) boundary polygon to a Plotly map.

    Parameters:
    - fig: Plotly figure object
    - name: Name of the FIR to display in the legend
    - coordinates: List of (lat_dms, lon_dms) tuples in DMS format (e.g., '011543N', '1032139E')
    - linecolor: Outline color of the FIR boundary (default: 'black')
    - linewidth: Thickness of the FIR boundary line (default: 1.5)
    - legendgroup: Legend group name for grouping traces (default: 'FIR')
    - legendrank: Rank to control order in the legend (default: 1)
    - showlegend: Whether to show the trace in the legend (default: True)
    - legendgrouptitle_text: Title to group legend entries (default: 'FIR')
    """
    
    lat_list, lon_list = parse_coordinates(coordinates)
    hovertext = [
        f"{name}<br>{decimal_to_dms_str(lat, lon)}<br>#{i}"
        for i, (lat, lon) in enumerate(zip(lat_list, lon_list))
    ]
    
    fig.add_trace(go.Scattermap(
        lat=lat_list,
        lon=lon_list,
        # mode='markers+lines',   # Debugging
        # hovertemplate='%{text}<extra></extra>', # Set to text for debugging
        mode='lines',   # Production
        hovertemplate='%{fullData.name}<extra></extra>',   # Set to fullData.name for production
        fill='none',
        line=dict(color=linecolor, width=linewidth),
        name=name,
        legendgroup=legendgroup,
        legendrank=legendrank,
        legendgrouptitle_text=legendgrouptitle_text,
        hoverinfo= 'name',
        text=hovertext,
        showlegend=showlegend,
        customdata=['FIR']
    ))
    if label == True:
        # Remove "FIR" from the name for the label
        name_cleaned = name.replace("FIR", "").strip()
        fontsize = 15   
        
        # Add text label
        fig.add_trace(go.Scattermap(
            lat=[label_lat],  # Use the first coordinate for label
            lon=[label_lon],  # Use the first coordinate for label
            mode='markers+text',
            name=name,
            text="FIR<br>"+ name_cleaned,
            textfont=dict(size=fontsize, color='black', family='Open Sans Bold, Verdana Bold, Arial Black, sans-serif'),
            textposition='top center',
            marker=dict(size=30, symbol='x'),
            legendgroup=legendgroup,
            hoverinfo='none',
            showlegend=False,
        ))

    
def add_airport(fig, name, code, lat, lon, color, size, legendgroup, showlegend=True):
    """
    Adds an airport marker with a text label and hover popup.
    
    Parameters:
    - fig: the plotly figure object
    - name: full airport name (e.g., "Seletar Airport")
    - code: ICAO code (e.g., "WSSL")
    - lat, lon: coordinates
    - color: marker color
    - size: marker size
    - legendgroup: group name for legend grouping
    - showlegend: whether to display this item in the legend
    """
    fig.add_trace(go.Scattermap(
        lat=[lat],
        lon=[lon],
        mode='markers+text',
        marker=dict(size=size, color=color, symbol='circle'),
        textposition='top right',
        name=f'{name} ({code})',
        hovertext=code,
        legendgroup=legendgroup,
        legendgrouptitle_text=f"<b>{name}<b>",
        showlegend=showlegend,
        customdata=['static'],
        hovertemplate='📍 %{fullData.name}<extra></extra>'
    ))

def add_runway(fig, name, lat_list, lon_list, fillcolor, linecolor, linewidth, legendgroup, legendgrouptitle_text = None, showlegend=True, ):
    """
    Adds a filled polygon to represent a runway.
    
    Parameters:
    - fig: the plotly figure object
    - name: runway label (e.g., "RWY 03/21")
    - lat_list, lon_list: lists of coordinates outlining the runway
    - fillcolor: polygon fill
    - linecolor: boundary line color
    - linewidth: boundary line width
    - legendgroup: group name for legend grouping
    - showlegend: whether to display this item in the legend
    """
    fig.add_trace(go.Scattermap(
        lat=lat_list,
        lon=lon_list,
        mode='lines',
        fill='toself',
        fillcolor=fillcolor,
        line=dict(color=linecolor, width=linewidth),
        name=name,
        legendgroup=legendgroup,
        legendgrouptitle_text=legendgrouptitle_text,
        showlegend=showlegend,
        customdata=['static']
    ))

def add_waypoint(fig, name, coordinates, color='royalblue',legendgrouptitle_text= None):
    """
    Adds a waypoint marker to the map.
    
    Parameters:
    - fig: Plotly figure object
    - name: Waypoint name (e.g., "WSSS")
    - coordinates: Tuple of (latitude, longitude)
    """
    if coordinates == ('',''):
        lat, lon = [None], [None]
        hovertext = [None]
    else:
        lat, lon = parse_coordinates([coordinates])
        hovertext = [decimal_to_dms_str(lat[0], lon[0])]
    
    # hovertext = [
    #     f"{name}<br>{decimal_to_dms_str(lat, lon)}<br>#{i}"
    #     for i, (lat, lon) in enumerate(zip(lat_list, lon_list))
    # ]
    
    fig.add_trace(go.Scattermap(
        lat=lat,
        lon=lon,
        mode='markers',
        marker=dict(size=waypoint_marker_size, color= color),
        textposition='top right',
        name=name,
        text=hovertext,
        hovertemplate='%{text}',     #fullData.name
        # legendgroup='Waypoints',
        legendgrouptitle_text=legendgrouptitle_text,
        showlegend=True,
        customdata=['WAYPOINT'],
    ))
    
#endregion

########## -------------------------------------------------------------------------------------------------------------------------- ##########

# RWY customisation
rwy_width = 1.5
airport_marker_size = 11
color_airport = 'steelblue'
color_rwy = 'dodgerblue'
color_rwy_fill = 'rgba(0, 0, 255, 0.1)'
color_rwy_inactive = 'red'
color_rwy_inactive_fill = 'rgba(255, 0, 0, 0.7)'

# Other customisation
normal_waypoint_marker_size = 9
holding_dme_waypoint_marker_size = 12

# Version info
version = '1.4.1'   # Toggling layers will reset map view. Much better performance compared to 1.4.0, especially with waypoints toggled. 


# Dash app
app = dash.Dash(__name__)
fig = go.Figure()

#region Singapore FIR Sectors
from aerodromes import SG_FIR_sector1_coordinates, SG_FIR_sector2_coordinates, SG_FIR_sector3_coordinates, SG_FIR_sector4_coordinates
from aerodromes import SG_FIR_sector5_coordinates, SG_FIR_sector6_coordinates, SG_FIR_sector7_coordinates, SG_FIR_sector8_coordinates

# Sector 1
add_sector(
    fig=fig,
    name='Sector 1',
    coordinates=SG_FIR_sector1_coordinates,
    fillcolor='mediumslateblue',
    linecolor='grey',
    opacity=0.3,
    linewidth=1,
    legendgroup='SG FIR',
    legendgrouptitle_text='<b>Singapore FIR Sectors</b>',
    legendrank=2,
    showlegend=True
)

# Sector 2
add_sector(
    fig=fig,
    name='Sector 2',
    coordinates=SG_FIR_sector2_coordinates,
    fillcolor='aqua',
    linecolor='grey',
    opacity=0.3,
    linewidth=1,
    legendgroup='SG FIR',
    showlegend=True
)

# Sector 3
add_sector(
    fig=fig,
    name='Sector 3',
    coordinates=SG_FIR_sector3_coordinates,
    fillcolor='violet',
    linecolor='grey',
    opacity=0.3,
    linewidth=1,
    legendgroup='SG FIR',
    showlegend=True
)

# Sector 4
add_sector(
    fig=fig,
    name='Sector 4',
    coordinates=SG_FIR_sector4_coordinates,
    fillcolor='yellow',
    linecolor='grey',
    opacity=0.3,
    linewidth=1,
    legendgroup='SG FIR',
    showlegend=True
)

# Sector 5
add_sector(
    fig=fig,
    name='Sector 5',
    coordinates=SG_FIR_sector5_coordinates,
    fillcolor='cornflowerblue',
    linecolor='grey',
    opacity=0.3,
    linewidth=1,
    legendgroup='SG FIR',
    showlegend=True
)

# Sector 6
add_sector(
    fig=fig,
    name='Sector 6',
    coordinates=SG_FIR_sector6_coordinates,
    fillcolor='lightgreen',
    linecolor='grey',
    opacity=0.3,
    linewidth=1,
    legendgroup='SG FIR',
    showlegend=True
)

# Sector 7
add_sector(
    fig=fig,
    name='Sector 7',
    coordinates=SG_FIR_sector7_coordinates,
    fillcolor='lightskyblue',
    linecolor='grey',
    opacity=0.3,
    linewidth=1,
    legendgroup='SG FIR',
    showlegend=True
)

# Sector 8
add_sector(
    fig=fig,
    name='Sector 8',
    coordinates=SG_FIR_sector8_coordinates,
    fillcolor='navajowhite',
    linecolor='grey',
    opacity=0.4,
    linewidth=1,
    legendgroup='SG FIR',
    showlegend=True
)

#endregion

#region FIR boundaries
from aerodromes import SG_FIR_coordinates, KL_FIR_vested1_coordinates, KL_FIR_vested2_coordinates, JAKARTA_FIR_delegated_coordinates
from aerodromes import KL_FIR_coordinates, BKK_FIR_coordinates, PP_FIR_coordinates, HCM_FIR_coordinates, KOTA_KINABALU_FIR_coordinates, UJUNG_PANDANG_FIR, JKT_FIR_coordinates

# Kuala Lumpur FIR
add_FIR(fig, 'KUALA LUMPUR FIR (GND/SEA - FL150)', KL_FIR_vested1_coordinates, linecolor='grey', linewidth=1.5, legendgroup='FIR', legendrank=2, showlegend=True, label=False)
add_FIR(fig, 'KUALA LUMPUR FIR (GND/SEA - FL200)', KL_FIR_vested2_coordinates, linecolor='grey', linewidth=1.5, legendgroup='FIR', legendrank=2, showlegend=True, label=False)
add_FIR(fig, 'KUALA LUMPUR FIR', KL_FIR_coordinates, linecolor='black', linewidth=1.5, legendgroup='FIR', legendrank=2, showlegend=True, label_lat=6.5, label_lon=96.5)

# Bangkok FIR
add_FIR(fig, 'BANGKOK FIR', BKK_FIR_coordinates, linecolor='black', linewidth=1.5, legendgroup='FIR', legendrank=3, showlegend=True, label_lat=9.5, label_lon=101)

# Phnom Penh FIR
add_FIR(fig, 'PHNOM PENH FIR', PP_FIR_coordinates, linecolor='black', linewidth=1.5, legendgroup='FIR', legendrank=4, showlegend=True, label_lat=12, label_lon=104.5)

# Ho Chi Minh FIR
add_FIR(fig, 'HO CHI MINH FIR', HCM_FIR_coordinates, linecolor='black', linewidth=1.5, legendgroup='FIR', legendrank=5, showlegend=True, label_lat=8, label_lon=107.5)

# Kota Kinabalu FIR
add_FIR(fig, 'KOTA KINABALU FIR', KOTA_KINABALU_FIR_coordinates, linecolor='black', linewidth=1.5, legendgroup='FIR', legendrank=6, showlegend=True, label_lat=2.5, label_lon=113)

# Ujung Pandang FIR
add_FIR(fig, 'UJUNG PANDANG FIR', UJUNG_PANDANG_FIR, linecolor='black', linewidth=1.5, legendgroup='FIR', legendrank=7, showlegend=True, label_lat=-2, label_lon=115.5)

# Jakarta FIR
add_FIR(fig, 'JAKARTA FIR (DELEGATED)', JAKARTA_FIR_delegated_coordinates, linecolor='grey', linewidth=1.5, legendgroup='FIR', legendrank=8, showlegend=True, label=False)
add_FIR(fig, 'JAKARTA FIR', JKT_FIR_coordinates, linecolor='black', linewidth=1.5, legendgroup='FIR', legendrank=8, showlegend=True, label_lat=-1.75, label_lon=102.5)

# Singapore FIR
add_FIR(fig, 'SINGAPORE FIR', SG_FIR_coordinates, linecolor='black', linewidth=1.5, legendgroup='FIR', legendgrouptitle_text= '<b>FIRs</b>',legendrank=1, showlegend=True, label_lat=6.5, label_lon=111)


#endregion

#region Airports and runways

#region Singapore
from aerodromes import WSSS_lat, WSSS_lon, WSSL_lat, WSSL_lon, WSAP_lat, WSAP_lon, WSAT_lat, WSAT_lon, WSAG_lat, WSAG_lon

add_airport(fig, 'Singapore Changi Airport', 'WSSS', WSSS_lat, WSSS_lon, color_airport, airport_marker_size, 'changi')
add_airport(fig, 'Seletar Airport', 'WSSL', WSSL_lat, WSSL_lon, color_airport, airport_marker_size, 'seletar')
add_airport(fig, 'Paya Lebar Air Base', 'WSAP', WSAP_lat, WSAP_lon, color_airport, airport_marker_size, 'payalebar')
add_airport(fig, 'Tengah Air Base', 'WSAT', WSAT_lat, WSAT_lon, color_airport, airport_marker_size, 'tengah')
add_airport(fig, 'Sembawang Air Base', 'WSAG', WSAG_lat, WSAG_lon, color_airport, airport_marker_size, 'sembawang')

# Add runways

from aerodromes import lat_list_WSSS_02L, lon_list_WSSS_02L, lat_list_WSSS_02C, lon_list_WSSS_02C, lat_list_WSSS_02R, lon_list_WSSS_02R
add_runway(fig, 'RWY 02L/20R', lat_list_WSSS_02L, lon_list_WSSS_02L, color_rwy_fill, color_rwy, rwy_width, 'changi')
add_runway(fig, 'RWY 02C/20C', lat_list_WSSS_02C, lon_list_WSSS_02C, color_rwy_fill, color_rwy, rwy_width, 'changi')
add_runway(fig, 'RWY 02R/20L', lat_list_WSSS_02R, lon_list_WSSS_02R, color_rwy_inactive_fill, color_rwy_inactive, rwy_width, 'changi')

from aerodromes import lat_list_WSSL_03, lon_list_WSSL_03
add_runway(fig, 'RWY 03/21', lat_list_WSSL_03, lon_list_WSSL_03, color_rwy_fill, color_rwy, rwy_width, 'seletar')

from aerodromes import lat_list_WSAP_02, lon_list_WSAP_02
add_runway(fig, 'RWY 02/20', lat_list_WSAP_02, lon_list_WSAP_02, color_rwy_inactive_fill, color_rwy_inactive, rwy_width, 'payalebar')

from aerodromes import lat_list_WSAT_18, lon_list_WSAT_18, lat_list_WSAT_36, lon_list_WSAT_36
add_runway(fig, 'RWY 18/36', lat_list_WSAT_18, lon_list_WSAT_18, color_rwy_inactive_fill, color_rwy_inactive, rwy_width, 'tengah')
add_runway(fig, 'Military Airstrip', lat_list_WSAT_36, lon_list_WSAT_36, color_rwy_inactive_fill, color_rwy_inactive, rwy_width, 'tengah')

from aerodromes import lat_list_WSAG_04, lon_list_WSAG_04, lat_list_WSAG_H05, lon_list_WSAG_H05
add_runway(fig, 'RWY 04/22', lat_list_WSAG_04, lon_list_WSAG_04, color_rwy_inactive_fill, color_rwy_inactive, rwy_width, 'sembawang')
add_runway(fig, 'RWY H05/H23', lat_list_WSAG_H05, lon_list_WSAG_H05, color_rwy_inactive_fill, color_rwy_inactive, rwy_width, 'sembawang')

from aerodromes import lat_list_sudong_09, lon_list_sudong_09
add_runway(
    fig=fig,
    name='RWY 09/27',
    lat_list=lat_list_sudong_09,
    lon_list=lon_list_sudong_09,
    fillcolor=color_rwy_inactive_fill,
    linecolor=color_rwy_inactive,
    linewidth=rwy_width,
    legendgroup='sudong',
    legendgrouptitle_text = '<b>Pulau Sudong Military Airstrip</b>',
    showlegend=True
)

#endregion

#region Malaysia
from aerodromes import WMKJ_lat, WMKJ_lon

add_airport(fig, 'Senai Intl Airport', 'WMKJ', WMKJ_lat, WMKJ_lon, color_airport, airport_marker_size, 'senai')

from aerodromes import lat_list_WMKJ_16, lon_list_WMKJ_16
add_runway(fig, 'RWY 16/34', lat_list_WMKJ_16, lon_list_WMKJ_16, color_rwy_fill, color_rwy, rwy_width, 'senai')

#endregion

#region Indonesia
from aerodromes import WIDD_lat, WIDD_lon, WIDN_lat, WIDN_lon, WIDT_lat, WIDT_lon

add_airport(fig, 'Hang Nadim Intl Airport', 'WIDD', WIDD_lat, WIDD_lon, color_airport, airport_marker_size, 'hangnadim')
add_airport(fig, 'Raja Haji Fisabilillah Intl Airport', 'WIDN', WIDN_lat, WIDN_lon, color_airport, airport_marker_size, 'tanjungpinang')
add_airport(fig, 'Raja Haji Abdullah Airport', 'WIDT', WIDT_lat, WIDT_lon, color_airport, airport_marker_size, 'tanjungbalai')

from aerodromes import lat_list_WIDD_04, lon_list_WIDD_04, lat_list_WIDN_04, lon_list_WIDN_04, lat_list_WIDT_09, lon_list_WIDT_09
add_runway(fig, 'RWY 04/22', lat_list_WIDD_04, lon_list_WIDD_04, color_rwy_fill, color_rwy, rwy_width, 'hangnadim')
add_runway(fig, 'RWY 04/22', lat_list_WIDN_04, lon_list_WIDN_04, color_rwy_fill, color_rwy, rwy_width, 'tanjungpinang')
add_runway(fig, 'RWY 09/27', lat_list_WIDT_09, lon_list_WIDT_09, color_rwy_fill, color_rwy, rwy_width, 'tanjungbalai')

#endregion

#region Other popular airports

airports = pd.read_csv('airports.csv')

for idx, apt in airports.iterrows():
    name = apt['Name']
    icao = apt['ICAO']
    lat, lon = apt['Latitude'], apt['Longitude']
    add_airport(fig, name, icao, lat, lon, color_airport, airport_marker_size, icao)


#endregion

# Add notes for restricted/military runways
add_runway(
    fig=fig,
    name='Red RWY: Restricted/Military',
    lat_list=[None],
    lon_list=[None],
    fillcolor=color_rwy_inactive_fill,
    linecolor=color_rwy_inactive,
    linewidth=rwy_width,
    legendgroup='note',
    legendgrouptitle_text = '<b>Note:</b>',
    showlegend=True
)

#endregion

#region Add STARs and SIDs
from aerodromes import STARs, SIDs, STAR_SID_waypoints, runway_procedures

for rwy, procs in runway_procedures.items():
    for proc_type, proc_dict in [("STARs", STARs), ("SIDs", SIDs)]:
        for proc_name in procs[proc_type]:
            if proc_name in proc_dict:
                waypoints = proc_dict[proc_name]
                coords = [STAR_SID_waypoints[wp] for wp in waypoints if wp in STAR_SID_waypoints]
                if coords:
                    lat_list, lon_list = parse_coordinates(coords)
                    fig.add_trace(go.Scattermap(
                        lat=lat_list,
                        lon=lon_list,
                        mode='lines+markers',
                        name=proc_name,
                        visible=False,
                        legendgroup=proc_name,
                        legendgrouptitle_text=f"<b>{proc_type}</b>" if "ARAMA" in proc_name 
                                                            or "ANITO" in proc_name 
                                                            else '',
                        customdata=[rwy, proc_type],
                        hoverinfo='name+text',
                        text=waypoints,
                        line=dict(width=2, color= 'salmon' if proc_type == "STARs" else 'mediumseagreen')
                    ))
#endregion

# Add a version info trace to legend
fig.add_trace(go.Scattermap(
    lat=[None], lon=[None], mode='lines', line=dict(color='black', width=2),
    name=f'🗺️ map version: {version}', showlegend=True, hoverinfo='skip', legendgroup='note', 
))

#region Waypoints
from aerodromes import combined_waypoints

entry_exit_wpts = ['KEXAS', 'PASPU', 'REMES', 'VAMPO']          # ENTRY AND EXIT GATES
holding_wpts = ['NYLON', 'KEXAS', 'REMES', 'BOBAG', 'VAMPO']    # Holding Fix - AIP SINGAPORE 20 FEB 2025
dme_wpts = ['BTM', 'PU', 'SJ', 'TPG', 'VJB', 'VMR', 'VTK']


for waypoint_name, waypoint_coordinates in combined_waypoints.items():
    # Waypoints distinction
    waypoint_marker_size = normal_waypoint_marker_size
    if waypoint_name == 'ABVIP':    # Set legend title for first waypoint
        add_waypoint(fig, waypoint_name, waypoint_coordinates, legendgrouptitle_text='<b>Waypoints</b>')
        
    elif waypoint_name in entry_exit_wpts or waypoint_name in holding_wpts:
        # Highlight entry/exit gates and holding fix   
        waypoint_marker_size = holding_dme_waypoint_marker_size
        add_waypoint(fig, waypoint_name, waypoint_coordinates, color='orangered')
        
    elif waypoint_name in dme_wpts:
        # Highlight DME waypoints
        waypoint_marker_size = holding_dme_waypoint_marker_size
        add_waypoint(fig, waypoint_name, waypoint_coordinates, color='orange')
        
    else:   # Normal waypoints
        add_waypoint(fig, waypoint_name, waypoint_coordinates)

add_waypoint(fig, name= 'Red: Holding Fix',  color= 'orangered', coordinates= ('',''), legendgrouptitle_text='<b>Note:</b>')
add_waypoint(fig, name= 'Orange: DME', color= 'orange', coordinates= ('',''))

#endregion

#region Map and Dash layout

fig.update_layout(
    map=dict(
        style="carto-positron",
        center=dict(lat=WSSS_lat + 0.5, lon=WSSS_lon),
        zoom=6.5
    ),
    width=1700,
    height=780,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
    legend=dict(
        title='<b>Legend</b>',
        x=1.0,
        y=1.0,
        bgcolor='white',
        bordercolor='black',
        borderwidth=0,
        itemclick='toggle',
        itemdoubleclick='toggleothers'
    )
)

label_style_rwy = {
    "fontFamily": "Open Sans, Verdana, Arial, sans-serif",
    "fontSize": "16px",
    "color": "#444",
    "fontWeight": "bold"
}

label_style_distance = {
    "fontFamily": "Open Sans, Verdana, Arial, sans-serif",
    "fontSize": "16px",
    "color": "#444",
    "fontWeight": "bold",
    "marginRight": "10px"
}

app.layout = html.Div([
    html.Div([
        html.Label("Arrival Runway:", style=label_style_rwy),
        html.Label("Departure Runway:", style={**label_style_rwy, 'marginLeft': '60px'}),
        html.Div([
            dcc.Dropdown(
                id='arrival-runway-select',
                options=[{"label": rwy, "value": rwy} for rwy in runway_procedures.keys()],
                value=list(runway_procedures.keys())[0],
                style={
                    "fontFamily": "Open Sans, Verdana, Arial, sans-serif",
                    "fontSize": "14px",
                    "color": "#444",
                    "height": "34px",
                    "padding": "2px",
                    "width": "200px"
                }
            ),
            dcc.Dropdown(
                id='departure-runway-select',
                options=[{"label": rwy, "value": rwy} for rwy in runway_procedures.keys()],
                value=list(runway_procedures.keys())[4],
                style={
                    "fontFamily": "Open Sans, Verdana, Arial, sans-serif",
                    "fontSize": "14px",
                    "color": "#444",
                    "height": "34px",
                    "padding": "2px",
                    "width": "200px"
                }
            ),
            html.Label("Radius (NM):", style={**label_style_distance, 'marginLeft': '20px'}),
            dcc.Input(
                id='radius-nm',
                type='number',
                value=50,
                step=1,
                style={
                    "fontFamily": "Open Sans, Verdana, Arial, sans-serif",
                    "fontSize": "14px",
                    "color": "#444",
                    "height": "32px",
                    "padding": "5px",
                    "width": "105px",
                    "marginLeft": "5px"
                }
            ),
            dcc.Checklist(
                id='layer-toggle',
                options=[
                    {'label': 'Aerodromes', 'value': 'AERO'},
                    {'label': 'FIRs', 'value': 'FIR'},
                    {'label': 'Sectors', 'value': 'SECTOR'},
                    {'label': 'Waypoints', 'value': 'WAYPOINT'},
                ],
                value=['AERO', 'FIR'],
                labelStyle={
                    "fontFamily": "Open Sans, Verdana, Arial, sans-serif",
                    "fontSize": "14px",
                    "color": "#444",
                    "marginLeft": "10px",
                    "marginRight": "10px",
                    "display": "inline-block"
                },
                inputStyle={
                    "marginRight": "6px",
                    "accentColor": "dodgerblue"
                },
                style={
                    "marginLeft": "10px",
                    "display": "flex",
                    "alignItems": "center"
                }
               ),
        ], style={'display': 'flex', 'alignItems': 'center'})
    ], style={'padding': 2, 'width': '100%'}),

    html.Div([
        dcc.Graph(id='map', figure=fig)
    ], style={'width': '80%', 'display': 'inline-block'}),
])



#endregion

# Callbacks
@app.callback(
    Output('map', 'figure'),
    Input('arrival-runway-select', 'value'),
    Input('departure-runway-select', 'value'),
    Input('layer-toggle', 'value'),
    Input('radius-nm', 'value'),
)


def update_map(selected_runway_arrival, selected_runway_departure, selected_layers, radius_nm):

    # Toggle visibility based on selected layers and runways
    
    for i, trace in enumerate(fig.data):
        trace_name = trace.name.lower()
        is_sector = 'sector' in trace_name
        is_fir = 'fir' in trace_name
        
        trace_data = trace.customdata if trace.customdata else [None, None]
        trace_rwy = trace_data[0] if len(trace_data) > 0 else None
        trace_type = trace_data[1] if len(trace_data) > 1 else None
        
        show = (
            (trace_type == "STARs" and trace_rwy == selected_runway_arrival) or
            (trace_type == "SIDs" and trace_rwy== selected_runway_departure) or
            (trace_rwy == 'static' and 'AERO' in selected_layers) or
            (trace_rwy in selected_layers) or
            (trace_rwy == 'WAYPOINT' and 'WAYPOINT' in selected_layers) or
            (is_sector and 'SECTOR' in selected_layers) or
            (is_fir and 'FIR' in selected_layers) or
            (trace.name == 'Radius Circle') or
            '🗺️' in trace.name
        )
        fig.data[i].visible = show

    try:
        if radius_nm >= 0:
            radius_deg = radius_nm / 60
            theta = [2 * math.pi * i / 100 for i in range(101)]
            lat_circ = [WSSS_lat + radius_deg * math.sin(t) for t in theta]
            lon_circ = [WSSS_lon + radius_deg * math.cos(t) for t in theta]
            fig.data = [t for t in fig.data if t.name != 'Radius Circle']
            fig.add_trace(go.Scattermap(
                lat=lat_circ, lon=lon_circ,
                mode='lines', line=dict(color='mediumblue', width=2), hoverinfo='name', hovertemplate='%{fullData.name}<extra></extra>',
                name=f'{radius_nm} NM Radius Circle', showlegend=True, legendgroup='note'
            ))
    except TypeError:
        pass
    
    return fig

if __name__ == '__main__':
    app.run(debug=True)  # Set to True for development
    # app.run(debug=False)    # Set to False for production
