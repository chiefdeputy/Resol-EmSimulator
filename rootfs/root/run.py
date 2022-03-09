#import os
#os.environ["PATH"] = os.environ["PATH"] + ";" + os.environ["JAVA_HOME"] + "\\bin\\server"

import jnius_config
jnius_config.set_classpath('/root/vbus.jar')
from jnius import autoclass
import asyncio
import time
import json
import os
from aiohttp import web
import websockets

class VBusCom:
    def __init__(self):
        self._config = self.__parse_config()
        self._cache = {}

        # Create classes
        Addr = autoclass("java.net.InetAddress")
        Connection = autoclass('de.resol.vbus.Connection')
        TcpDataSource = autoclass('de.resol.vbus.TcpDataSource')
        TcpDataSourceProvider = autoclass('de.resol.vbus.TcpDataSourceProvider')
        EmDeviceEmulator = autoclass('de.resol.vbus.deviceemulators.EmDeviceEmulator')

        dataSource = TcpDataSourceProvider.fetchInformation(Addr.getByName(self._config["host"]), 1500)
        dataSource.setLivePassword(self._config['password'])
        connection = dataSource.connectLive(0, 0x0020)

        self.device = EmDeviceEmulator(connection, 1)

        # Start the device. This will start listening for EM request packets
        # and answering them with a reply packet containing the fake
        # sensor values set above.
        self.device.start()

        # Establish the connection and start the listening background thread.
        connection.connect()
        self._last_time = time.time() * 1000

    async def connection(self):
        while True:
            now = time.time() * 1000
            delta = int(now - self._last_time)
            self._last_time = now

            update_period = float(self.device.update(delta))
            if update_period < 1:
                update_period = 300.0
            await asyncio.sleep(update_period / 1000)

            self.__update_sensors()

    def update(entity_id, new_state):
        if entity_id in self._config["sensors"]:
            self._cache[entity_id] = new_state

    def __update_sensors():
        for entity_id, new_state in self._cache.items():
            index = self._config["sensors"].index(entity_id)
            if new_state['attributes']['unit_of_measurement'] == "°C":
                self.device.setResistorValueByNrAndPt1000Temperatur(index, new_state['state'])
            else:
                self.device.setResistorValueByNr(index, new_state['state'])

    def __parse_config(self):
        config = {}
        with open("/data/options.json") as f:
            config = json.load(f)
        print(config)
        return config


class HassWs:
    def __init__(self, update_callback):
        print("Setup Ws listener")
        self._token = os.environ("SUPERVISOR_TOKEN")
        #self._url = "ws://hassio:8123/api/websocket"
        self._url = "ws://supervisor/core/websocket"
        self._updater = update_callback

    async def listener(self):
        print("Connecting Ws listener")
        async with websockets.connect(self._url) as websocket:
            print("Authenticating Ws listener")
            await websocket.send(json.dumps({'type': 'auth','access_token': self._token}))
            await websocket.send(json.dumps({'id':1, 'type': 'get_states'}))
            await websocket.send(json.dumps({'id': 2, 'type': 'subscribe_events', 'event_type': 'state_changed'}))

            print("Start socket...")
            while True:
                message = await websocket.recv()
                if message is None:
                    break
                try:   
                    data = json.loads(message)['event']['data']
                    entity_id = data['entity_id']
                    self._updater(data['entity_id'], data['new_state'])
                except Exception:
                    pass


class JsonServer:
    def request(self, request):
        print("JSON")
        return web.Response(text='Hello, world')

    def __init__(self):
        self.port = 8080

        print("Setup web app.")
        app = web.Application(debug=False)
        app.add_routes([web.get('/states', self.request)])
        self._runner = web.AppRunner(app)

    async def run(self):
        print("Setup TCP web server.")
        await self._runner.setup()
        site = web.TCPSite(self._runner, 'localhost', self.port)
        
        print("Start web site.")
        await site.start()
        print("Enter web tasks idle loop.")
        while True:
            await asyncio.sleep(3600)  


vbus_com = VBusCom()
hass_ws = HassWs(vbus_com.update)

loop = asyncio.get_event_loop()
tasks = [vbus_com.connection(), hass_ws.listener()]
tasks = [hass_ws.listener()]

if False:
    json_server = JsonServer()
    tasks.append(json_server.run())

finished, unfinished = loop.run_until_complete(
    asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED))

loop.close()
print(f"Task exited unexpected:{finished}")
print(unfinished)
