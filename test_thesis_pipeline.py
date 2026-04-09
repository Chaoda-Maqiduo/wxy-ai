import requests
import json
import time
import sys

BASE_URL = "http://localhost:10461/api/v1/thesis"

title = "基于量子纠缠的保密通信协议分析与仿真研究"
print(f"1. Requesting outline for: {title}")
res = requests.post(f"{BASE_URL}/outline", json={"title": title})
if res.status_code != 200:
    print("Failed to get outline:", res.text)
    sys.exit(1)

outline_data = res.json()
print("Outline received!")

print("2. Submitting thesis generation task...")
payload = {
    "title": title,
    "outline": outline_data.get("outline", ""),
    "author": "张三",
    "advisor": "李四教授",
    "degree_type": "理学学士",
    "major": "物理学",
    "school": "测试大学理学院",
    "target_word_count": 8000,
    "target_word_count_max": 10000
}

res2 = requests.post(f"{BASE_URL}/generate", json=payload)
if res2.status_code != 200:
    print("Failed to start generation:", res2.text)
    sys.exit(1)

task_id = res2.json().get("task_id")
print("Task submitted, task_id:", task_id)

print("3. Polling status...")
for i in range(300): # max 50 mins
    time.sleep(10)
    try:
        res3 = requests.get(f"{BASE_URL}/status/{task_id}")
        if res3.status_code == 200:
            status_data = res3.json()
            status = status_data.get("status")
            print(f"[{i*10}s] Status: {status}")
            if status == "success":
                print("Generation complete! DOCX saved at:", status_data.get("docx_path"))
                sys.exit(0)
            elif status == "failed":
                print("Generation failed:", status_data.get("message"))
                sys.exit(1)
        else:
            print("Poll error:", res3.text)
    except Exception as e:
        print("Poll exception:", e)

