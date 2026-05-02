# Vehicle Maintenance Scheduler

Optimises daily vehicle maintenance task selection per depot using **0/1 Knapsack dynamic programming**.

## Problem

Each depot has a fixed **mechanic-hour budget**. A pool of maintenance tasks is available, each with a `Duration` (hours) and an `Impact` score (operational importance). The goal is to select the subset of tasks that maximises total impact without exceeding the budget.

## Algorithm

**0/1 Knapsack — Bottom-up Dynamic Programming**

```
dp[i][w] = max impact using first i tasks with budget w
```

- **Time complexity:** O(N × W) — N = tasks, W = mechanic-hour budget
- **Space complexity:** O(N × W) — for N=30, W≤200: a 6,000-cell table (negligible)
- **Correctness:** Guaranteed optimal — explores every feasible subset implicitly

After filling the DP table, the selected task set is recovered via backtracking.

## Setup & Usage

```bash
pip install requests

# Run against live API (set your key first)
export API_KEY=<your-api-key>
python3 scheduler.py

# Run in demo mode (uses data from the problem sheet, no API key needed)
python3 scheduler.py --demo
```

## API Endpoints Used

| Endpoint | Description |
|----------|-------------|
| `GET /evaluation-service/depots` | Returns depot IDs and mechanic-hour budgets |
| `GET /evaluation-service/vehicles` | Returns tasks with Duration and Impact |

Both are protected routes — pass your key via the `API_KEY` environment variable.

## Results (Demo data)

| Depot | Budget (h) | Used (h) | Tasks Selected | Max Impact |
|-------|-----------|---------|----------------|------------|
| 1     | 60        | 60      | 17             | 117        |
| 2     | 135       | 135     | 29             | 169        |
| 3     | 188       | 142     | 30             | 170        |
| 4     | 97        | 97      | 23             | 154        |
| 5     | 164       | 142     | 30             | 170        |

Depots 3 & 5 reach full task saturation (all 30 tasks still don't use their entire budget).

## Files

| File | Description |
|------|-------------|
| `scheduler.py` | Main script — fetches data, runs knapsack, prints results |
| `results.json` | JSON output of the last run |
| `README.md` | This file |
| `output_screenshot.png` | Terminal output screenshot |
