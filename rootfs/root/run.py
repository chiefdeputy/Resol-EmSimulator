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

config_path = "/data/options.json"
ws_url = "ws://supervisor/core/websocket"

config = {}

class VBusCom:
    def __init__(self):
        self._cache = {}
        self._data_init_done = False
        self._last_time = 0

        # Create classes
        Addr = autoclass("java.net.InetAddress")
        Connection = autoclass('de.resol.vbus.Connection')
        TcpDataSource = autoclass('de.resol.vbus.TcpDataSource')
        TcpDataSourceProvider = autoclass('de.resol.vbus.TcpDataSourceProvider')
        EmDeviceEmulator = autoclass('de.resol.vbus.deviceemulators.EmDeviceEmulator')

        dataSource = TcpDataSourceProvider.fetchInformation(Addr.getByName(config["host"]), 1500)
        dataSource.setLivePassword(config['password'])
        # Bus address of a PC is 0x0020, using 0x0026 to avoid collisions
        # https://danielwippermann.github.io/resol-vbus/#/vsf
        self._connection = dataSource.connectLive(0, 0x0026)
        self.device = EmDeviceEmulator(self._connection, 1)

    async def connection(self):
        print("Resol: Connection manager started.")
        while self._data_init_done == False:
            await asyncio.sleep(0.25)

        # Start the device. This will start listening for EM request packets
        # and answering them with a reply packet containing the initial values
        self.device.start()
        self._update_sensors()
        # Establish the connection and start the listening background thread.
        self._connection.connect()

        while True:
            now = time.time() * 1000
            delta = min(int(now - self._last_time), 10000)
            self._last_time = now

            update_period = float(self.device.update(delta))
            if update_period < 1:
                update_period = 300.0
            await asyncio.sleep(update_period / 1000)

            self._update_sensors()

    def update(self, entity_id: str, new_state: dict):
        if entity_id is None:
            # Mass change and intial value setup
            for data in new_state:
                if data["entity_id"] in config["sensors"]:
                    #self._cache[entity_id] = {"state": data["state"], "attributes": data["attributes"]}
                    self._cache[data["entity_id"]] = data
            self._data_init_done = True

        elif entity_id in config["sensors"]:
            self._cache[entity_id] = new_state

    def _update_sensors(self):
        for entity_id, new_state in self._cache.items():
            index = config["sensors"].index(entity_id) + 1
            if index > 6:
                print(f"Resol: Only 5 sensors supported atm. Ignoring change of {entity_id}")
                continue

            if new_state['state'] in ('on', 'off', 'unavailable', 'unknown'):
                if new_state['state'] == "on":
                    self.device.setResistorValueByNr(index, 0)
                else:
                    self.device.setResistorValueByNr(index, 4000)
                
                print(f"Resol: {entity_id} was switched {new_state['state']}.")
            elif 'unit_of_measurement' in new_state['attributes']:
                if new_state['attributes']['unit_of_measurement'] == "°C":
                    value = new_state['state']
                    try:
                        value = float(value)
                    except:
                        value = 999.0
                    self.device.setResistorValueByNrAndPt1000Temperatur(index, value)
                    print(f"Resol: {entity_id} was set to {value}°C.")
            else:
                self.device.setResistorValueByNr(index, new_state['state'])
                print(f"Resol: {entity_id} was set to {value} Ohms.")
        self._cache = {}


class HassWs:
    def __init__(self, update_callback: callable):
        print("Websocket: Setup listener")
        self._url = ws_url
        self._updater = update_callback

    async def listener(self):
        connection_states = [
            (   {"type": "auth_required"},
                {'type': 'auth','access_token': os.environ["SUPERVISOR_TOKEN"]}),
            (   {"type": "auth_ok"},
                {'id':1, 'type': 'get_states'}),
            (   {"id": 1, "type": "result", "success": True },
                {'id': 2, 'type': 'subscribe_trigger', 'trigger': {"platform": "state", "entity_id":config["sensors"]} }),
            (   {"id": 2, "type": "result", "success": True},
                {}
            )]

        print("Websocket: Connecting...")
        async with websockets.connect(self._url) as websocket:
            for state in connection_states:
                message = await asyncio.wait_for(websocket.recv(), 1)
                message = json.loads(message)
                #check if message contains values of expected answer
                if state[0].items() <= message.items():
                    if message["type"] == "result" and message["id"] == 1:
                        self._updater(None, message["result"])
                    elif message["type"] == "result" and message["id"] == 2:
                        print("Websocket: Connection established, listening to state events...")
                        break
                    await websocket.send(json.dumps(state[1]))
                else:
                    print("Websocket: Error. Expected message:")
                    print(state[0])
                    print("But got:")
                    print(message)
                    return

            while True:
                message = await websocket.recv()
                if message is None:
                    print("Websocket: Terminated.")
                    break
                try:   
                    data = json.loads(message)['event']['variables']["trigger"]["to_state"]
                    entity_id = data['entity_id']
                    self._updater(data['entity_id'], data)
                except Exception:
                    pass


class JsonServer:
    def request(self, request):
        print("JSON Server: New Get Request")
        return web.Response(text='Hello, world')

    def __init__(self):
        print("JSON Server: Setup web app.")
        app = web.Application(debug=False)
        app.add_routes([web.get('/states', self.request)])
        self._runner = web.AppRunner(app)

    async def run(self):
        print("JSON Server: Setup TCP web server.")
        await self._runner.setup()
        site = web.TCPSite(self._runner, 'localhost', 26514)
        await site.start()
        while True:
            await asyncio.sleep(3600)  



with open(config_path) as f:
    config = json.load(f)

vbus_com = VBusCom()
hass_ws = HassWs(vbus_com.update)

loop = asyncio.get_event_loop()
tasks = [vbus_com.connection(), hass_ws.listener()]

if config["json_server"]:
    json_server = JsonServer()
    tasks.append(json_server.run())

finished, unfinished = loop.run_until_complete(
    asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED))

loop.close()
print(f"Task exited unexpected:{finished}")
print(unfinished)
