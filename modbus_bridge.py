#!/usr/bin/env python3
"""
Modbus Bridge for Double 485 Bus
Bridges Modbus communications between two RS-485 buses via Moxa NPort devices.

Port 1: Solar inverter (Modbus slave) - Connected via Moxa NPort
Port 2: External system (Modbus master/slave) - Connected via Moxa NPort
TCP Server: Listens for external TCP requests and bridges to Port 1
"""

import asyncio
import logging
import os
import sys
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ModbusBridge:
    """
    Modbus Bridge that handles bidirectional communication between two RS-485 buses
    through Moxa NPort devices with proper locking to prevent simultaneous transmissions.
    """
    
    def __init__(self, 
                 nport1_host: str, nport1_port: int,
                 nport2_host: str, nport2_port: int,
                 listen_host: str = '0.0.0.0', listen_port: int = 5020,
                 timeout: int = 3):
        """
        Initialize the Modbus Bridge.
        
        Args:
            nport1_host: IP address of Moxa NPort for Port 1 (solar inverter)
            nport1_port: TCP port of Moxa NPort for Port 1
            nport2_host: IP address of Moxa NPort for Port 2 (external system)
            nport2_port: TCP port of Moxa NPort for Port 2
            listen_host: Host to listen on for TCP server
            listen_port: Port to listen on for TCP server
            timeout: Socket timeout in seconds
        """
        self.nport1_host = nport1_host
        self.nport1_port = nport1_port
        self.nport2_host = nport2_host
        self.nport2_port = nport2_port
        self.listen_host = listen_host
        self.listen_port = listen_port
        self.timeout = timeout
        
        # Lock to prevent simultaneous transmissions on the 485 bus
        self.bus_lock = asyncio.Lock()
        
        # Connection tracking
        self.nport1_reader: Optional[asyncio.StreamReader] = None
        self.nport1_writer: Optional[asyncio.StreamWriter] = None
        self.nport2_reader: Optional[asyncio.StreamReader] = None
        self.nport2_writer: Optional[asyncio.StreamWriter] = None
        
        self.running = False
        
    async def connect_nport1(self) -> bool:
        """Connect to Moxa NPort 1 (Solar Inverter)."""
        try:
            logger.info(f"Connecting to NPort 1 at {self.nport1_host}:{self.nport1_port}")
            self.nport1_reader, self.nport1_writer = await asyncio.wait_for(
                asyncio.open_connection(self.nport1_host, self.nport1_port),
                timeout=self.timeout
            )
            logger.info("Successfully connected to NPort 1")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NPort 1: {e}")
            return False
    
    async def ensure_nport1_connected(self) -> bool:
        """Ensure NPort 1 is connected, reconnect if necessary."""
        if self.nport1_writer and self.nport1_reader:
            return True
        
        logger.warning("NPort 1 not connected, attempting to reconnect...")
        return await self.connect_nport1()
    
    async def connect_nport2(self) -> bool:
        """Connect to Moxa NPort 2 (External System)."""
        try:
            logger.info(f"Connecting to NPort 2 at {self.nport2_host}:{self.nport2_port}")
            self.nport2_reader, self.nport2_writer = await asyncio.wait_for(
                asyncio.open_connection(self.nport2_host, self.nport2_port),
                timeout=self.timeout
            )
            logger.info("Successfully connected to NPort 2")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to NPort 2: {e}")
            return False
    
    async def bridge_tcp_to_nport1(self, client_reader: asyncio.StreamReader, 
                                   client_writer: asyncio.StreamWriter):
        """
        Handle TCP client connections and bridge data to NPort 1 (solar inverter).
        
        Args:
            client_reader: StreamReader for client connection
            client_writer: StreamWriter for client connection
        """
        client_addr = client_writer.get_extra_info('peername')
        logger.info(f"New TCP client connected from {client_addr}")
        
        try:
            while self.running:
                # Read data from TCP client
                data = await asyncio.wait_for(client_reader.read(1024), timeout=self.timeout)
                
                if not data:
                    logger.info(f"TCP client {client_addr} disconnected")
                    break
                
                logger.debug(f"Received {len(data)} bytes from TCP client: {data.hex()}")
                
                # Ensure NPort 1 connection is available, reconnect if needed
                if not await self.ensure_nport1_connected():
                    logger.error("Cannot establish connection to NPort 1")
                    # Send error response to client or just continue
                    continue
                    
                # Acquire lock before transmitting on 485 bus
                async with self.bus_lock:
                    try:
                        # Forward data to NPort 1 (solar inverter)
                        self.nport1_writer.write(data)
                        await asyncio.wait_for(
                            self.nport1_writer.drain(),
                            timeout=self.timeout
                        )
                        logger.debug(f"Forwarded {len(data)} bytes to NPort 1")
                        
                        # Wait for response from solar inverter
                        try:
                            response = await asyncio.wait_for(
                                self.nport1_reader.read(1024), 
                                timeout=self.timeout
                            )
                            
                            if response:
                                logger.debug(f"Received {len(response)} bytes from NPort 1: {response.hex()}")
                                # Send response back to TCP client
                                client_writer.write(response)
                                await client_writer.drain()
                                logger.debug(f"Sent response back to TCP client")
                        except asyncio.TimeoutError:
                            logger.warning("Timeout waiting for response from NPort 1")
                    except Exception as e:
                        logger.error(f"Error communicating with NPort 1: {e}")
                        # Connection might be broken, clear it
                        self.nport1_reader = None
                        self.nport1_writer = None
                        
        except asyncio.TimeoutError:
            logger.info(f"TCP client {client_addr} timed out")
        except Exception as e:
            logger.error(f"Error handling TCP client {client_addr}: {e}")
        finally:
            client_writer.close()
            await client_writer.wait_closed()
            logger.info(f"TCP client {client_addr} connection closed")
    
    async def bridge_nport2_to_nport1(self):
        """
        Monitor NPort 2 (external system) and bridge data to NPort 1 (solar inverter).
        """
        logger.info("Starting NPort 2 to NPort 1 bridge")
        
        while self.running:
            try:
                if not self.nport2_reader:
                    logger.warning("NPort 2 not connected, attempting to reconnect...")
                    if not await self.connect_nport2():
                        await asyncio.sleep(5)
                        continue
                
                # Read data from NPort 2 (external system)
                data = await asyncio.wait_for(
                    self.nport2_reader.read(1024), 
                    timeout=1.0
                )
                
                if not data:
                    logger.warning("NPort 2 connection closed, reconnecting...")
                    if self.nport2_writer:
                        try:
                            self.nport2_writer.close()
                            await self.nport2_writer.wait_closed()
                        except Exception as e:
                            logger.error(f"Error closing NPort 2 connection: {e}")
                    self.nport2_reader = None
                    self.nport2_writer = None
                    await asyncio.sleep(1)
                    continue
                
                logger.debug(f"Received {len(data)} bytes from NPort 2: {data.hex()}")
                
                # Ensure NPort 1 connection is available, reconnect if needed
                if not await self.ensure_nport1_connected():
                    logger.error("Cannot establish connection to NPort 1")
                    await asyncio.sleep(1)
                    continue
                
                # Acquire lock before transmitting on 485 bus
                async with self.bus_lock:
                    try:
                        # Forward data to NPort 1 (solar inverter)
                        self.nport1_writer.write(data)
                        await asyncio.wait_for(
                            self.nport1_writer.drain(),
                            timeout=self.timeout
                        )
                        logger.debug(f"Forwarded {len(data)} bytes from NPort 2 to NPort 1")
                        
                        # Wait for response from solar inverter
                        try:
                            response = await asyncio.wait_for(
                                self.nport1_reader.read(1024), 
                                timeout=self.timeout
                            )
                            
                            if response:
                                logger.debug(f"Received {len(response)} bytes from NPort 1: {response.hex()}")
                                # Send response back to NPort 2
                                if self.nport2_writer:
                                    self.nport2_writer.write(response)
                                    await self.nport2_writer.drain()
                                    logger.debug(f"Sent response back to NPort 2")
                        except asyncio.TimeoutError:
                            logger.warning("Timeout waiting for response from NPort 1")
                    except Exception as e:
                        logger.error(f"Error communicating with NPort 1: {e}")
                        # Connection might be broken, clear it
                        self.nport1_reader = None
                        self.nport1_writer = None
                        
            except asyncio.TimeoutError:
                # No data available, continue loop
                continue
            except Exception as e:
                logger.error(f"Error in NPort 2 to NPort 1 bridge: {e}")
                # Clean up NPort 2 connection on error
                if self.nport2_writer:
                    try:
                        self.nport2_writer.close()
                        await self.nport2_writer.wait_closed()
                    except Exception:
                        pass
                self.nport2_reader = None
                self.nport2_writer = None
                await asyncio.sleep(1)
    
    async def start_tcp_server(self):
        """Start TCP server to listen for external connections."""
        server = await asyncio.start_server(
            self.bridge_tcp_to_nport1,
            self.listen_host,
            self.listen_port
        )
        
        addr = server.sockets[0].getsockname()
        logger.info(f"TCP server listening on {addr}")
        
        async with server:
            await server.serve_forever()
    
    async def run(self):
        """Run the Modbus bridge."""
        logger.info("Starting Modbus Bridge...")
        self.running = True
        
        # Connect to NPort 1 (solar inverter) - this is critical
        if not await self.connect_nport1():
            logger.error("Failed to connect to NPort 1 (solar inverter). Exiting.")
            return
        
        # Try to connect to NPort 2 (external system) - but continue if it fails
        # as it will reconnect automatically
        await self.connect_nport2()
        
        # Start both the TCP server and NPort 2 bridge
        try:
            await asyncio.gather(
                self.start_tcp_server(),
                self.bridge_nport2_to_nport1()
            )
        except KeyboardInterrupt:
            logger.info("Received shutdown signal")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            await self.cleanup()
    
    async def cleanup(self):
        """Clean up connections."""
        logger.info("Cleaning up connections...")
        self.running = False
        
        if self.nport1_writer:
            self.nport1_writer.close()
            await self.nport1_writer.wait_closed()
        
        if self.nport2_writer:
            self.nport2_writer.close()
            await self.nport2_writer.wait_closed()
        
        logger.info("Cleanup complete")


def load_config():
    """Load configuration from environment variables."""
    try:
        config = {
            'nport1_host': os.getenv('NPORT1_HOST', '192.168.1.100'),
            'nport1_port': int(os.getenv('NPORT1_PORT', '4001')),
            'nport2_host': os.getenv('NPORT2_HOST', '192.168.1.101'),
            'nport2_port': int(os.getenv('NPORT2_PORT', '4002')),
            'listen_host': os.getenv('LISTEN_HOST', '0.0.0.0'),
            'listen_port': int(os.getenv('LISTEN_PORT', '5020')),
            'timeout': int(os.getenv('MODBUS_TIMEOUT', '3'))
        }
    except ValueError as e:
        logger.error(f"Invalid configuration value: {e}")
        logger.error("Please check that all port numbers and timeout values are valid integers")
        sys.exit(1)
    
    logger.info("Configuration loaded:")
    logger.info(f"  NPort 1 (Solar Inverter): {config['nport1_host']}:{config['nport1_port']}")
    logger.info(f"  NPort 2 (External System): {config['nport2_host']}:{config['nport2_port']}")
    logger.info(f"  TCP Server: {config['listen_host']}:{config['listen_port']}")
    logger.info(f"  Timeout: {config['timeout']}s")
    
    return config


async def main():
    """Main entry point."""
    config = load_config()
    
    bridge = ModbusBridge(
        nport1_host=config['nport1_host'],
        nport1_port=config['nport1_port'],
        nport2_host=config['nport2_host'],
        nport2_port=config['nport2_port'],
        listen_host=config['listen_host'],
        listen_port=config['listen_port'],
        timeout=config['timeout']
    )
    
    await bridge.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application stopped by user")
        sys.exit(0)
