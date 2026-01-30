# Quick Start Guide

This guide will help you get the Modbus 485 Bridge up and running quickly.

## Prerequisites

1. **Moxa NPort Devices**: Two Moxa NPort serial-to-Ethernet converters configured and connected to your network
2. **Docker & Docker Compose**: Installed on your system
3. **Network Access**: Ensure the Docker host can reach both Moxa NPort devices

## Step-by-Step Setup

### 1. Configure Your Moxa NPort Devices

Before running the bridge, configure your Moxa NPort devices:

#### NPort 1 (Solar Inverter)
- Set to **TCP Server** mode or **Real COM** mode
- Configure serial settings to match your solar inverter:
  - Baud rate (e.g., 9600, 19200, 38400)
  - Parity (None, Even, Odd)
  - Data bits (7 or 8)
  - Stop bits (1 or 2)
- Note the IP address and TCP port (e.g., 192.168.1.100:4001)

#### NPort 2 (External System)
- Configure similarly to match your external system
- Note the IP address and TCP port (e.g., 192.168.1.101:4002)

### 2. Clone and Configure

```bash
# Clone the repository
git clone https://github.com/nejcmedved/double-485-bus.git
cd double-485-bus

# Create configuration file from example
cp config.env.example config.env

# Edit config.env with your actual NPort settings
nano config.env
```

### 3. Update config.env

Edit the `config.env` file with your NPort IP addresses and ports:

```bash
# Moxa NPort Configuration for Port 1 (Solar Inverter)
NPORT1_HOST=192.168.1.100    # Change to your NPort 1 IP
NPORT1_PORT=4001             # Change to your NPort 1 TCP port

# Moxa NPort Configuration for Port 2 (External System)
NPORT2_HOST=192.168.1.101    # Change to your NPort 2 IP
NPORT2_PORT=4002             # Change to your NPort 2 TCP port

# TCP Server Configuration (external clients connect here)
LISTEN_HOST=0.0.0.0
LISTEN_PORT=5020

# Timeout in seconds
MODBUS_TIMEOUT=3
```

### 4. Test Network Connectivity

Before starting the bridge, verify you can reach the NPort devices:

```bash
# Test NPort 1
ping 192.168.1.100
telnet 192.168.1.100 4001

# Test NPort 2
ping 192.168.1.101
telnet 192.168.1.101 4002
```

If telnet connects successfully, press Ctrl+] then type `quit` to exit.

### 5. Start the Bridge

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f
```

You should see output like:
```
modbus-bridge | INFO - Configuration loaded:
modbus-bridge | INFO -   NPort 1 (Solar Inverter): 192.168.1.100:4001
modbus-bridge | INFO -   NPort 2 (External System): 192.168.1.101:4002
modbus-bridge | INFO -   TCP Server: 0.0.0.0:5020
modbus-bridge | INFO - Starting Modbus Bridge...
modbus-bridge | INFO - Connecting to NPort 1 at 192.168.1.100:4001
modbus-bridge | INFO - Successfully connected to NPort 1
modbus-bridge | INFO - TCP server listening on ('0.0.0.0', 5020)
```

### 6. Test the Bridge

#### Test TCP Server Connection

From another machine or terminal:

```bash
telnet <docker-host-ip> 5020
```

You should be able to connect. The bridge will forward your data to the solar inverter.

#### Monitor Communication

Watch the logs to see data flowing:

```bash
docker-compose logs -f
```

Look for messages like:
```
DEBUG - Received X bytes from TCP client: <hex-data>
DEBUG - Forwarded X bytes to NPort 1
DEBUG - Received Y bytes from NPort 1: <hex-data>
DEBUG - Sent response back to TCP client
```

## Troubleshooting

### Bridge won't start

**Check logs:**
```bash
docker-compose logs
```

**Common issues:**
- NPort devices not reachable: Verify IP addresses and network connectivity
- Port already in use: Change `LISTEN_PORT` in config.env
- Invalid configuration: Check all values in config.env are correct

### No connection to NPort

**Error:** `Failed to connect to NPort 1`

**Solutions:**
1. Verify NPort IP address is correct
2. Check NPort is powered on and connected to network
3. Verify firewall isn't blocking the connection
4. Try connecting manually with telnet to verify port is open
5. Check NPort is in TCP Server mode or Real COM mode

### No data flowing

**Check:**
1. Modbus device (solar inverter) is powered on and connected
2. RS-485 wiring is correct (A to A, B to B)
3. RS-485 termination resistors are in place if needed
4. Baud rate, parity, and other serial settings match on NPort and device
5. Enable DEBUG logging in modbus_bridge.py to see all data

### Network mode issues

If the bridge can't reach NPort devices:

1. Edit `docker-compose.yml`
2. Change to host network mode:

```yaml
services:
  modbus-bridge:
    network_mode: host
    # Remove the ports: section when using host mode
    # Remove the networks: section when using host mode
```

## Next Steps

Once the bridge is running:

1. **Test with your external system**: Connect your Modbus client to port 5020
2. **Monitor performance**: Watch logs and verify data is flowing correctly
3. **Adjust timeouts**: If you see timeout errors, increase `MODBUS_TIMEOUT`
4. **Enable debug logging**: For detailed troubleshooting, set logging level to DEBUG in modbus_bridge.py

## Support

For issues or questions:
- Check the main [README.md](README.md) for detailed documentation
- Review the troubleshooting section
- Open an issue on GitHub

## Advanced: Running Without Docker

If you prefer to run directly with Python:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export NPORT1_HOST=192.168.1.100
export NPORT1_PORT=4001
export NPORT2_HOST=192.168.1.101
export NPORT2_PORT=4002

# Run the bridge
python3 modbus_bridge.py
```
