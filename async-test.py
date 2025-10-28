import asyncio
import time
from datetime import datetime

import random



async def sensor_a():
    interval = 1.0
    for i in range(n_test):
        await asyncio.sleep(interval)
        random_int = random.random()
        now = datetime.now().isoformat(timespec='microseconds')
        print(f"[Sensor A] Measurement at t = {round(time.time() - start_time, 3)}s | Time: {now} | Test Number: {i} | Random Number")

async def sensor_b():
    interval = 1.5
    for i in range(n_test):
        await asyncio.sleep(interval)
        now = datetime.now().isoformat(timespec='microseconds')
        print(f"[Sensor B] Measurement at t = {round(time.time() - start_time, 3)}s | Time: {now} | Test Number: {i}")

async def sensor_c():
    interval = 2.0
    for i in range(n_test):
        await asyncio.sleep(interval)
        now = datetime.now().isoformat(timespec='microseconds')
        print(f"[Sensor C] Measurement at t = {round(time.time() - start_time, 3)}s | Time: {now} | Test Number: {i}")

async def normal_sleep_test():
    interval = 2.0
    for i in range(n_test):
        time.sleep(1)
        now = datetime.now().isoformat(timespec='microseconds')
        print(f"[Normal Sleep Test] Measurement at t = {round(time.time() - start_time, 3)}s | Time: {now} | Test Number: {i}")

async def main():
    global start_time
    global n_test
    n_test = 5

    Sleep_test = input('[Y] or [N]').lower()
    sensors=[sensor_a(), sensor_b(), sensor_c()]
    if Sleep_test=='y':
        sensors.append(normal_sleep_test())
    
    start_time = time.time()
    start_timer = datetime.now().isoformat(timespec='microseconds')
    print(f"Start Time : {start_timer}")

    perf_start = time.perf_counter()
    await asyncio.gather(*sensors)
    perf_end = time.perf_counter()

    print(f"Total execution time: {perf_end - perf_start:.6f} seconds")

asyncio.run(main())
