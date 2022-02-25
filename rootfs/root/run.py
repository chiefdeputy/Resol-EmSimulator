from time import sleep
import jnius_config
jnius_config.set_classpath('/root/vbus-0.7.0.jar')
from jnius import autoclass
import asyncio
import time
import json
import os

class VBusCom:
    def __init__(self):
        self.config = self.__parse_config()

        # Create classes
        Addr = autoclass("java.net.InetAddress")
        Connection = autoclass('de.resol.vbus.Connection')
        TcpDataSource = autoclass('de.resol.vbus.TcpDataSource')
        TcpDataSourceProvider = autoclass('de.resol.vbus.TcpDataSourceProvider')
        EmDeviceEmulator = autoclass('de.resol.vbus.deviceemulators.EmDeviceEmulator')

        dataSource = TcpDataSourceProvider.fetchInformation(Addr.getByName("192.168.110.167"), 1500)
        dataSource.setLivePassword("vbus")
        connection = dataSource.connectLive(0, 0x0020)

        self.device = EmDeviceEmulator(connection, 1)

        # Start the device. This will start listening for EM request packets
        # and answering them with a reply packet containing the fake
        # sensor values set above.
        self.device.start()

        # Establish the connection and start the listening background thread.
        connection.connect()
        self._last_time = time.time() * 1000

    async def update(self):
        while True:
            now = time.time() * 1000
            delta = int(now - self._last_time)
            self._last_time = now

            update_period = float(self.device.update(delta))
            if update_period < 1:
                update_period = 300.0

            await asyncio.sleep(update_period / 1000)

    def __parse_config(self):
        config = {}
        with open("/data/options.json") as f:
            config = json.load(f)
        print(os.environ["SUPERVISOR_TOKEN"])
        print(config)
        return config



vbus_com = VBusCom()

loop = asyncio.get_event_loop()
loop.run_until_complete(vbus_com.update())

loop.close()

pass