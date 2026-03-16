import asyncio
import httpx
import os

DITTO_HOST = os.getenv("DITTO_HOST", "localhost")
DITTO_PORT = os.getenv("DITTO_PORT", "8080")
DITTO_URL  = f"http://{DITTO_HOST}:{DITTO_PORT}"
THING_ID   = "org.vehicle:my-device"
HEADERS    = {"x-ditto-pre-authenticated": "nginx:ditto"}

THRESHOLDS = {
    "VehicleSpeed":       {"warn": 100, "critical": 120},
    "EngineSpeed":        {"warn": 6000, "critical": 7500},
    "ThrottlePosition":   {"warn": 80, "critical": 95},
    "CoolantTemperature": {"warn": 100, "critical": 110},
    "BatteryStateOfCharge": {"warn": 25, "critical": 10, "invert": True},
}

def status(feature, value):
    t = THRESHOLDS.get(feature, {})
    if not t:
        return "OK"
    invert = t.get("invert", False)
    if invert:
        if value <= t["critical"]: return "CRITICAL"
        if value <= t["warn"]:     return "WARNING"
    else:
        if value >= t["critical"]: return "CRITICAL"
        if value >= t["warn"]:     return "WARNING"
    return "OK"

def color(s):
    return {"OK": "", "WARNING": "(!)", "CRITICAL": "(!!)"}[s]

async def main():
    async with httpx.AsyncClient(timeout=5) as client:
        while True:
            try:
                r = await client.get(
                    f"{DITTO_URL}/api/2/things/{THING_ID}/features",
                    headers=HEADERS
                )
                features = r.json()
                print("\033[2J\033[H", end="")  # clear screen
                print("=" * 45)
                print("   SDV LIVE MONITOR — org.vehicle:my-device")
                print("=" * 45)
                for feature, data in features.items():
                    value = data.get("properties", {}).get("value", 0)
                    s = status(feature, value)
                    print(f"  {feature:<28} {value:>8.2f}  {color(s)}")
                print("=" * 45)
                print("  OK | (!) WARNING | (!!) CRITICAL")
            except Exception as e:
                print(f"Error: {e}")
            await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(main())