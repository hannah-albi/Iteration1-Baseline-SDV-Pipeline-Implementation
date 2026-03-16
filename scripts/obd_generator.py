import asyncio
import random
import os

KUKSA_HOST = os.getenv("KUKSA_HOST", "localhost")
KUKSA_PORT = int(os.getenv("KUKSA_PORT", "55555"))

SIGNALS = {
    "Vehicle.Speed":                                       (0.0,   255.0),
    "Vehicle.OBD.EngineSpeed":                            (600.0, 8000.0),
    "Vehicle.OBD.ThrottlePosition":                       (0.0,   100.0),
    "Vehicle.OBD.CoolantTemperature":                     (70.0,  120.0),
    "Vehicle.Powertrain.TractionBattery.StateOfCharge.Current":   (0.0,   100.0),
}

state = {path: (low + high) / 2 for path, (low, high) in SIGNALS.items()}

def next_values():
    for path, (low, high) in SIGNALS.items():
        delta = random.uniform(-0.05, 0.05) * (high - low)
        state[path] = round(max(low, min(high, state[path] + delta)), 2)
    return dict(state)

async def main():
    print("Script started!", flush=True)
    print(f"Connecting to Kuksa at {KUKSA_HOST}:{KUKSA_PORT}", flush=True)

    from kuksa_client.grpc.aio import VSSClient
    from kuksa_client.grpc import Datapoint

    while True:
        try:
            print("Attempting connection...", flush=True)
            async with VSSClient(KUKSA_HOST, KUKSA_PORT) as client:
                print("Connected to Kuksa!", flush=True)
                i = 0
                while True:
                    values = next_values()
                    await client.set_current_values({
                        path: Datapoint(val) for path, val in values.items()
                    })
                    i += 1
                    print(f"[#{i}] Speed={values['Vehicle.Speed']} | "
                          f"RPM={values['Vehicle.OBD.EngineSpeed']} | "
                          f"Battery={values['Vehicle.Powertrain.TractionBattery.StateOfCharge.Current']}%",
                          flush=True)
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"Error: {e} — retrying in 5s", flush=True)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())