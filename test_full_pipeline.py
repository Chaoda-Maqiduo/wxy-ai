import requests, time, sys

BASE = "http://localhost:10461/api/v1/thesis"
TITLE = "区块链技术在供应链金融中的应用模式与风险控制研究"
TARGET = 10000

print(f"=== 全流程测试: {TITLE} ({TARGET}字) ===\n")

# 1. 大纲
print("[1/4] 生成大纲...")
r = requests.post(f"{BASE}/outline", json={"title": TITLE, "target_word_count": TARGET}, timeout=60)
r.raise_for_status()
outline = r.json()["outline"]
print(f"  ✅ 大纲 OK ({len(outline)} 字符)\n")

# 2. 提交生成
print("[2/4] 提交论文生成任务...")
payload = {
    "title": TITLE, "outline": outline, "author": "张三", "advisor": "李教授",
    "degree_type": "工学学士", "major": "信息管理与信息系统",
    "school": "测试大学信息学院", "target_word_count": TARGET,
}
r2 = requests.post(f"{BASE}/generate", json=payload, timeout=60)
r2.raise_for_status()
task_id = r2.json()["task_id"]
print(f"  ✅ 任务ID: {task_id}\n")

# 3. 轮询
print("[3/4] 等待生成完成...")
start = time.time()
result = None
for i in range(300):
    time.sleep(10)
    d = requests.get(f"{BASE}/status/{task_id}", timeout=10).json()
    elapsed = int(time.time() - start)
    s = d.get("status")
    print(f"  [{elapsed:>3}s] {s}")
    if s == "completed":
        result = d; break
    elif s == "failed":
        print(f"  ❌ 失败: {d.get('message')}"); sys.exit(1)

if not result:
    print("  ❌ 超时"); sys.exit(1)

# 4. 汇总
chars = result.get("fulltext_char_count", 0)
figs = result.get("figure_count", 0)
docx = result.get("docx_path", "")
print(f"\n[4/4] === 测试结果 ===")
print(f"  目标字数:   {TARGET}")
print(f"  实际字符数: {chars}")
print(f"  图表数量:   {figs}")
print(f"  文档路径:   {docx}")
print(f"  总耗时:     {int(time.time()-start)}s")

# 5. 验证路径穿越防御
print(f"\n[BONUS] 路径穿越防御测试...")
r3 = requests.get(f"{BASE}/status/../../.env", timeout=5)
print(f"  GET /status/../../.env -> HTTP {r3.status_code} ({'✅ 已拦截' if r3.status_code == 422 else '❌ 未拦截!'})")

print(f"\n=== 全部完成 ===")
