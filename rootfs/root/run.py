from vbus import *
from hass import *
import asyncio
import json
import os

config = {}
with open(os.environ["CONFIG"]) as f:
    config = json.load(f)

print(f'Configuration:\n{json.dumps(config, indent=4)}\n\n')

connection = Connection(config["host"], config['password'])
device_emulator = DeviceEmulator(connection, config["sensors"], 1)
hass_ws = HassWs(config["sensors"], device_emulator.update, os.environ["SUPERVISOR_TOKEN"])

loop = asyncio.get_event_loop()
tasks = [device_emulator.run(), hass_ws.run()]

if config["json_server"]:
    port = 26514
    if "port" in config:
        port = config["port"]
    json_server = BusDataServer(connection, port)
    tasks.append(json_server.run())

connection.start()

finished, unfinished = loop.run_until_complete(
    asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION))

print(f"Task exited unexpected:{finished}")
loop.run_until_complete(asyncio.sleep(30))
loop.close()
