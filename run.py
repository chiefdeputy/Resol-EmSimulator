from time import sleep
import jnius_config
jnius_config.set_classpath('./vbus-0.7.0.jar')
from jnius import autoclass
import asyncio
import time
import json

class VBusCom:
    def __init__(self):

        # Create classes
        Addr = autoclass("java.net.InetAddress")
        Connection = autoclass('de.resol.vbus.Connection')
        TcpDataSource = autoclass('de.resol.vbus.TcpDataSource')
        TcpDataSourceProvider = autoclass('de.resol.vbus.TcpDataSourceProvider')
        EmDeviceEmulator = autoclass('de.resol.vbus.deviceemulators.EmDeviceEmulator')

        dataSource = TcpDataSourceProvider.fetchInformation(Addr.getByName("192.168.110.167"), 1500)
        dataSource.setLivePassword("vbus")
        connection = dataSource.connectLive(0, 0x0020)

        self.device1 = EmDeviceEmulator(connection, 1)
        self.device1.setResistorValueByNrAndPt1000Temperatur(1, -40)
        self.device1.setResistorValueByNrAndPt1000Temperatur(2, 0)
        self.device1.setResistorValueByNrAndPt1000Temperatur(3, 40)
        self.device1.setResistorValueByNrAndPt1000Temperatur(4, 80)
        self.device1.setResistorValueByNrAndPt1000Temperatur(5, 120)
        self.device1.setResistorValueByNrAndPt1000Temperatur(6, 160)

        # Start the device. This will start listening for EM request packets
        # and answering them with a reply packet containing the fake
        # sensor values set above.
        self.device1.start()

        # Establish the connection and start the listening background thread.
        connection.connect()
        self._last_time = time.time() * 1000

    async def update(self):
        while True:
            now = time.time() * 1000
            delta = int(now - self._last_time)
            self._last_time = now

            update_period = float(self.device1.update(delta))
            if update_period < 1:
                update_period = 300.0

            await asyncio.sleep(update_period / 1000)
    def __parse_config(self):
        self.config = json.load("/data/options.json")



vbus_com = VBusCom()

loop = asyncio.get_event_loop()
loop.run_until_complete(vbus_com.update())

loop.close()

pass