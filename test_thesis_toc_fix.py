import requests
import sys
import time

BASE_URL = "http://localhost:10461/api/v1/thesis"
title = "乡村振兴战略背景下农村电商发展现状与对策研究"
TARGET_WORDS = 8000

print(f"1. Requesting outline: {title}, target={TARGET_WORDS}")
res = requests.post(f"{BASE_URL}/outline", json={"title": title, "target_word_count": TARGET_WORDS})
res.raise_for_status()
outline = res.json().get("outline", "")
print("Outline OK!")

print("2. Submitting thesis...")
payload = {
    "title": title, "outline": outline,
    "author": "李明", "advisor": "王教授",
    "degree_type": "管理学学士", "major": "电子商务",
    "school": "测试大学商学院", "target_word_count": TARGET_WORDS,
}
res2 = requests.post(f"{BASE_URL}/generate", json=payload)
res2.raise_for_status()
task_id = res2.json().get("task_id")
print(f"Task: {task_id}")

print("3. Polling...")
start = time.time()
for _ in range(300):
    time.sleep(10)
    d = requests.get(f"{BASE_URL}/status/{task_id}").json()
    status = d.get("status")
    elapsed = int(time.time() - start)
    print(f"[{elapsed}s] {status}")
    if status in ("completed", "success"):
        print(f"DONE! chars={d.get('fulltext_char_count')}, figures={d.get('figure_count')}, docx={d.get('docx_path')}")
        sys.exit(0)
    elif status == "failed":
        print("FAILED:", d.get("message"));
        sys.exit(1)
