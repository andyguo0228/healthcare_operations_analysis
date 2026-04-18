# Outpatient Oncology Operations Dashboard — Blueprint

> Designed against the existing Power BI semantic model (`*.tmdl`) for a synthetic outpatient oncology clinic. Assumes the model is already deployed; this document covers **model fixes, missing measures, and the report layout** needed to turn raw throughput data into operational decisions.

---

## 0. Executive Summary — What's Broken Before We Add Pages

You've already done ~70% of the work. The star schema is sound, the grain is handled (Rooms = event-level, Appointments = visit-level via `helper_arrivaltimes`), and the measure library has real DAX in it (not placeholder junk). But there are **six concrete issues** that will bite you on the first dashboard page. Fix these *before* you start laying out visuals — debugging a blank visual at 5pm on a Friday is not a personality trait worth cultivating.

| # | Issue | Severity | Fix |
|---|---|---|---|
| 1 | `Appointments[Provider ID]` is **hidden** but is the only link to `Providers` — you can't slice by provider name without exposing a path | 🟠 Medium | Keep hidden but confirm relationship is active + single-direction (1:*) |
| 2 | `Appointments[MRN]` → `Patients[MRN]` relationship uses MRN instead of `Patient ID` — works, but MRN is not the Patients PK in the data dictionary (`patient_id` is) | 🟡 Low | Leave it, but be aware `Unique Patients = DISTINCTCOUNT(Appointments[MRN])` is only accurate because MRN is 1:1 with patient_id in the synthetic data |
| 3 | No Providers ↔ Date relationship, and no Treatments ↔ Date relationship — limits time-based analysis on those dims | 🟠 Medium | Add inactive role-playing date relationship on `Treatments[Start Date]` for cohort analysis (use `USERELATIONSHIP`) |
| 4 | `Avg Wait Time (Min)` uses `AVERAGE(Rooms[Duration])` filtered on `Is Waiting Room = TRUE`. This averages **per-event minutes**, not **per-appointment wait minutes** — an appointment with two waiting-room stops gets double-weighted in the denominator | 🔴 High | Rewrite as `AVERAGEX` over appointments (see §3.2) |
| 5 | No measure for **room utilization** — your biggest operational lever (exam/infusion rooms) has no measure supporting it | 🔴 High | Add `Room Utilization %` and `Total Room Minutes` (see §3.2) |
| 6 | `Appts Rolling 3M Avg` divides by 3 regardless of whether 3 months of data exist → inflates early-period averages downward | 🟡 Low | Use `DIVIDE(COUNTROWS(Appointments), DISTINCTCOUNT('Date'[Month Year]))` within the period |

---

## 1. Dataset Summary

**Grain recap** (from `DATA_DICTIONARY.md` + TMDL partitions):

| Table | Grain | Row estimate | Role |
|---|---|---|---|
| `Patients` | 1 row / patient | ~few thousand | Dimension |
| `Providers` | 1 row / provider | ~dozens | Dimension |
| `Appointments` | 1 row / appointment (post-dedup in Power Query) | ~tens of thousands | Fact (visit-level) |
| `Rooms` | 1 row / room event / appointment | 3–7× `Appointments` | Fact (event-level) |
| `Treatments` | 1 row / patient line-of-therapy | ~1–3× patients | Fact (treatment line) |
| `Date` | 1 row / day | ~1,460 (4 yrs) | Dimension |
| `Sort Table` | 1 row / Room Type | 5 | Helper |
| `_Measures` | Empty | 0 | Measure holder ✅ |

**Key analytical themes the data supports:**
1. Throughput (volume, completion, no-show)
2. Patient flow & wait times (Rooms grain)
3. Provider productivity
4. Room/resource utilization
5. Patient mix (dx, insurance, stage)
6. Treatment pipeline (new starts, active lines, regimen mix)

**Key analytical themes it does NOT support (flag to stakeholders upfront):**
- Cost / revenue / billing — no financial fields exist
- Scheduling capacity vs. actual — no planned slot data, only actuals
- Patient satisfaction / outcomes — no PROMs or survival data

---

## 2. Data Model Fixes

### 2.1 Star Schema (ASCII)

```
                  ┌─────────────┐
                  │    Date     │◄──┐
                  └─────────────┘   │
                         ▲           │ (inactive, Start Date)
                         │ (active,  │
                         │  Appt Dt) │
                         │           │
   ┌──────────┐   ┌──────┴──────┐   │
   │ Patients │◄──┤ Appointments├───┼──────┐
   └──────────┘   └──────┬──────┘   │      │
        ▲                │           │      │
        │                │ 1:*       │      │
        │                ▼           │      │
        │         ┌─────────────┐    │      │
        │         │    Rooms    │    │      │
        │         └─────────────┘    │      │
        │                │           │      │
        │                │           │      │
        │         ┌──────┴──────┐    │      │
        │         │ Sort Table  │    │      │
        │         └─────────────┘    │      │
        │                            │      │
        │         ┌─────────────┐    │      │
        └─────────┤ Treatments  ├────┘      │
                  └─────────────┘           │
                                            │
                  ┌─────────────┐           │
                  │  Providers  │◄──────────┘
                  └─────────────┘
                        ▲
                        └─ Appointments.Provider ID (1:*)
```

### 2.2 Relationship Changes

| Action | From | To | Type | Direction | Active |
|---|---|---|---|---|---|
| **Add** | `Treatments[Start Date]` | `Date[Date]` | 1:* | Single | Inactive (role-play) |
| **Add** | `Treatments[End Date]` | `Date[Date]` | 1:* | Single | Inactive (role-play) |
| **Keep** | `Rooms[Appointment ID]` | `Appointments[Appointment ID]` | 1:* | Single | Active |
| **Reconsider** | `Rooms[Room Type]` → `Sort Table[Room Type]` | — | — | — | This autodetected relationship is fine but unnecessary — you're using `Sort Table` only for sort order. Consider collapsing `Sort Table` into a calculated column on `Rooms` and retiring the table (1 less moving part). |

### 2.3 Power Query Changes

Two things to fix in M:

**a) `Appointments` partition loses flags you'll want.** After dedup you keep flags like `New Patient Flag`, `Infusion Flag`, `Urgent Flag` — good. But you drop `Visit Type` context when joining `Rooms` back, which is fine. No change needed — flagged for awareness.

**b) `Rooms[Is Waiting Room]` hardcodes three room names.** If a new waiting room label appears (`"Chemo Waiting"`, `"Pre-Op Waiting"`), the logic silently breaks.

```m
// Replace the conditional column logic with:
#"Added Is Waiting Room" = Table.AddColumn(
    #"Renamed Columns",
    "Is Waiting Room",
    each Text.Contains([Room], "Waiting", Comparer.OrdinalIgnoreCase),
    type logical
)
```

**c) Add a calculated column on `Appointments` for day-of-week bucketing** (used in heatmap visual later):

```dax
Appt Day of Week = WEEKDAY(Appointments[Appointment Date], 2)  -- Mon = 1
Appt Hour = HOUR(Appointments[First Arrival])
```

---

## 3. DAX Measure Additions

Your existing `_Measures` table has 20 measures. You need roughly 12 more to support the dashboard pages below. All new measures grouped by folder.

### 3.1 Fixes to existing measures

```dax
// REPLACE the existing Avg Wait Time (Min) - it's currently averaging events, not visits
Avg Wait Time (Min) = 
VAR WaitByAppt = 
    ADDCOLUMNS(
        SUMMARIZE(Rooms, Appointments[Appointment ID]),
        "@Wait", 
            CALCULATE(
                SUM(Rooms[Duration]),
                Rooms[Is Waiting Room] = TRUE
            )
    )
RETURN
    AVERAGEX(WaitByAppt, [@Wait])
```

```dax
// REPLACE Appts Rolling 3M Avg - handles partial windows correctly
Appts Rolling 3M Avg = 
VAR _period = 
    CALCULATETABLE(
        VALUES('Date'[Month Year Sort]),
        DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -3, MONTH)
    )
VAR _months = COUNTROWS(_period)
VAR _visits = 
    CALCULATE(
        COUNTROWS(Appointments),
        DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -3, MONTH)
    )
RETURN
    DIVIDE(_visits, _months)
```

### 3.2 New measures — Folder: `Throughput`

```dax
YTD Appointments = TOTALYTD([Total Appointments], 'Date'[Date])

Appts MTD = TOTALMTD([Total Appointments], 'Date'[Date])

Appts QTD = TOTALQTD([Total Appointments], 'Date'[Date])

Completed Appointments = 
CALCULATE(
    [Total Appointments],
    Appointments[Status] = "Completed"
)
```

### 3.3 New measures — Folder: `Resource Utilization`

```dax
// Total clinical minutes consumed (excludes waiting rooms)
Total Exam Minutes = 
CALCULATE(
    SUM(Rooms[Duration]),
    Rooms[Room Type] = "Exam Room"
)

Total Infusion Minutes = 
CALCULATE(
    SUM(Rooms[Duration]),
    Rooms[Room Type] = "Infusion Room"
)

// Distinct rooms actually used in the selected period
Active Exam Rooms = 
CALCULATE(
    DISTINCTCOUNT(Rooms[Room]),
    Rooms[Room Type] = "Exam Room"
)

// Room utilization % against a nominal 8hr (480 min) operating day
// Assumes Mon-Fri; adjust _operatingDays if Sat clinics exist
Exam Room Utilization % = 
VAR _minutes = [Total Exam Minutes]
VAR _rooms = [Active Exam Rooms]
VAR _operatingDays = 
    CALCULATE(
        COUNTROWS('Date'),
        'Date'[Day of Week] <= 5
    )
VAR _capacity = _rooms * _operatingDays * 480
RETURN
    DIVIDE(_minutes, _capacity, 0)

Infusion Room Utilization % = 
VAR _minutes = [Total Infusion Minutes]
VAR _rooms = 
    CALCULATE(
        DISTINCTCOUNT(Rooms[Room]),
        Rooms[Room Type] = "Infusion Room"
    )
VAR _operatingDays = 
    CALCULATE(
        COUNTROWS('Date'),
        'Date'[Day of Week] <= 5
    )
VAR _capacity = _rooms * _operatingDays * 480
RETURN
    DIVIDE(_minutes, _capacity, 0)
```

### 3.4 New measures — Folder: `Wait Time Analysis`

```dax
// Median is more honest than average for wait times (long right tail)
Median Wait Time (Min) = 
VAR WaitByAppt = 
    ADDCOLUMNS(
        SUMMARIZE(Rooms, Appointments[Appointment ID]),
        "@Wait", 
            CALCULATE(
                SUM(Rooms[Duration]),
                Rooms[Is Waiting Room] = TRUE
            )
    )
RETURN
    MEDIANX(FILTER(WaitByAppt, [@Wait] > 0), [@Wait])

// 90th percentile - what does a "bad day" look like
P90 Wait Time (Min) = 
VAR WaitByAppt = 
    ADDCOLUMNS(
        SUMMARIZE(Rooms, Appointments[Appointment ID]),
        "@Wait", 
            CALCULATE(
                SUM(Rooms[Duration]),
                Rooms[Is Waiting Room] = TRUE
            )
    )
RETURN
    PERCENTILEX.INC(FILTER(WaitByAppt, [@Wait] > 0), [@Wait], 0.9)

// % of appts where patient waited > 20 min
Long Wait % = 
VAR WaitByAppt = 
    ADDCOLUMNS(
        SUMMARIZE(Rooms, Appointments[Appointment ID]),
        "@Wait", 
            CALCULATE(
                SUM(Rooms[Duration]),
                Rooms[Is Waiting Room] = TRUE
            )
    )
VAR _long = COUNTROWS(FILTER(WaitByAppt, [@Wait] > 20))
VAR _total = COUNTROWS(WaitByAppt)
RETURN
    DIVIDE(_long, _total, 0)
```

### 3.5 New measures — Folder: `Provider Performance`

```dax
// Number of distinct providers working in the period
Active Providers = 
CALCULATE(
    DISTINCTCOUNT(Appointments[Provider ID]),
    Appointments[Status] = "Completed"
)

// Average visits per provider per day they worked
Appts per Provider Day = 
VAR _providerDays = 
    SUMMARIZE(
        Appointments,
        Appointments[Provider ID],
        'Date'[Date]
    )
VAR _denom = COUNTROWS(_providerDays)
RETURN
    DIVIDE([Completed Appointments], _denom)

// Provider rank by volume - used in Top N filter
Provider Rank = 
RANKX(
    ALL(Providers[Provider Name]),
    [Total Appointments],
    ,
    DESC,
    Dense
)
```

### 3.6 New measures — Folder: `Treatment Pipeline`

```dax
// Total active treatment lines on selected date (snapshot)
Active Treatment Lines = 
CALCULATE(
    COUNTROWS(Treatments),
    Treatments[Active Flag] = 1
)

// New starts in period (uses inactive relationship via USERELATIONSHIP)
New Treatment Starts = 
CALCULATE(
    COUNTROWS(Treatments),
    USERELATIONSHIP(Treatments[Start Date], 'Date'[Date])
)

// Patients currently in active treatment (distinct)
Patients in Active Tx = 
CALCULATE(
    DISTINCTCOUNT(Treatments[Patient ID]),
    Treatments[Active Flag] = 1
)
```

---

## 4. Report Layout — 5 Pages

### Design principles
- **Every page answers ONE business question.** If you can't state it in 9 words, the page is wrong.
- **Top bar: Date slicer + reset button, always.** Cross-page synced.
- **Left panel: Secondary slicers (provider, visit type, dx group).** Cross-page synced.
- **Default state: Last 90 days.** Analysts will scroll back; execs will not.
- **Palette: your existing `#005F73` / `#EE9B00` / `#AE2012` gradient is fine.** Don't invent a new one.

---

### 📄 Page 1 — **Operational Overview** (Exec Summary)
**Business question:** *Are we running efficiently this month?*  
**Audience:** Clinic director, COO  
**Refresh cadence:** Daily

**Layout (16:9, 1280×720):**

```
┌─────────────────────────────────────────────────────────────────┐
│  [Title: Oncology Ops Dashboard]       [Date Range Slicer ▼]    │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                    │
│ │Total │ │Compl.│ │No-Show│ │Avg  │ │Unique│                    │
│ │Appts │ │ Rate │ │ Rate │ │Wait │ │Pats  │                    │
│ │ KPI  │ │ KPI  │ │ KPI  │ │ KPI │ │ KPI  │                    │
│ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘                    │
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────┐  ┌────────────────────────────────┐│
│ │ Appointments Trend       │  │ Status Breakdown               ││
│ │ (Line: Total + 3M Avg)   │  │ (100% stacked bar by month)    ││
│ │ x: Month  y: count       │  │                                ││
│ └──────────────────────────┘  └────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│ ┌──────────────────────────┐  ┌────────────────────────────────┐│
│ │ Top 10 Providers         │  │ Visit Mix                      ││
│ │ (Horizontal bar, DESC)   │  │ (Donut: Visit Type)            ││
│ │                          │  │                                ││
│ └──────────────────────────┘  └────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

**Visual-by-visual:**

| Visual | Type | Fields | Notes |
|---|---|---|---|
| Total Appts | Card | `[Total Appointments]` | Format: 0 |
| Completion Rate | Card | `[Completion Rate]` | Conditional format: green >90%, amber 85-90%, red <85% |
| No-Show Rate | Card | `[No-Show Rate]` | Color by `[NoShow Color]` measure you already have ✅ |
| Avg Wait | Card | `[Avg Wait Time (Min)]` (fixed version) | Color by `[Wait Time Color]` ✅ |
| Unique Patients | Card | `[Unique Patients]` | Format: 0 |
| Trend | Line chart | X: `Date[Month Year]` (sorted by `Month Year Sort`). Y1: `[Total Appointments]`, Y2: `[Appts Rolling 3M Avg]` | Secondary line should be dashed/gray |
| Status breakdown | 100% stacked column | X: `Date[Month Year]`. Legend: `Appointments[Status]`. Value: `[Total Appointments]` | |
| Top 10 Providers | Horizontal bar | Y: `Providers[Provider Name]`. X: `[Total Appointments]`. Sort: DESC. Filter: `[Provider Rank] ≤ 10` | |
| Visit Mix | Donut | Legend: `Appointments[Visit Type]`. Value: `[Total Appointments]` | |

---

### 📄 Page 2 — **Patient Flow & Wait Times**
**Business question:** *Where are patients getting stuck?*  
**Audience:** Operations manager, front-desk lead

**Key visuals:**

| Visual | Type | Fields | Why |
|---|---|---|---|
| Wait time distribution | Histogram (column) | X: wait-minute buckets (calc column: <5, 5-10, 10-20, 20-30, 30-60, 60+). Y: count of appointments | Exposes the right tail that an average hides |
| Median / Avg / P90 wait | Multi-row card | `[Median Wait Time (Min)]`, `[Avg Wait Time (Min)]`, `[P90 Wait Time (Min)]` | Three numbers, one story |
| Wait time by hour of day | Heatmap (matrix, cond format) | Rows: `Appt Hour` (calc col). Columns: `Date[Day Name Short]`. Values: `[Avg Wait Time (Min)]` | Reveals the 10am / Mon-Tue crush |
| Wait by visit type | Clustered bar | Axis: `Visit Type`. Values: `[Avg Wait Time (Min)]`, `[P90 Wait Time (Min)]` | Walk-ins vs scheduled is the real comparison |
| Room flow sequence | Decomposition tree or sankey (custom visual) | Analyze: `[Total Appointments]`. Explain by: `Rooms[Room Type]` via `Sequence` | Sankey is better if you have the custom visual enabled |
| Long Wait % trend | Line | X: `Date[Month Year]`. Y: `[Long Wait %]` | Is it getting better or worse? |

**Slicer specific to this page:** Room Type (multi-select).

---

### 📄 Page 3 — **Provider Performance**
**Business question:** *Who is over/under-booked and why?*  
**Audience:** Clinic director, physician leadership

| Visual | Type | Fields |
|---|---|---|
| Provider leaderboard | Table | Columns: `Provider Name`, `Years Experience`, `[Total Appointments]`, `[Completed Appointments]`, `[No-Show Rate]`, `[Avg Visit Duration (Min)]`, `[Appts per Provider Day]` |
| Volume vs experience | Scatter | X: `Years Experience`, Y: `[Appts per Provider Day]`, Size: `[Total Appointments]`, Details: `Provider Name` |
| Duration distribution | Box plot (custom visual) OR violin | Category: `Provider Name`. Value: appointment-level `Total Duration` |
| Provider × Visit Type matrix | Matrix | Rows: `Provider Name`. Columns: `Visit Type`. Values: `[Total Appointments]` with data bars |
| No-show by provider | Bar, conditional color | X: `[No-Show Rate]`. Y: `Provider Name`. Color by rate threshold |

**Why scatter over bar for volume vs experience:** a bar chart answers "who is busy"; the scatter answers "is experience predicting throughput"—which is the actual question leadership asks.

---

### 📄 Page 4 — **Resource Utilization**
**Business question:** *Are we under-using rooms we're paying for?*  
**Audience:** Facilities, CFO-adjacent

| Visual | Type | Fields |
|---|---|---|
| Exam Room Util % | Gauge or KPI card | `[Exam Room Utilization %]` vs target 75% |
| Infusion Room Util % | Gauge or KPI card | `[Infusion Room Utilization %]` vs target 80% |
| Minutes by room type (trend) | Stacked area | X: `Date[Month Year]`. Y: `SUM(Rooms[Duration])`. Legend: `Room Type` (uses `Sort Table` sort order ✅) |
| Utilization heatmap | Matrix, cond format | Rows: `Rooms[Room]`. Columns: `Date[Day Name Short]`. Values: `SUM(Rooms[Duration])` |
| Room-type sequence funnel | Funnel | Category: `Room Type` (by `Sequence`). Value: `[Total Appointments]` that touched each stage |

**Important note on the gauge:** you were told "avoid gauges" in the skill, and generally that's right. Here, a single-metric utilization % against a fixed target is one of the **three or four actual legitimate use cases** for a gauge. Use a KPI card if you disagree; I won't fight you.

---

### 📄 Page 5 — **Patient & Treatment Mix**
**Business question:** *Who are we treating, and with what?*  
**Audience:** Clinical leadership, population health

| Visual | Type | Fields |
|---|---|---|
| Patients by diagnosis | Treemap | Group: `Dx Group`. Detail: `Diagnosis`. Value: `DISTINCTCOUNT(Patient ID)` |
| Insurance mix | Donut | `Insurance`, count of patients |
| Age pyramid | Butterfly bar (native bar w/ neg values) | Bucket age into 10-yr bins; split by `Sex` |
| Active treatment lines over time | Line | X: `Date[Month Year]`. Y: `[Active Treatment Lines]` (using inactive relationship) |
| Regimen mix | Bar, sorted DESC | X: `[Total Appointments]`. Y: `Regimen Name` (top 15) |
| Stage × Dx Group matrix | Matrix with conditional formatting | Rows: `Diagnosis`. Columns: `Stage`. Values: DISTINCTCOUNT of patients |

---

## 5. Slicer & Interaction Strategy

### Synced slicers (sync across all 5 pages)
- Date range (top-right)
- Provider (dropdown)
- Visit Type (multi-select)
- Dx Group (tile — only 2 values)

### Page-specific slicers
- Page 2: Room Type, Day of Week
- Page 3: Years Experience range
- Page 4: Room Type
- Page 5: Age bucket, Stage

### Cross-filter rules (set via Format → Edit Interactions)
- Page 1: KPI cards should NOT cross-filter each other
- Page 3: Scatter plot should cross-filter the leaderboard; leaderboard should NOT cross-filter the scatter (preserves context)

---

## 6. Advanced Features Worth Adding

| Feature | When | Why |
|---|---|---|
| **Drillthrough to Appointment Detail** | Right-click any provider or patient | Execs need to eyeball the raw rows — build a "Detail" page hidden from nav |
| **Bookmarks: "Today vs Last 30d vs YTD" toggle** | Page 1 | Saves 3 slicer clicks. Navigator button in top bar. |
| **Field Parameter for Metric Selector** | Pages 2 & 3 | Let user swap what's on the Y axis between `Avg Wait`, `Median Wait`, `P90` without rebuilding 3 visuals. You already have a pattern for this. |
| **What-if Parameter: "Target No-Show Rate"** | Page 1 | Shows gap-to-target visually. Low effort, high perceived value. |
| **RLS by Provider** | If physicians get individual access | Filter `Providers[Provider ID]` = `USERNAME()` mapping table |
| **Incremental Refresh** | If you move off the SharePoint CSV | On `Appointments` partitioned by `Appointment Date`, keep last 13 months incremental, archive beyond that |

---

## 7. Things I'd Push Back On If This Were My Model

- **The CSV-over-SharePoint web fetch is a rough pattern.** Any auth expiry or URL change nukes the refresh. Migrate to a dataflow or a proper Fabric lakehouse source when you can. The current setup is fine for a prototype, not for production.
- **`Zip Code` is typed as `int64` and summarizes by `count`.** A leading-zero Bronx ZIP (`10467`) will survive this, but a Boston one (`02108`) becomes `2108`. Cast to text in Power Query if you ever map it.
- **No RLS means any report viewer sees everything.** Synthetic data today — fine. The minute this pattern is reused on real PHI, RLS is not optional, it's HIPAA.
- **`Comorbidity Score` is being used as a numeric sum (`summarizeBy: sum`)** — it's an ordinal, not an additive quantity. Summing it will produce nonsense on any visual. Change to `summarizeBy: none` or use `AVERAGE` explicitly in measures.

---

## 8. Build Checklist

Ordered. Don't skip ahead — each step depends on the prior.

1. Apply the **6 model fixes in §0** (30 min)
2. Add the **new relationships in §2.2** (10 min)
3. Rewrite `Avg Wait Time (Min)` and `Appts Rolling 3M Avg` per §3.1 (20 min)
4. Add the **12 new measures in §3.2–§3.6**, organized into folders (45 min)
5. Build **Page 1 (Overview)** end-to-end, validate against a known test case (1 hr)
6. Replicate slicer panel to Pages 2–5 using **Sync Slicers** (15 min)
7. Build Pages 2–5 per §4 (2–3 hrs each)
8. Add **drillthrough detail page** (30 min)
9. Add **bookmarks + Field Parameter** from §6 (1 hr)
10. Review with a real user. They will break something. That's the point.

**Total realistic build time: ~15–20 hours** if the model fixes land cleanly. Double it if you're also learning Power BI as you go.

---

*Blueprint version 1.0 — grounded in the provided `.tmdl` files, not a generic template.*
