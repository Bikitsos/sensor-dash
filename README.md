# Sensor Dashboard

A real-time sensor monitoring dashboard built with NiceGUI and Supabase, designed to display data from IoT sensors stored in a PostgreSQL database.

## Features

- **Real-time Dashboard**: Monitor temperature, humidity, pressure, air quality, and boolean sensors
- **Supabase Integration**: Connects to your Supabase PostgreSQL database
- **Auto-refresh**: Updates data every 30 seconds automatically  
- **Responsive Design**: Clean, modern interface with status indicators
- **Demo Mode**: Works without database connection for testing
- **Device Statistics**: Shows active sensor count, daily data points, and alerts

## Sensor Types Supported

Based on your Supabase schema, the dashboard supports:

### Numeric Sensors
- **Temperature** (°C)
- **Humidity** (%)
- **Pressure** (hPa)
- **Battery** level
- **Voltage**
- **Link Quality**
- **Illuminance** (lux)
- **Brightness**

### Boolean Sensors
- Motion detection
- Door/window contact
- Water leak detection
- Occupancy
- Smoke detection
- Gas detection
- Vibration

## Setup Instructions

### Option 1: Local Development

#### 1. Prerequisites
- Python 3.12+
- A Supabase project with the sensor schema

#### 2. Install Dependencies
```bash
uv install
```

#### 3. Configure Supabase (Optional)
Create a `.env` file in the project root:
```bash
cp .env.example .env
```

Edit `.env` with your Supabase credentials:
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key-here
```

### 4. Database Schema
The dashboard expects the following Supabase tables:
- `sensor_readings` - Main sensor data table
- `devices` - Device metadata table  
- `latest_sensor_readings` - View for latest readings per device

Refer to the SQL schema provided for table structure.

### 5. Run the Dashboard
```bash
uv run main.py
```

The dashboard will be available at: http://localhost:8081

### Option 2: Using Podman (Containerized)

#### 1. Prerequisites
- Podman installed on your system
- `.env` file configured with your credentials

#### 2. Quick Start with Podman
```bash
# Build and start the dashboard
./run-podman.sh build
./run-podman.sh start

# Or use podman-compose (if you have podman-compose installed)
podman-compose up -d
```

#### 3. Podman Management Commands
```bash
# Build the container image
./run-podman.sh build

# Start the dashboard
./run-podman.sh start

# Stop the dashboard  
./run-podman.sh stop

# Restart the dashboard
./run-podman.sh restart

# View logs
./run-podman.sh logs
./run-podman.sh logs -f  # Follow logs

# Check status
./run-podman.sh status

# Open shell in container
./run-podman.sh shell

# Clean up (remove container and image)
./run-podman.sh clean
```

#### 4. Using Systemd (Optional - Auto-start)
```bash
# Copy service file to systemd
cp sensor-dashboard.service ~/.config/systemd/user/

# Enable and start the service
systemctl --user enable sensor-dashboard.service
systemctl --user start sensor-dashboard.service

# Check status
systemctl --user status sensor-dashboard.service
```

#### 5. Container Access
- **Dashboard URL**: http://localhost:8081
- **Default Login**: admin / sensor123
- **Logs**: `./run-podman.sh logs`

## Usage

### Demo Mode
If no Supabase credentials are provided, the dashboard runs in demo mode with sample data.

### Live Data
With Supabase configured, the dashboard will:
- Display real sensor readings from your database
- Update statistics based on actual device data
- Show connection status in the header
- Auto-refresh data every 30 seconds

### Manual Refresh
Use the "Refresh Data" button to manually update all sensor readings.

## Database Schema Requirements

Your `sensor_readings` table should include:
- Device identification fields (`device_name`, `device_ieee_address`)
- Sensor measurement fields (`temperature`, `humidity`, `pressure`, etc.)
- Boolean sensor fields (`motion`, `contact`, `water_leak`, etc.)
- Timestamp fields (`timestamp`, `created_at`, `updated_at`)

The `latest_sensor_readings` view provides the most recent reading for each device.

## Development

### Adding New Sensor Types
1. Update the `fetch_latest_sensor_data()` method
2. Add new sensor cards in `create_sensor_sections()`
3. Modify the UI layout as needed

### Customizing Alerts
Implement alert logic in the `fetch_device_stats()` method based on sensor thresholds.

## Project Structure
```
sensor-dash/
├── main.py              # Main application file
├── pyproject.toml       # Project dependencies
├── .env.example         # Environment template
├── README.md           # This file
└── .git/               # Git repository
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with both demo and live data modes
5. Submit a pull request

## License

This project is open source and available under the MIT License.
