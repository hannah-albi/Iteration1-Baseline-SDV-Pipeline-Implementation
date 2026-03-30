import asyncio
import os
import json
import time
import zenoh
import httpx
from kuksa_client.grpc.aio import VSSClient

KUKSA_HOST = os.getenv("KUKSA_HOST", "localhost")
KUKSA_PORT = int(os.getenv("KUKSA_PORT", "55555"))
DITTO_HOST = os.getenv("DITTO_HOST", "localhost")
DITTO_PORT = os.getenv("DITTO_PORT", "8080")
DITTO_URL  = f"http://{DITTO_HOST}:{DITTO_PORT}"
THING_ID   = "org.vehicle:my-device"

SIGNAL_MAP = {
    "Vehicle.Speed":                                              "VehicleSpeed",
    "Vehicle.OBD.EngineSpeed":                                   "EngineSpeed",
    "Vehicle.OBD.ThrottlePosition":                              "ThrottlePosition",
    "Vehicle.OBD.CoolantTemperature":                            "CoolantTemperature",
    "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current":  "BatteryStateOfCharge",
}

HEADERS = {
    "x-ditto-pre-authenticated": "nginx:ditto",
    "Content-Type": "application/json"
}

async def update_ditto(client, feature, value):
    url = f"{DITTO_URL}/api/2/things/{THING_ID}/features/{feature}/properties/value"
    r = await client.put(url, json=value, headers=HEADERS)
    print(f"Ditto {feature}={round(value,2)} → {r.status_code}", flush=True)

async def main():
    print("Bridge starting...", flush=True)

    # Connect to Zenoh router
    conf = zenoh.Config()
    conf.insert_json5("connect/endpoints", '["tcp/localhost:7447"]')
    session = zenoh.open(conf)
    print("Zenoh session opened!", flush=True)

    async with httpx.AsyncClient(timeout=5) as http:
        while True:
            try:
                print("Connecting to Kuksa...", flush=True)
                async with VSSClient(KUKSA_HOST, KUKSA_PORT) as kuksa:
                    print("Connected to Kuksa!", flush=True)
                    async for updates in kuksa.subscribe_current_values(list(SIGNAL_MAP.keys())):
                        for vss_path, datapoint in updates.items():
                            if datapoint is None:
                                continue
                            feature = SIGNAL_MAP.get(vss_path)
                            if not feature:
                                continue
                            value = datapoint.value
                            # Defining send time
                            send_ts = time.time()
                            # Printing the send time of feature
                            print(f"SENT {feature}={round(value,2)} at {send_ts:.2f}", flush=True)
                            # Publish through Zenoh
                            payload = json.dumps({"feature": feature, "value": value, "ts": send_ts})
                            session.put(f"vehicle/{feature.lower()}", payload)

                            # Iteration 2 extension -- message delay within communication layer & 
                            # latency measurement 
                            if feature == "VehicleSpeed":
                                print("Applying delay...", flush=True)
                                await asyncio.sleep(5)
                            
                            # Forward to Ditto
                            await update_ditto(http, feature, value)

                            recv_ts = time.time()
                            print(f"RECEIVED {feature}={round(value,2)} at {recv_ts:.2f} | latency={recv_ts - send_ts:.2f}s", flush=True)

            except Exception as e:
                print(f"Error: {e} — retrying in 5s", flush=True)
                await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
