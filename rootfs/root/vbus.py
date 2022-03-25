import os
import jnius_config
jnius_config.set_classpath(os.environ["JAVA_CLASSES"])
from jnius import *

import queue
import asyncio
import time
from aiohttp import web
import json
import time
import logging

Specification = autoclass("de.resol.vbus.Specification")
spec = Specification.getDefaultSpecification()


class ConnectionCallback(PythonJavaClass):
    __javainterfaces__ = ['de/resol/vbus/ConnectionListener']
    _queue = queue.SimpleQueue()
    _bus_packets = {}

    @java_method('(Lde/resol/vbus/Connection;)')
    def connectionStateChanged(self, connection):
        pass

    @java_method("(Lde/resol/vbus/Connection;Lde/resol/vbus/Packet;)V")
    def packetReceived(self, connection, packet):
        self._queue.put(packet)
        pass
    
    @java_method("(Lde/resol/vbus/Connection;Lde/resol/vbus/Datagram;)V")
    def datagramReceived(self, connection, datagram):
        pass

    @java_method("(Lde/resol/vbus/Connection;)V")
    def connectionStateChanged(self, connection):
        pass

    def getCache(self):
        now = time.time()
        while not self._queue.empty():
            packet = self._queue.get()
            self._bus_packets[packet.getId()] = packet
        for id, packet in dict(self._bus_packets).items():
            ts = float(packet.getTimestamp()) / 1000
            diff = now - ts
            if diff > 60:
                del self._bus_packets[id]
        
        data = {}
        for pfv in spec.getPacketFieldValuesForHeaders(tuple(self._bus_packets.values())):
            data[pfv.getPacketFieldId()] = {"name": pfv.getName(),
                                            "value": pfv.formatText(),
                                            "value_raw": pfv.getRawValueDouble(),
                                            "source_name": spec.getSourceDeviceSpec(pfv.getPacket()).getName(),
                                            "destination_name": spec.getDestinationDeviceSpec(pfv.getPacket()).getName(),
                                            "unit": str(pfv.getPacketFieldSpec().getUnit().unitTextText).strip(),
                                            "type": pfv.getPacketFieldSpec().getType().name(),
                                            "channel": pfv.getPacketSpec().getChannel()
                                            }
        return data


class BusDataServer:
    logger=logging.getLogger("WServer")
    def __init__(self, connection, server_port):
        self.logger.info("Setup web app.")
        app = web.Application()
        app.add_routes([web.get('/data', self.data_request)])
        app.add_routes([web.get('/cgi-bin/get_resol_device_information', self.device_info_request)])
        self._server_port = server_port
        self._runner = web.AppRunner(app)
        self._bus_data = []

        self.logger.info("Listening to VBus.")
        self._callback = ConnectionCallback()
        connection.add_listener(self._callback)

    async def run(self):
        self.logger.info(f"Setup TCP web server on port {self._server_port}.")
        await self._runner.setup()
        site = web.TCPSite(self._runner, port=self._server_port)
        await site.start()
        while True:
            await asyncio.sleep(10)
            self._bus_data = self._callback.getCache()

    def data_request(self, request):
        return web.json_response(self._bus_data)
    
    def device_info_request(self, request):
        text = []
        text.append('vendor = "chiefdeputy"')
        text.append('product = "Resol-EmSimulator"')
        text.append('serial = ""')
        text.append(f'version = "{os.environ["BUILD_VERSION"]}"')
        text.append('build = ""')
        text.append('name = "addon_slug"')
        text.append('features = "emsimulator_custom_1"')
        return web.Response(text='\n'.join(text))


class Connection:
    logger = logging.getLogger("VBusCon")
    def __init__(self, host, password, port=80):
        # Create classes
        Addr = autoclass("java.net.InetAddress")
        Connection = autoclass('de.resol.vbus.Connection')
        #TcpDataSource = autoclass('de.resol.vbus.TcpDataSource')
        TcpDataSourceProvider = autoclass('de.resol.vbus.TcpDataSourceProvider')
        
        self.logger.info(f"Connecting to VBus device at {host}")
        dataSource = TcpDataSourceProvider.fetchInformation(Addr.getByName(host), port, 1500)
        dataSource.setLivePassword(password)
        # Bus address of a PC is 0x0020, using 0x0026 to avoid collisions
        # https://danielwippermann.github.io/resol-vbus/#/vsf
        self._connection = dataSource.connectLive(0, 0x0026)

    def start(self):
        self._connection.connect()

    def add_listener(self, callback):
        self._connection.addListener(callback)

    def get(self):
        return self._connection


class DeviceEmulator:
    logger = logging.getLogger("DevSim ")

    def __init__(self, connection, sensors, device_number=1):
        self._cache = {}
        self._data_init_done = False
        self._last_time = 0
        self._sensors = sensors

        EmDeviceEmulator = autoclass('de.resol.vbus.deviceemulators.EmDeviceEmulator')
        self._device = EmDeviceEmulator(connection.get(), device_number)

    async def run(self):
        self.logger.info("Connection manager started.")
        while self._data_init_done == False:
            await asyncio.sleep(0.25)

        # Start the device. This will start listening for EM request packets
        # and answering them with a reply packet containing the initial values
        self._device.start()
        self._update_sensors()

        while True:
            now = time.time() * 1000
            delta = min(int(now - self._last_time), 10000)
            self._last_time = now

            update_period = float(self._device.update(delta))
            if update_period < 1:
                update_period = 300.0
            await asyncio.sleep(update_period / 1000)

            self._update_sensors()

    def update(self, entity_id: str, new_state: dict):
        if entity_id is None:
            # Mass change and intial value setup
            for data in new_state:
                if data["entity_id"] in self._sensors:
                    #self._cache[entity_id] = {"state": data["state"], "attributes": data["attributes"]}
                    self._cache[data["entity_id"]] = data
            self._data_init_done = True

        elif entity_id in self._sensors:
            self._cache[entity_id] = new_state

    def _update_sensors(self):
        for entity_id, new_state in self._cache.items():
            index = self._sensors.index(entity_id) + 1
            if index > 6:
                self.logger.warning(f"Only 5 sensors supported atm. Ignoring change of {entity_id}")
                continue

            if new_state['state'] in ('on', 'off', 'unavailable', 'unknown'):
                if new_state['state'] == "on":
                    self._device.setResistorValueByNr(index, 0)
                else:
                    self._device.setResistorValueByNr(index, 4000)
                
                self.logger.info(f"\
                    {entity_id} switched sensor {index} to \
                    \"{'on' if new_state['state'] == 'on' else 'off'}\" on \
                    EM #{self._device.getSubAddress()}.")
            elif 'unit_of_measurement' in new_state['attributes']:
                if new_state['attributes']['unit_of_measurement'] == "°C":
                    value = new_state['state']
                    try:
                        value = float(value)
                    except:
                        value = 999.0
                    self._device.setResistorValueByNrAndPt1000Temperatur(index, value)
                    self.logger.info(f"{entity_id} set sensor {index} to {value}°C on EM #{self._device.getSubAddress()}.")
            else:
                self._device.setResistorValueByNr(index, new_state['state'])
                self.logger.info(f"{entity_id} set sensor {index} to {value} Ohms on EM #{self._device.getSubAddress()}.")
        self._cache = {}
