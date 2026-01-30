# Modbus 485 Bridge for Moxa NPort

This application provides a bidirectional bridge for Modbus communications over two RS-485 buses using Moxa NPort serial-to-Ethernet converters.

## Overview

The bridge connects:
- **Port 1 (NPort 1)**: Solar inverter (Modbus slave) via Moxa NPort
- **Port 2 (NPort 2)**: External system via Moxa NPort
- **TCP Server**: Listens for external TCP requests and bridges them to Port 1

### Key Features

- ✅ **Bidirectional bridging**: TCP → Port 1 and Port 2 → Port 1
- ✅ **Thread-safe locking**: Prevents simultaneous transmissions on the 485 bus
- ✅ **Auto-reconnection**: Automatically reconnects to NPort devices if connection is lost
- ✅ **Docker support**: Easy deployment with Docker and Docker Compose
- ✅ **Configurable**: Environment-based configuration

## Architecture

```
                                    ┌──────────────────┐
                                    │  Solar Inverter  │
                                    │  (Modbus Slave)  │
                                    └────────┬─────────┘
                                             │ RS-485
                                             │
                                    ┌────────┴─────────┐
                                    │   Moxa NPort 1   │
                                    │  (Serial-to-TCP) │
                                    └────────┬─────────┘
                                             │ TCP/IP
                                             │
    ┌────────────────┐              ┌────────┴─────────┐
    │ External TCP   │──────TCP────▶│  Modbus Bridge   │
    │   Clients      │              │  (This App)      │
    └────────────────┘              │   with Lock      │
                                    └────────┬─────────┘
                                             │ TCP/IP
                                    ┌────────┴─────────┐
                                    │   Moxa NPort 2   │
                                    │  (Serial-to-TCP) │
                                    └────────┬─────────┘
                                             │ RS-485
                                             │
                                    ┌────────┴─────────┐
                                    │ External System  │
                                    │  (Modbus M/S)    │
                                    └──────────────────┘
```

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.11+
- Moxa NPort devices configured and accessible on the network

## Configuration

Edit the `config.env` file to match your Moxa NPort settings:

```bash
# Moxa NPort Configuration for Port 1 (Solar Inverter)
NPORT1_HOST=192.168.1.100
NPORT1_PORT=4001

# Moxa NPort Configuration for Port 2 (External System)
NPORT2_HOST=192.168.1.101
NPORT2_PORT=4002

# TCP Server Configuration (to listen for external requests)
LISTEN_HOST=0.0.0.0
LISTEN_PORT=5020

# Modbus Configuration
MODBUS_TIMEOUT=3
```

### Configuration Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `NPORT1_HOST` | IP address of Moxa NPort for solar inverter | 192.168.1.100 |
| `NPORT1_PORT` | TCP port of Moxa NPort for solar inverter | 4001 |
| `NPORT2_HOST` | IP address of Moxa NPort for external system | 192.168.1.101 |
| `NPORT2_PORT` | TCP port of Moxa NPort for external system | 4002 |
| `LISTEN_HOST` | Host address for TCP server to listen on | 0.0.0.0 |
| `LISTEN_PORT` | TCP port for external clients to connect to | 5020 |
| `MODBUS_TIMEOUT` | Timeout in seconds for Modbus operations | 3 |

## Installation & Usage

### Important: Network Configuration

The Docker container needs network access to your Moxa NPort devices. By default, the docker-compose.yml uses a bridge network. Depending on your setup:

- **If NPort devices are on the same network as Docker host**: The default bridge network should work. Ensure the IP addresses in `config.env` are accessible from the Docker container.
- **If you need host network access**: Modify `docker-compose.yml` to use `network_mode: host` instead of the custom bridge network. This gives the container direct access to the host's network interfaces.
- **For production deployments**: Consider using Docker's macvlan or ipvlan network drivers for direct network access.

### Option 1: Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/nejcmedved/double-485-bus.git
cd double-485-bus
```

2. Copy the example config and edit with your Moxa NPort settings:
```bash
cp config.env.example config.env
# Edit config.env with your NPort IP addresses and ports
```

3. Build and run:
```bash
docker-compose up -d
```

4. View logs:
```bash
docker-compose logs -f
```

5. Stop the service:
```bash
docker-compose down
```

### Option 2: Docker

```bash
# Build the image
docker build -t modbus-bridge .

# Run the container
docker run -d \
  --name modbus-bridge \
  --env-file config.env \
  -p 5020:5020 \
  --restart unless-stopped \
  modbus-bridge
```

### Option 3: Python (Direct)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set environment variables or edit config.env:
```bash
export NPORT1_HOST=192.168.1.100
export NPORT1_PORT=4001
export NPORT2_HOST=192.168.1.101
export NPORT2_PORT=4002
```

3. Run the application:
```bash
python modbus_bridge.py
```

## How It Works

### Data Flow

1. **TCP Client → Solar Inverter (Port 1)**:
   - External TCP clients connect to the bridge's TCP server (port 5020)
   - Data from TCP clients is forwarded to NPort 1 (solar inverter)
   - Responses from the inverter are sent back to the TCP client
   - Bus lock ensures exclusive access during the transaction

2. **External System (Port 2) → Solar Inverter (Port 1)**:
   - Data from NPort 2 (external system) is monitored continuously
   - When data arrives, it's forwarded to NPort 1 (solar inverter)
   - Responses from the inverter are sent back to NPort 2
   - Bus lock ensures exclusive access during the transaction

### Locking Mechanism

The application uses an asyncio lock to ensure that only one communication can occur on the solar inverter's RS-485 bus at a time. This prevents:
- Data corruption from simultaneous transmissions
- Bus collisions
- Garbled responses

## Troubleshooting

### Connection Issues

**NPort not reachable:**
- Verify NPort IP addresses and ports in `config.env`
- Check network connectivity: `ping <NPORT_IP>`
- Verify Moxa NPort TCP server mode is enabled
- Check firewall settings

**Application won't start:**
- Check Docker logs: `docker-compose logs -f`
- Verify all required environment variables are set
- Ensure ports are not already in use

### Modbus Communication Issues

**No response from solar inverter:**
- Verify RS-485 wiring is correct
- Check Modbus settings (baud rate, parity, stop bits) on NPort
- Verify solar inverter Modbus address and registers
- Increase `MODBUS_TIMEOUT` value

**Timeout errors:**
- Increase `MODBUS_TIMEOUT` in `config.env`
- Check RS-485 termination resistors
- Verify device addresses don't conflict

## Moxa NPort Configuration Tips

1. Configure NPort in **TCP Server** or **Real COM** mode
2. Set appropriate serial settings (baud rate, parity, data bits, stop bits)
3. Disable any packet delimiter or timeout settings for raw data mode
4. Use static IP addresses for stable connections

## Development

### File Structure

```
.
├── modbus_bridge.py      # Main application
├── requirements.txt      # Python dependencies
├── config.env           # Configuration file
├── Dockerfile           # Docker image definition
├── docker-compose.yml   # Docker Compose configuration
└── README.md            # This file
```

### Testing

For development and testing, you can use Modbus simulation tools:
- **modpoll**: Command-line Modbus master simulator
- **diagslave**: Modbus slave simulator
- **Moxa NPort simulator**: For testing without physical devices

## License

This project is open source. See LICENSE file for details.

## Support

For issues and questions, please open an issue on GitHub.
