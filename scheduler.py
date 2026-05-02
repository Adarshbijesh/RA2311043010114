#!/usr/bin/env python3
"""
Vehicle Maintenance Scheduler
==============================
Fetches depot budgets and vehicle/task data from the protected evaluation API,
then solves a 0/1 Knapsack problem per depot to maximise total operational-impact
score within the available mechanic-hour budget.

Usage
-----
    export API_KEY=<your-key>
    python3 scheduler.py            # live API
    python3 scheduler.py --demo     # demo mode (embedded data from problem sheet)

Algorithm
---------
Classic bottom-up dynamic programming knapsack.
  Time  complexity : O(N x W)  — N = number of tasks, W = mechanic-hour budget
  Space complexity : O(N x W)  — DP table
  For N=30, W<=200: a 30x200 = 6,000 cell table — very fast.
"""

import os, sys, json, argparse, requests
from typing import TypedDict

# ── ANSI colours ──────────────────────────────────────────────────────────────
BOLD="\033[1m"; CYAN="\033[96m"; GREEN="\033[92m"
YELLOW="\033[93m"; RED="\033[91m"; DIM="\033[2m"; RESET="\033[0m"

# ── API config ────────────────────────────────────────────────────────────────
BASE_URL = "http://20.207.122.201/evaluation-service"
API_KEY  = os.getenv("API_KEY", "")
HEADERS  = {"x-api-key": API_KEY, "Accept": "application/json"}

# ── Embedded demo data (from the problem sheet) ───────────────────────────────
DEMO_DEPOTS = [
    {"ID":1,"MechanicHours":60}, {"ID":2,"MechanicHours":135},
    {"ID":3,"MechanicHours":188},{"ID":4,"MechanicHours":97},
    {"ID":5,"MechanicHours":164},
]
DEMO_TASKS = [
    {"TaskID":"264e638f-1c7a-4d67-9f9c-53f3d1766d37","Duration":1,"Impact":5},
    {"TaskID":"73ce9dca-1536-4a7a-9f1e-c67083afad61","Duration":6,"Impact":2},
    {"TaskID":"4b6e22ee-b4ed-45a4-a6af-5294b0d69f37","Duration":1,"Impact":3},
    {"TaskID":"d6372f32-852b-46a9-8e8c-e730fecc3c22","Duration":5,"Impact":5},
    {"TaskID":"ec40b581-bdfc-43e0-a047-871fdafe8167","Duration":7,"Impact":3},
    {"TaskID":"fb1e3165-67c9-4e96-a5c3-2d20085d293b","Duration":6,"Impact":3},
    {"TaskID":"330065c0-3815-4e10-a18a-b93b117e30a8","Duration":5,"Impact":1},
    {"TaskID":"72a91abc-4ed7-492c-9e99-348e7437953b","Duration":5,"Impact":9},
    {"TaskID":"8a7ff5b1-335c-4a2f-96d8-09c4a362e781","Duration":6,"Impact":10},
    {"TaskID":"08000114-9506-463d-ba2e-3343ec4e2e89","Duration":6,"Impact":6},
    {"TaskID":"a1e0b8e6-1076-4a2f-b83b-5e6017900033","Duration":6,"Impact":1},
    {"TaskID":"52635341-7c5f-475a-9839-4676f8fe5fd4","Duration":1,"Impact":5},
    {"TaskID":"9e08defa-7bb5-4a83-9e29-417165922894","Duration":6,"Impact":9},
    {"TaskID":"f92b0f39-35ec-47c3-a465-3e49c22185b6","Duration":2,"Impact":5},
    {"TaskID":"65c0d74a-82ef-4fcc-9d85-9b082bb85310","Duration":5,"Impact":7},
    {"TaskID":"68ee2f8d-4145-4472-bce9-1d0968a8092a","Duration":1,"Impact":1},
    {"TaskID":"8a294532-c7ee-4e19-803d-f98b7e73e8bc","Duration":8,"Impact":7},
    {"TaskID":"18c655b2-380d-4295-8905-863f0de32c8f","Duration":2,"Impact":9},
    {"TaskID":"436e87a6-2b5b-42b9-9c35-deaa2c8ef54e","Duration":2,"Impact":3},
    {"TaskID":"0a823f1b-03c3-4722-af40-e17a7b9ee0ff","Duration":2,"Impact":5},
    {"TaskID":"0bf780cb-1099-4f61-99bf-dec95a7063b6","Duration":3,"Impact":10},
    {"TaskID":"e716fb11-1064-4db7-9d76-06d19f4f6f67","Duration":5,"Impact":5},
    {"TaskID":"60586e47-ab9c-407d-85ca-1215084f3f41","Duration":8,"Impact":8},
    {"TaskID":"08635e52-dad5-4b78-8ab1-e55db53c0c18","Duration":8,"Impact":5},
    {"TaskID":"871ddcf5-0bba-4233-bf12-c776c496e314","Duration":7,"Impact":10},
    {"TaskID":"b57f17dc-db77-42bf-a7e9-8fec596ce498","Duration":7,"Impact":1},
    {"TaskID":"1d893de7-fbba-4c77-927b-e3076fe805d5","Duration":1,"Impact":8},
    {"TaskID":"1743e1b5-9dfd-4506-9905-98c3e054aee1","Duration":5,"Impact":8},
    {"TaskID":"48851915-eaf5-48ec-a20c-5074d7050c5f","Duration":8,"Impact":8},
    {"TaskID":"7d81e6ca-8f03-4c4a-9ec0-701f820c5655","Duration":7,"Impact":8},
]

# ── Types ─────────────────────────────────────────────────────────────────────
class Depot(TypedDict):
    ID: int; MechanicHours: int

class Task(TypedDict):
    TaskID: str; Duration: int; Impact: int

# ── API helpers ───────────────────────────────────────────────────────────────
def fetch_depots() -> list[Depot]:
    r = requests.get(f"{BASE_URL}/depots", headers=HEADERS, timeout=15)
    r.raise_for_status()
    d = r.json()
    return d.get("depots", d) if isinstance(d, dict) else d

def fetch_tasks() -> list[Task]:
    r = requests.get(f"{BASE_URL}/vehicles", headers=HEADERS, timeout=15)
    r.raise_for_status()
    d = r.json()
    return d.get("vehicles", d) if isinstance(d, dict) else d

# ── 0/1 Knapsack — bottom-up DP ──────────────────────────────────────────────
def knapsack(tasks: list[Task], capacity: int) -> tuple[int, list[Task]]:
    n, W = len(tasks), capacity
    dp = [[0]*(W+1) for _ in range(n+1)]
    for i, t in enumerate(tasks, 1):
        d, imp = t["Duration"], t["Impact"]
        for w in range(W+1):
            dp[i][w] = dp[i-1][w]
            if d <= w and dp[i-1][w-d]+imp > dp[i][w]:
                dp[i][w] = dp[i-1][w-d]+imp
    # backtrack
    sel, w = [], W
    for i in range(n, 0, -1):
        if dp[i][w] != dp[i-1][w]:
            sel.append(tasks[i-1]); w -= tasks[i-1]["Duration"]
    return dp[n][W], sel[::-1]

# ── Pretty printers ───────────────────────────────────────────────────────────
def banner(title: str, w: int = 74) -> None:
    print(f"\n{CYAN}{'='*w}\n  {BOLD}{title}{RESET}{CYAN}\n{'='*w}{RESET}")

def print_depot(depot: Depot, score: int, sel: list[Task]) -> None:
    budget = depot["MechanicHours"]
    used   = sum(t["Duration"] for t in sel)
    util   = used/budget*100 if budget else 0
    print(f"\n  {BOLD}Depot #{depot['ID']}{RESET}  |  "
          f"Budget: {YELLOW}{budget:>4}h{RESET}  |  "
          f"Used: {GREEN}{used:>4}h{RESET}  |  "
          f"Utilisation: {util:>5.1f}%  |  "
          f"Max Impact Score: {BOLD}{GREEN}{score}{RESET}")
    if not sel:
        print(f"    {RED}No tasks fit within budget.{RESET}"); return
    print(f"  {'TaskID':<40}  {'Dur':>5}  {'Impact':>6}")
    print(f"  {'-'*40}  {'-'*5}  {'-'*6}")
    for t in sel:
        ic = f"{GREEN}{t['Impact']:>6}{RESET}" if t["Impact"]>=8 else f"{t['Impact']:>6}"
        print(f"  {DIM}{t['TaskID']:<40}{RESET}  {t['Duration']:>5}h  {ic}")

# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true", help="Use embedded demo data")
    args = ap.parse_args()

    banner("Vehicle Maintenance Scheduler  —  0/1 Knapsack DP Optimisation")

    if args.demo:
        print(f"  {YELLOW}[DEMO MODE]{RESET} Using embedded data from problem sheet.\n")
        depots, tasks = DEMO_DEPOTS, DEMO_TASKS
    else:
        print("  Fetching data from live API …\n")
        try:
            depots = fetch_depots()
            print(f"  {GREEN}+{RESET}  Depots : {len(depots)} records")
        except Exception as e:
            print(f"  {RED}x  Depot fetch failed: {e}  — using demo data{RESET}")
            depots = DEMO_DEPOTS
        try:
            tasks = fetch_tasks()
            print(f"  {GREEN}+{RESET}  Tasks  : {len(tasks)} records")
        except Exception as e:
            print(f"  {RED}x  Task fetch failed: {e}  — using demo data{RESET}")
            tasks = DEMO_TASKS

    print(f"\n  {DIM}{len(depots)} depot(s)  |  {len(tasks)} task(s) available{RESET}")

    banner("Optimal Task Selection per Depot")
    results = []
    for depot in depots:
        score, sel = knapsack(tasks, depot["MechanicHours"])
        used = sum(t["Duration"] for t in sel)
        print_depot(depot, score, sel)
        results.append({"depot_id": depot["ID"], "budget": depot["MechanicHours"],
                         "used": used, "n_tasks": len(sel),
                         "task_ids": [t["TaskID"] for t in sel],
                         "max_impact": score})

    banner("Summary")
    fmt = "  {:<10}  {:>10}  {:>8}  {:>15}  {:>12}"
    print(fmt.format("DepotID","Budget (h)","Used (h)","Tasks Selected","Max Impact"))
    print(fmt.format("-"*10,"-"*10,"-"*8,"-"*15,"-"*12))
    for r in results:
        print(fmt.format(r["depot_id"],r["budget"],r["used"],r["n_tasks"],r["max_impact"]))

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.json")
    with open(out, "w") as f:
        json.dump({"depots": len(depots), "tasks": len(tasks), "results": results}, f, indent=2)
    print(f"\n  {GREEN}+{RESET}  Results saved to {out}")
    print(f"  {GREEN}Optimisation complete.{RESET}\n")

if __name__ == "__main__":
    main()
