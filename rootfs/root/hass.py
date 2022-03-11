import asyncio
import json
import websockets
import os


ws_url = "ws://supervisor/core/websocket"

class HassWs:
    def __init__(self, sensors, update_callback: callable, token: str):
        print("Websocket: Setup listener")
        self._url = ws_url
        self._updater = update_callback
        self._token = token
        self._sensors= sensors

    async def run(self):
        connection_states = [
            (   {"type": "auth_required"},
                {'type': 'auth','access_token': self._token}),
            (   {"type": "auth_ok"},
                {'id': 1, 'type': 'get_states'}),
            (   {"id": 1, "type": "result", "success": True },
                {'id': 2, 'type': 'subscribe_trigger', 'trigger': {"platform": "state", "entity_id":self._sensors} }),
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
                    raise ValueError("Unexpected response from Supervisor while connecting.")

            while True:
                message = await websocket.recv()
                if message is None:
                    print("Websocket: Terminated.")
                    raise TimeoutError("Websocket: Terminated.")
                try:   
                    data = json.loads(message)['event']['variables']["trigger"]["to_state"]
                    entity_id = data['entity_id']
                    self._updater(data['entity_id'], data)
                except Exception:
                    pass
