from nicegui import ui
import os
from datetime import datetime, timedelta
import asyncio
from typing import List, Dict, Optional
import logging
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import pytz

# Load environment variables from .env file
load_dotenv()

# Authentication configuration
DASHBOARD_USER = os.getenv('DASHBOARD_USER', 'admin')
DASHBOARD_PASS = os.getenv('DASHBOARD_PASS', 'password')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Timezone configuration
CYPRUS_TZ = pytz.timezone('Europe/Nicosia')  # Handles daylight saving time properly
UTC_TZ = pytz.UTC

# Import Supabase (will be used when credentials are provided)
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase not available - running in demo mode")

class SensorDashboard:
    def __init__(self):
        self.supabase: Optional[Client] = None
        self.sensor_data: Dict = {}
        self.device_stats: Dict = {
            'active_sensors': 0,
            'data_points_today': 0
        }
        self.authenticated = False  # Track authentication state
        self.filter_range = '24h'  # Default filter range
        self.custom_start_date = None
        self.custom_end_date = None
        self.setup_supabase()
    
    def setup_supabase(self):
        """Initialize Supabase client if credentials are available"""
        try:
            supabase_url = os.getenv('SUPABASE_URL', '')
            supabase_key = os.getenv('SUPABASE_KEY', '')
            
            if supabase_url and supabase_key and SUPABASE_AVAILABLE:
                self.supabase = create_client(supabase_url, supabase_key)
                logger.info("Supabase client initialized successfully")
            else:
                logger.info("Supabase credentials not found - using demo data")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")
    
    async def fetch_device_stats(self):
        """Fetch device statistics from Supabase"""
        if not self.supabase:
            # Demo data when Supabase is not available
            self.device_stats = {
                'active_sensors': 12,
                'data_points_today': 2847
            }
            return
        
        try:
            # Get active devices count
            devices_response = self.supabase.table('devices').select('id').eq('is_active', True).execute()
            self.device_stats['active_sensors'] = len(devices_response.data)
            
            # Get data points from today (since data is stored with correct timezone)
            now_cyprus = datetime.now(CYPRUS_TZ)
            today_start_cyprus = now_cyprus.replace(hour=0, minute=0, second=0, microsecond=0)
            
            readings_response = self.supabase.table('sensor_readings').select('id').gte('timestamp', today_start_cyprus.isoformat()).execute()
            self.device_stats['data_points_today'] = len(readings_response.data)
            
        except Exception as e:
            logger.error(f"Error fetching device stats: {e}")
    
    async def fetch_latest_sensor_data(self):
        """Fetch latest sensor readings from Supabase"""
        if not self.supabase:
            # Demo data when Supabase is not available
            self.sensor_data = {
                'temperature_sensors': [
                    {'name': 'Living Room', 'value': '22.5', 'unit': '°C', 'timestamp': '2 min ago', 'is_stale': False},
                    {'name': 'Bedroom', 'value': '20.1', 'unit': '°C', 'timestamp': '3 min ago', 'is_stale': False},
                    {'name': 'Kitchen', 'value': '24.2', 'unit': '°C', 'timestamp': '1 min ago', 'is_stale': False},
                ],
                'humidity_sensors': [
                    {'name': 'Living Room', 'value': '45', 'unit': '%', 'timestamp': '2 min ago', 'is_stale': False},
                    {'name': 'Bedroom', 'value': '52', 'unit': '%', 'timestamp': '3 min ago', 'is_stale': False},
                    {'name': 'Bathroom', 'value': '68', 'unit': '%', 'timestamp': '4 min ago', 'is_stale': False},
                ]
            }
            return
        
        try:
            # Fetch latest readings using the view you created
            response = self.supabase.table('latest_sensor_readings').select('*').execute()
            
            # Organize data by sensor type
            temp_sensors = []
            humidity_sensors = []
            
            for reading in response.data:
                device_name = reading.get('device_name', 'Unknown')
                timestamp_str = self.format_timestamp(reading.get('timestamp'))
                raw_timestamp = reading.get('timestamp')
                
                # Check if data is stale (older than 4 hours)
                is_stale = self.is_data_stale(raw_timestamp, hours=4)
                
                # Temperature sensors
                if reading.get('temperature') is not None:
                    temp_sensors.append({
                        'name': device_name,
                        'value': f"{reading['temperature']:.1f}",
                        'unit': '°C',
                        'timestamp': timestamp_str,
                        'is_stale': is_stale
                    })
                
                # Humidity sensors
                if reading.get('humidity') is not None:
                    humidity_sensors.append({
                        'name': device_name,
                        'value': f"{reading['humidity']:.1f}",
                        'unit': '%',
                        'timestamp': timestamp_str,
                        'is_stale': is_stale
                    })
            
            self.sensor_data = {
                'temperature_sensors': temp_sensors,
                'humidity_sensors': humidity_sensors
            }
            
        except Exception as e:
            logger.error(f"Error fetching sensor data: {e}")
    
    async def fetch_historical_data(self, time_range='24h', start_date=None, end_date=None):
        """Fetch historical sensor data with flexible time filtering"""
        if not self.supabase:
            # Demo historical data with Cyprus timezone
            now_cyprus = datetime.now(CYPRUS_TZ)
            
            # Determine hours based on time_range
            if time_range == '12h':
                hours = 12
            elif time_range == '24h':
                hours = 24
            elif time_range == '7d':
                hours = 24 * 7
            elif time_range == '30d':
                hours = 24 * 30
            else:
                hours = 24
                
            timestamps = [now_cyprus - timedelta(hours=i) for i in range(hours, 0, -1)]
            
            return {
                'temperature_history': [
                    {'device_name': 'Living Room', 'timestamp': ts, 'temperature': 22 + (i % 4)}
                    for i, ts in enumerate(timestamps)
                ],
                'humidity_history': [
                    {'device_name': 'Living Room', 'timestamp': ts, 'humidity': 45 + (i % 10)}
                    for i, ts in enumerate(timestamps)
                ]
            }
        
        try:
            # Calculate time range based on filter
            now_cyprus = datetime.now(CYPRUS_TZ)
            
            if time_range == '12h':
                since_cyprus = now_cyprus - timedelta(hours=12)
                until_cyprus = now_cyprus
            elif time_range == '24h':
                since_cyprus = now_cyprus - timedelta(hours=24)
                until_cyprus = now_cyprus
            elif time_range == '7d':
                since_cyprus = now_cyprus - timedelta(days=7)
                until_cyprus = now_cyprus
            elif time_range == '30d':
                since_cyprus = now_cyprus - timedelta(days=30)
                until_cyprus = now_cyprus
            elif time_range == 'custom' and start_date and end_date:
                # Parse custom dates and set timezone
                since_cyprus = CYPRUS_TZ.localize(datetime.fromisoformat(start_date))
                until_cyprus = CYPRUS_TZ.localize(datetime.fromisoformat(end_date))
            else:
                # Default to 24 hours
                since_cyprus = now_cyprus - timedelta(hours=24)
                until_cyprus = now_cyprus
            
            # Fetch data from Supabase
            response = self.supabase.table('sensor_readings').select(
                'device_name, timestamp, temperature, humidity'
            ).gte('timestamp', since_cyprus.isoformat()).lte('timestamp', until_cyprus.isoformat()).order('timestamp').execute()
            
            # Group data by sensor type - keep timestamps as-is from database
            temp_data = []
            humidity_data = []
            
            for r in response.data:
                if r.get('temperature') is not None:
                    # Parse timestamp as-is from database (already correct)
                    timestamp_str = r['timestamp']
                    if timestamp_str.endswith('+00'):
                        timestamp_str = timestamp_str.replace('+00', '+00:00')
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    temp_data.append({
                        'device_name': r['device_name'],
                        'timestamp': timestamp,
                        'temperature': float(r['temperature'])
                    })
                
                if r.get('humidity') is not None:
                    # Parse timestamp as-is from database (already correct)
                    timestamp_str = r['timestamp']
                    if timestamp_str.endswith('+00'):
                        timestamp_str = timestamp_str.replace('+00', '+00:00')
                    timestamp = datetime.fromisoformat(timestamp_str)
                    
                    humidity_data.append({
                        'device_name': r['device_name'],
                        'timestamp': timestamp,
                        'humidity': float(r['humidity'])
                    })
            
            return {
                'temperature_history': temp_data,
                'humidity_history': humidity_data
            }
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {e}")
            return {}
    
    def create_temperature_graph(self, data, time_range='24h'):
        """Create temperature trend graph with specified time range"""
        if not data:
            return go.Figure().add_annotation(text="No temperature data available", 
                                            showarrow=False, x=0.5, y=0.5)
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        fig = go.Figure()
        
        # Group by device and create a line for each
        for device in df['device_name'].unique():
            device_data = df[df['device_name'] == device]
            fig.add_trace(go.Scatter(
                x=device_data['timestamp'],
                y=device_data['temperature'],
                mode='lines+markers',
                name=device,
                line=dict(width=2)
            ))
        
        # Create title based on time range
        range_titles = {
            '12h': 'Last 12 Hours',
            '24h': 'Last 24 Hours',
            '7d': 'Last 7 Days',
            '30d': 'Last 30 Days',
            'custom': 'Custom Range'
        }
        
        title = f"Temperature Trends - {range_titles.get(time_range, 'Last 24 Hours')}"
        
        fig.update_layout(
            title=title,
            xaxis_title='Time',
            yaxis_title='Temperature (°C)',
            hovermode='x unified',
            showlegend=True,
            height=500,  # Increased height
            width=None,  # Let it use full width
            margin=dict(l=50, r=50, t=50, b=50),
            # Remove scroll bars and controls
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True)
        )
        
        return fig
    
    def create_humidity_graph(self, data, time_range='24h'):
        """Create humidity trend graph with specified time range"""
        if not data:
            return go.Figure().add_annotation(text="No humidity data available", 
                                            showarrow=False, x=0.5, y=0.5)
        
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        fig = go.Figure()
        
        for device in df['device_name'].unique():
            device_data = df[df['device_name'] == device]
            fig.add_trace(go.Scatter(
                x=device_data['timestamp'],
                y=device_data['humidity'],
                mode='lines+markers',
                name=device,
                line=dict(width=2),
                fill='tonexty' if len(fig.data) > 0 else None
            ))
        
        # Create title based on time range
        range_titles = {
            '12h': 'Last 12 Hours',
            '24h': 'Last 24 Hours',
            '7d': 'Last 7 Days',
            '30d': 'Last 30 Days',
            'custom': 'Custom Range'
        }
        
        title = f"Humidity Trends - {range_titles.get(time_range, 'Last 24 Hours')}"
        
        fig.update_layout(
            title=title,
            xaxis_title='Time',
            yaxis_title='Humidity (%)',
            hovermode='x unified',
            showlegend=True,
            height=500,  # Increased height
            width=None,  # Let it use full width
            margin=dict(l=50, r=50, t=50, b=50),
            # Remove scroll bars and controls
            xaxis=dict(fixedrange=True),
            yaxis=dict(fixedrange=True)
        )
        
        return fig
    
    def create_sensor_summary_chart(self):
        """Create a summary chart of current sensor values"""
        temp_sensors = self.sensor_data.get('temperature_sensors', [])
        humidity_sensors = self.sensor_data.get('humidity_sensors', [])
        
        if not temp_sensors and not humidity_sensors:
            return go.Figure().add_annotation(text="No sensor data available", 
                                            showarrow=False, x=0.5, y=0.5)
        
        # Create a bar chart of current sensor values
        devices = []
        temperatures = []
        humidities = []
        
        # Match temperature and humidity by device name
        device_data = {}
        
        for sensor in temp_sensors:
            device_data[sensor['name']] = {'temp': float(sensor['value'])}
        
        for sensor in humidity_sensors:
            if sensor['name'] in device_data:
                device_data[sensor['name']]['humidity'] = float(sensor['value'])
            else:
                device_data[sensor['name']] = {'humidity': float(sensor['value'])}
        
        for device, values in device_data.items():
            devices.append(device)
            temperatures.append(values.get('temp', 0))
            humidities.append(values.get('humidity', 0))
        
        fig = go.Figure()
        
        if temperatures:
            fig.add_trace(go.Bar(
                name='Temperature (°C)',
                x=devices,
                y=temperatures,
                yaxis='y',
                marker_color='lightcoral'
            ))
        
        if humidities:
            fig.add_trace(go.Bar(
                name='Humidity (%)',
                x=devices,
                y=humidities,
                yaxis='y2',
                marker_color='lightblue'
            ))
        
        fig.update_layout(
            title='Current Sensor Values by Device',
            xaxis=dict(title='Devices', fixedrange=True),
            yaxis=dict(title='Temperature (°C)', side='left', fixedrange=True),
            yaxis2=dict(title='Humidity (%)', side='right', overlaying='y', fixedrange=True),
            barmode='group',
            height=400
        )
        
        return fig
    
    def format_timestamp(self, timestamp_str):
        """Format timestamp to relative time - DB timestamps are Cyprus time with wrong +00 suffix"""
        if not timestamp_str:
            return "Unknown"
        
        try:
            # The database timestamps are actually Cyprus local time but have +00:00 suffix
            # We need to strip the timezone info and treat as Cyprus local time
            if timestamp_str.endswith('+00:00'):
                # Remove the incorrect +00:00 suffix
                timestamp_str = timestamp_str.replace('+00:00', '')
            elif timestamp_str.endswith('+00'):
                # Remove the incorrect +00 suffix  
                timestamp_str = timestamp_str.replace('+00', '')
            
            # Parse as naive datetime (no timezone info)
            timestamp_naive = datetime.fromisoformat(timestamp_str)
            
            # Treat as Cyprus local time
            timestamp_cyprus = CYPRUS_TZ.localize(timestamp_naive)
            
            # Get current time in Cyprus
            now_cyprus = datetime.now(CYPRUS_TZ)
            
            # Calculate the time difference
            diff = now_cyprus - timestamp_cyprus
            total_seconds = diff.total_seconds()
            
            # Handle future timestamps (shouldn't happen normally)
            if total_seconds < 0:
                total_seconds = abs(total_seconds)
                if total_seconds < 60:
                    return "Just now"
                elif total_seconds < 3600:
                    minutes = int(total_seconds // 60)
                    return f"{minutes} min from now"
                else:
                    hours = int(total_seconds // 3600)
                    return f"{hours} hr from now"
            
            # Normal past timestamps
            if total_seconds < 60:  # Less than 1 minute
                return "Just now"
            elif total_seconds < 3600:  # Less than 1 hour
                minutes = int(total_seconds // 60)
                return f"{minutes} min ago"
            elif total_seconds < 86400:  # Less than 1 day
                hours = int(total_seconds // 3600)
                return f"{hours} hr ago"
            else:  # More than 1 day
                days = int(total_seconds // 86400)
                return f"{days} days ago"
                
        except Exception as e:
            logger.error(f"Error parsing timestamp {timestamp_str}: {e}")
            return f"Unknown"

    def is_data_stale(self, timestamp_str: str, hours: int = 4) -> bool:
        """Check if sensor data is older than specified hours"""
        try:
            if not timestamp_str:
                return True
                
            # Parse the timestamp from database
            if timestamp_str.endswith('+00'):
                timestamp_str = timestamp_str.replace('+00', '+00:00')
            
            timestamp = datetime.fromisoformat(timestamp_str)
            now_cyprus = datetime.now(CYPRUS_TZ)
            
            # Convert timestamp to Cyprus timezone if it's UTC
            if timestamp.tzinfo is None or timestamp.tzinfo.utcoffset(timestamp) == timedelta(0):
                timestamp_utc = timestamp.replace(tzinfo=UTC_TZ)
                timestamp_cyprus = timestamp_utc.astimezone(CYPRUS_TZ)
            else:
                timestamp_cyprus = timestamp.astimezone(CYPRUS_TZ)
            
            # Calculate time difference
            time_diff = now_cyprus - timestamp_cyprus
            hours_diff = time_diff.total_seconds() / 3600
            
            return hours_diff > hours
            
        except Exception as e:
            logger.error(f"Error checking if data is stale for timestamp {timestamp_str}: {e}")
            return True  # Assume stale if we can't parse the timestamp

    async def export_to_csv(self, data_type='all'):
        """Export current filtered data to CSV"""
        try:
            # Get current historical data
            historical_data = await self.fetch_historical_data(self.filter_range)
            
            if not historical_data:
                return None
            
            # Create filename with timestamp
            timestamp = datetime.now(CYPRUS_TZ).strftime('%Y%m%d_%H%M%S')
            
            if data_type == 'temperature' and historical_data.get('temperature_history'):
                df = pd.DataFrame(historical_data['temperature_history'])
                filename = f'temperature_data_{timestamp}.csv'
            elif data_type == 'humidity' and historical_data.get('humidity_history'):
                df = pd.DataFrame(historical_data['humidity_history'])
                filename = f'humidity_data_{timestamp}.csv'
            elif data_type == 'all':
                # Combine both temperature and humidity data
                temp_df = pd.DataFrame(historical_data.get('temperature_history', []))
                humidity_df = pd.DataFrame(historical_data.get('humidity_history', []))
                
                # Merge on timestamp and device_name
                if not temp_df.empty and not humidity_df.empty:
                    df = pd.merge(temp_df, humidity_df, on=['timestamp', 'device_name'], how='outer')
                elif not temp_df.empty:
                    df = temp_df
                elif not humidity_df.empty:
                    df = humidity_df
                else:
                    return None
                
                filename = f'sensor_data_{timestamp}.csv'
            else:
                return None
            
            if df.empty:
                return None
            
            # Sort by timestamp
            df = df.sort_values('timestamp')
            
            # Format timestamp for better readability
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            # Create CSV content
            csv_content = df.to_csv(index=False)
            
            return {
                'filename': filename,
                'content': csv_content,
                'mime_type': 'text/csv'
            }
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return None

    def authenticate(self, username: str, password: str) -> bool:
        """Check if the provided credentials are valid"""
        return username == DASHBOARD_USER and password == DASHBOARD_PASS
    
    def logout(self):
        """Log out the user"""
        self.authenticated = False

# Initialize dashboard instance
dashboard = SensorDashboard()

# Global variables for graphs
historical_data = {}
graph_container = None

def create_header():
    """Create the main header section"""
    with ui.row().classes('w-full justify-between items-center p-4 bg-blue-600 text-white'):
        # Left side - Title
        with ui.column().classes('items-start'):
            ui.label('Sensor Dashboard').classes('text-2xl font-bold')
            ui.label('Real-time Monitoring System').classes('text-lg')
        
        # Center - Current Date/Time
        with ui.column().classes('items-center'):
            current_datetime_label = ui.label().classes('text-xl font-mono bg-blue-800 px-4 py-2 rounded')
            ui.label('Cyprus Time').classes('text-sm text-blue-200')
            
            def update_datetime():
                cyprus_now = datetime.now(CYPRUS_TZ)
                current_datetime_label.text = cyprus_now.strftime('%Y-%m-%d %H:%M:%S')
            
            # Update immediately and then every second
            update_datetime()
            ui.timer(1.0, update_datetime)
        
        # Right side - Connection status
        status_color = 'green' if dashboard.supabase else 'orange'
        status_text = 'Connected' if dashboard.supabase else 'Demo Mode'
        with ui.row().classes('items-center gap-2'):
            ui.icon('circle', size='sm').classes(f'text-{status_color}-400')
            ui.label(status_text).classes('text-sm')

def create_sensor_card(sensor_data, title_color='blue'):
    """Create a sensor card with real data"""
    # Determine if data is stale and set appropriate styling
    is_stale = sensor_data.get('is_stale', False)
    
    if is_stale:
        # Red card for stale data
        card_classes = 'flex-1 p-4 border border-red-500 bg-red-50'
        name_classes = 'font-semibold text-red-800'
        value_classes = 'text-2xl font-bold text-red-700'
        unit_classes = 'text-red-500'
        timestamp_classes = 'text-xs text-red-600 mt-1 font-semibold'
    else:
        # Normal card styling
        card_classes = 'flex-1 p-4 border'
        name_classes = 'font-semibold'
        value_classes = 'text-2xl font-bold text-gray-800'
        unit_classes = 'text-gray-500'
        timestamp_classes = 'text-xs text-gray-400 mt-1'
    
    with ui.card().classes(card_classes):
        ui.label(sensor_data['name']).classes(name_classes)
        with ui.row().classes('items-baseline gap-2'):
            ui.label(sensor_data['value']).classes(value_classes)
            ui.label(sensor_data['unit']).classes(unit_classes)
        
        # Add warning text for stale data
        if is_stale:
            ui.label(f"⚠️ Updated: {sensor_data['timestamp']} (Data may be stale)").classes(timestamp_classes)
        else:
            ui.label(f"Updated: {sensor_data['timestamp']}").classes(timestamp_classes)

def create_graphs_section():
    """Create the graphs section with historical data and filtering"""
    ui.label('Sensor Trends & Analytics').classes('text-2xl font-bold text-center mb-6 mt-8')
    
    # Filter controls
    with ui.card().classes('w-full mb-4 p-4'):
        ui.label('Time Range Filter').classes('text-lg font-semibold mb-2')
        
        with ui.row().classes('w-full gap-4 items-center flex-wrap'):
            # Quick filter buttons
            filter_buttons = ui.row().classes('gap-2 flex-wrap')
            with filter_buttons:
                ui.button('12 Hours', on_click=lambda: apply_filter('12h')).classes('bg-blue-500 hover:bg-blue-700 text-white')
                ui.button('24 Hours', on_click=lambda: apply_filter('24h')).classes('bg-blue-500 hover:bg-blue-700 text-white')
                ui.button('7 Days', on_click=lambda: apply_filter('7d')).classes('bg-blue-500 hover:bg-blue-700 text-white')
                ui.button('30 Days', on_click=lambda: apply_filter('30d')).classes('bg-blue-500 hover:bg-blue-700 text-white')
            
            # Custom date range (for future implementation)
            with ui.row().classes('gap-2 items-center ml-8'):
                ui.label('Custom Range:').classes('font-medium')
                start_date = ui.date().classes('w-32 text-sm')
                ui.label('to').classes('text-sm mx-1')
                end_date = ui.date().classes('w-32 text-sm')
                ui.button('Apply', on_click=lambda: apply_custom_filter(start_date.value, end_date.value)).classes('bg-green-500 hover:bg-green-700 text-white px-3 py-1 text-sm')
        
        # Current filter status
        filter_status = ui.label(f'Showing: Last 24 Hours').classes('text-sm text-gray-600 mt-2')
    
    # Graph navigation tabs
    with ui.tabs().classes('w-full') as tabs:
        temp_tab = ui.tab('Temperature')
        humidity_tab = ui.tab('Humidity')
        summary_tab = ui.tab('Summary')
    
    with ui.tab_panels(tabs, value=temp_tab).classes('w-full'):
        # Temperature graph panel
        with ui.tab_panel(temp_tab):
            temp_graph_container = ui.column().classes('w-full')
            with temp_graph_container:
                if historical_data.get('temperature_history'):
                    temp_fig = dashboard.create_temperature_graph(historical_data['temperature_history'], dashboard.filter_range)
                    ui.plotly(temp_fig).classes('w-full')  # Clean display without controls
                    
                    # Export button for temperature data
                    with ui.row().classes('justify-center mt-2'):
                        ui.button('Export Temperature Data to CSV', 
                                 on_click=lambda: export_data('temperature'),
                                 icon='download').classes('bg-blue-500 hover:bg-blue-700 text-white px-4 py-2')
                else:
                    ui.label('Loading temperature data...').classes('text-center text-gray-500 p-8')
        
        # Humidity graph panel
        with ui.tab_panel(humidity_tab):
            humidity_graph_container = ui.column().classes('w-full')
            with humidity_graph_container:
                if historical_data.get('humidity_history'):
                    humidity_fig = dashboard.create_humidity_graph(historical_data['humidity_history'], dashboard.filter_range)
                    ui.plotly(humidity_fig).classes('w-full')  # Clean display without controls
                    
                    # Export button for humidity data
                    with ui.row().classes('justify-center mt-2'):
                        ui.button('Export Humidity Data to CSV', 
                                 on_click=lambda: export_data('humidity'),
                                 icon='download').classes('bg-green-500 hover:bg-green-700 text-white px-4 py-2')
                else:
                    ui.label('Loading humidity data...').classes('text-center text-gray-500 p-8')
        
        # Summary chart panel
        with ui.tab_panel(summary_tab):
            summary_graph_container = ui.column().classes('w-full')
            with summary_graph_container:
                summary_fig = dashboard.create_sensor_summary_chart()
                ui.plotly(summary_fig).classes('w-full')  # Clean display without controls
                
                # Export button for all data
                with ui.row().classes('justify-center mt-2'):
                    ui.button('Export All Data to CSV', 
                             on_click=lambda: export_data('all'),
                             icon='download').classes('bg-purple-500 hover:bg-purple-700 text-white px-4 py-2')
    
    # Export function
    async def export_data(data_type):
        """Handle CSV export for different data types"""
        try:
            result = await dashboard.export_to_csv(data_type)
            if result:
                # Create a proper file download using bytes
                from io import BytesIO
                buffer = BytesIO(result['content'].encode('utf-8'))
                ui.download(buffer.getvalue(), result['filename'])
                ui.notify(f'Exported {data_type} data successfully!', color='positive')
            else:
                ui.notify('No data available to export', color='warning')
        except Exception as e:
            logger.error(f"Error during export: {e}")
            ui.notify('Export failed. Please try again.', color='negative')
    
    # Filter application functions
    async def apply_filter(time_range):
        dashboard.filter_range = time_range
        filter_status.text = f'Showing: {get_filter_display_name(time_range)}'
        await refresh_graphs()
    
    async def apply_custom_filter(start, end):
        if start and end:
            dashboard.filter_range = 'custom'
            dashboard.custom_start_date = start
            dashboard.custom_end_date = end
            filter_status.text = f'Showing: {start} to {end}'
            await refresh_graphs()
        else:
            ui.notify('Please select both start and end dates', type='warning')
    
    def get_filter_display_name(time_range):
        names = {
            '12h': 'Last 12 Hours',
            '24h': 'Last 24 Hours',
            '7d': 'Last 7 Days',
            '30d': 'Last 30 Days',
            'custom': 'Custom Range'
        }
        return names.get(time_range, 'Last 24 Hours')
    
    async def refresh_graphs():
        global historical_data
        # Fetch new data based on filter
        if dashboard.filter_range == 'custom':
            historical_data = await dashboard.fetch_historical_data(
                dashboard.filter_range, 
                dashboard.custom_start_date, 
                dashboard.custom_end_date
            )
        else:
            historical_data = await dashboard.fetch_historical_data(dashboard.filter_range)
        
        # Refresh the sensor sections which includes graphs
        if sensor_container:
            sensor_container.clear()
            with sensor_container:
                create_sensor_sections()

def create_sensor_sections():
    """Create sections for different sensor types with real data"""
    
    # Temperature Sensors Section
    with ui.card().classes('w-full m-4 p-4'):
        ui.label('Temperature Sensors').classes('text-xl font-bold text-blue-700 mb-4')
        temp_sensors = dashboard.sensor_data.get('temperature_sensors', [])
        if temp_sensors:
            with ui.row().classes('w-full gap-4 flex-wrap'):
                for sensor in temp_sensors[:4]:  # Show max 4 sensors per row
                    create_sensor_card(sensor, 'blue')
        else:
            ui.label('No temperature sensors found').classes('text-gray-500 italic')
    
    # Humidity Sensors Section
    with ui.card().classes('w-full m-4 p-4'):
        ui.label('Humidity Sensors').classes('text-xl font-bold text-green-700 mb-4')
        humidity_sensors = dashboard.sensor_data.get('humidity_sensors', [])
        if humidity_sensors:
            with ui.row().classes('w-full gap-4 flex-wrap'):
                for sensor in humidity_sensors[:4]:
                    create_sensor_card(sensor, 'green')
        else:
            ui.label('No humidity sensors found').classes('text-gray-500 italic')

    # Add graphs section
    create_graphs_section()

def create_footer():
    """Create footer with status information"""
    with ui.row().classes('w-full justify-between items-center p-4 bg-gray-100 mt-8'):
        cyprus_time = datetime.now(CYPRUS_TZ).strftime("%H:%M:%S")
        ui.label(f'Last Updated: {cyprus_time} (Cyprus Time)').classes('text-gray-600')
        db_status = 'Connected to Supabase' if dashboard.supabase else 'Demo Mode - No Database'
        status_color = 'green' if dashboard.supabase else 'orange'
        ui.label(f'Database Status: {db_status}').classes(f'text-{status_color}-600 font-semibold')

# Set page title
ui.page_title('Sensor Dashboard')

# Global variables for UI elements and graphs
active_sensors_label = None
data_points_label = None
sensor_container = None
main_container = None

def create_login_ui():
    """Create the login interface"""
    with ui.column().classes('w-full min-h-screen justify-center items-center bg-gray-100'):
        with ui.card().classes('w-96 p-8'):
            ui.label('Sensor Dashboard Login').classes('text-2xl font-bold mb-6 text-center')
            
            username_input = ui.input('Username').classes('w-full mb-4')
            password_input = ui.input('Password', password=True).classes('w-full mb-6')
            
            login_button = ui.button('Login', on_click=lambda: handle_login(username_input.value, password_input.value)).classes('w-full bg-blue-600 hover:bg-blue-700 text-white')
            
            error_label = ui.label('').classes('text-red-500 text-center mt-4')
            
            def handle_login(username: str, password: str):
                if dashboard.authenticate(username, password):
                    dashboard.authenticated = True
                    ui.navigate.to('/')  # Redirect to main page
                else:
                    error_label.text = 'Invalid username or password'
                    username_input.value = ''
                    password_input.value = ''

def create_main_dashboard():
    """Create the main dashboard UI"""
    global active_sensors_label, data_points_label, sensor_container, main_container
    
    with ui.column().classes('w-full min-h-screen') as main_container:
        create_header()
        
        # Main content area
        with ui.column().classes('flex-1 p-4'):
            with ui.row().classes('w-full justify-between items-center mb-8'):
                ui.label('Sensor Monitoring Dashboard').classes('text-3xl font-bold')
                
                # Add logout button
                with ui.row().classes('gap-2'):
                    ui.button('Logout', on_click=handle_logout).classes('bg-red-500 hover:bg-red-700 text-white')
                    refresh_button = ui.button('Refresh Data', on_click=lambda: None).classes('bg-blue-500 hover:bg-blue-700 text-white')
            
            # Status overview - will be updated with real data
            with ui.row().classes('w-full justify-center gap-8 mb-8'):
                with ui.card().classes('p-4 text-center'):
                    ui.label('Active Sensors').classes('font-semibold text-gray-600')
                    active_sensors_label = ui.label('0').classes('text-3xl font-bold text-green-600')
                
                with ui.card().classes('p-4 text-center'):
                    ui.label('Data Points Today').classes('font-semibold text-gray-600')
                    data_points_label = ui.label('0').classes('text-3xl font-bold text-blue-600')
            
            # Container for sensor sections - will be refreshed
            sensor_container = ui.column().classes('w-full')
            
            with sensor_container:
                create_sensor_sections()

def handle_logout():
    """Handle user logout"""
    dashboard.logout()
    ui.navigate.to('/')

# Main app logic - show login or dashboard based on authentication

async def refresh_data():
    """Refresh all dashboard data with current filter settings"""
    global historical_data
    await dashboard.fetch_device_stats()
    await dashboard.fetch_latest_sensor_data()
    
    # Use current filter settings
    if dashboard.filter_range == 'custom':
        historical_data = await dashboard.fetch_historical_data(
            dashboard.filter_range, 
            dashboard.custom_start_date, 
            dashboard.custom_end_date
        )
    else:
        historical_data = await dashboard.fetch_historical_data(dashboard.filter_range)
    
    ui.notify('Data and graphs refreshed!', type='positive')

async def setup_dashboard():
    """Initial data loading"""
    global historical_data
    await dashboard.fetch_device_stats()
    await dashboard.fetch_latest_sensor_data()
    historical_data = await dashboard.fetch_historical_data(dashboard.filter_range)

# Main app logic - show login or dashboard based on authentication

# Main app logic - show login or dashboard based on authentication

@ui.page('/')
def main_page():
    if dashboard.authenticated:
        show_dashboard()
    else:
        show_login()

def show_login():
    """Show the login interface"""
    ui.page_title('Login - Sensor Dashboard')
    
    with ui.column().classes('w-full min-h-screen justify-center items-center bg-gray-100'):
        with ui.card().classes('w-96 p-8'):
            ui.label('Sensor Dashboard Login').classes('text-2xl font-bold mb-6 text-center')
            
            username_input = ui.input('Username').classes('w-full mb-4')
            password_input = ui.input('Password', password=True).classes('w-full mb-6')
            
            error_label = ui.label('').classes('text-red-500 text-center mt-4')
            
            async def handle_login():
                if dashboard.authenticate(username_input.value, password_input.value):
                    dashboard.authenticated = True
                    ui.navigate.to('/')
                else:
                    error_label.text = 'Invalid username or password'
                    username_input.value = ''
                    password_input.value = ''
            
            login_button = ui.button('Login', on_click=handle_login).classes('w-full bg-blue-600 hover:bg-blue-700 text-white')

def show_dashboard():
    """Show the main dashboard"""
    global active_sensors_label, data_points_label, sensor_container, refresh_button
    
    ui.page_title('Sensor Dashboard')
    
    with ui.column().classes('w-full min-h-screen'):
        create_header()
        
        # Main content area
        with ui.column().classes('flex-1 p-4'):
            with ui.row().classes('w-full justify-between items-center mb-8'):
                ui.label('Sensor Monitoring Dashboard').classes('text-3xl font-bold')
                
                # Add logout button
                with ui.row().classes('gap-2'):
                    async def handle_logout():
                        dashboard.logout()
                        ui.navigate.to('/')
                    
                    ui.button('Logout', on_click=handle_logout).classes('bg-red-500 hover:bg-red-700 text-white')
                    refresh_button = ui.button('Refresh Data', on_click=lambda: None).classes('bg-blue-500 hover:bg-blue-700 text-white')
            
            # Status overview - will be updated with real data
            with ui.row().classes('w-full justify-center gap-8 mb-8'):
                with ui.card().classes('p-4 text-center'):
                    ui.label('Active Sensors').classes('font-semibold text-gray-600')
                    active_sensors_label = ui.label('0').classes('text-3xl font-bold text-green-600')
                
                with ui.card().classes('p-4 text-center'):
                    ui.label('Data Points Today').classes('font-semibold text-gray-600')
                    data_points_label = ui.label('0').classes('text-3xl font-bold text-blue-600')
            
            # Container for sensor sections - will be refreshed
            sensor_container = ui.column().classes('w-full')
            
            with sensor_container:
                create_sensor_sections()
        
        create_footer()
    
    # Update the refresh button
    refresh_button.on_click = refresh_dashboard
    
    # Initial data load when the page loads
    async def initialize():
        await setup_dashboard()
        update_stats_display()
        # Refresh sensor sections
        if sensor_container:
            sensor_container.clear()
            with sensor_container:
                create_sensor_sections()
    
    # Schedule initial load
    ui.timer(0.1, initialize, once=True)
    
    # Auto-refresh every 30 seconds
    ui.timer(30, refresh_dashboard)

# Function to update the stats display
def update_stats_display():
    if active_sensors_label:
        active_sensors_label.text = str(dashboard.device_stats['active_sensors'])
    if data_points_label:
        data_points_label.text = f"{dashboard.device_stats['data_points_today']:,}"

# Enhanced refresh function that updates UI
async def refresh_dashboard():
    await refresh_data()
    update_stats_display()
    
    # Clear and recreate sensor sections (includes graphs)
    if sensor_container:
        sensor_container.clear()
        with sensor_container:
            create_sensor_sections()

# Run the app
if __name__ in {"__main__", "__mp_main__"}:
    ui.run(port=8081, show=True, title='Sensor Dashboard')



