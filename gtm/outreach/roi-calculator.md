# IT Operations Automation — ROI Calculator

**Ant Automations**
**Version:** 1.0 · April 2026

---

## How to Use This Calculator

Fill in the **Customer Inputs** section with data from the Discovery call or the prospect's own estimates. The calculator produces a savings estimate, payback period, and non-financial benefits summary suitable for inclusion in a pilot proposal.

---

## Section 1: Customer Inputs

### Workflow Economics

| Input | Description | Customer Value | Typical Range |
|---|---|---|---|
| **A. Number of target workflows** | Workflows in pilot scope | [___] | 1–3 |
| **B. Monthly task volume (total)** | Total tickets/requests per month across all target workflows | [___] | 200–2,000 |
| **C. Average manual time per task** | Minutes of human effort per task (across systems) | [___] min | 10–30 min |
| **D. Fully loaded FTE cost (annual)** | Annual cost per IT ops staff member (salary + benefits + overhead) | EUR [___] | EUR 50,000–80,000 |
| **E. Current error/rework rate** | % of tasks requiring manual correction or re-execution | [___]% | 3–8% |
| **F. Rework time per error** | Additional minutes spent fixing each error | [___] min | 15–45 min |

### Compliance & Audit

| Input | Description | Customer Value | Typical Range |
|---|---|---|---|
| **G. Quarterly audit prep hours** | Hours spent per quarter gathering evidence for access reviews / compliance audits | [___] hrs | 40–200 hrs |
| **H. Number of audits per year** | Internal + external audit cycles per year | [___] | 2–4 |

### Platform Investment

| Input | Description | Customer Value |
|---|---|---|
| **I. Pilot annual fee** | Ant Automations pilot tier pricing | EUR [___] (typical: 15,000–30,000) |
| **J. Implementation fee** | One-time setup and integration (if applicable) | EUR [___] (typical: 0–5,000) |

---

## Section 2: Calculated Savings

### 2.1 Labour Savings from Task Automation

```
Hourly FTE cost         = D / (220 working days × 8 hours)
                        = EUR [___] / 1,760
                        = EUR [___] / hour

Monthly manual hours    = B × C / 60
                        = [___] × [___] / 60
                        = [___] hours/month

Monthly manual cost     = Monthly manual hours × Hourly FTE cost
                        = [___] × EUR [___]
                        = EUR [___] / month

Annual manual cost      = Monthly manual cost × 12
                        = EUR [___] / year
```

**Automation rate assumption:** 70% of tasks fully automated, 20% partially automated (50% time reduction), 10% remain manual.

```
Automated savings       = (70% × Annual manual cost) + (20% × 50% × Annual manual cost)
                        = (0.70 × EUR [___]) + (0.10 × EUR [___])
                        = EUR [___] / year

Effective automation %  = 80% of total manual cost eliminated
```

### 2.2 Error/Rework Savings

```
Monthly errors          = B × E / 100
                        = [___] × [___]% 
                        = [___] errors/month

Monthly rework hours    = Monthly errors × F / 60
                        = [___] × [___] / 60
                        = [___] hours/month

Annual rework cost      = Monthly rework hours × 12 × Hourly FTE cost
                        = [___] × 12 × EUR [___]
                        = EUR [___] / year

Rework savings (95% elimination) = Annual rework cost × 0.95
                                 = EUR [___] / year
```

### 2.3 Audit Compliance Savings

```
Annual audit prep hours  = G × H
                         = [___] × [___]
                         = [___] hours/year

Annual audit prep cost   = Annual audit prep hours × Hourly FTE cost
                         = [___] × EUR [___]
                         = EUR [___] / year

Audit savings (80% reduction) = Annual audit prep cost × 0.80
                              = EUR [___] / year
```

### 2.4 Total Annual Savings

```
Total annual savings    = Automated savings + Rework savings + Audit savings
                        = EUR [___] + EUR [___] + EUR [___]
                        = EUR [___] / year
```

---

## Section 3: ROI Summary

```
Total annual investment = I + (J amortised if multi-year)
                        = EUR [___] / year

Net annual savings      = Total annual savings - Total annual investment
                        = EUR [___] - EUR [___]
                        = EUR [___] / year

ROI %                   = (Net annual savings / Total annual investment) × 100
                        = [___]%

Payback period          = Total annual investment / Total annual savings × 12
                        = [___] months
```

---

## Section 4: Example Calculation

**Scenario:** Mid-enterprise IT ops team, 3 workflows, moderate volume

| Input | Value |
|---|---|
| Target workflows | 3 |
| Monthly task volume | 800 |
| Average manual time | 20 min |
| FTE annual cost | EUR 65,000 |
| Error rate | 5% |
| Rework time | 30 min |
| Quarterly audit prep | 120 hrs |
| Audits per year | 4 |
| Pilot fee | EUR 25,000 |
| Implementation fee | EUR 0 |

**Results:**

| Metric | Value |
|---|---|
| Hourly FTE cost | EUR 36.93 |
| Annual manual cost | EUR 118,182 |
| Automated savings (80%) | EUR 94,545 |
| Annual rework cost | EUR 17,727 |
| Rework savings (95%) | EUR 16,841 |
| Annual audit prep cost | EUR 17,727 |
| Audit savings (80%) | EUR 14,182 |
| **Total annual savings** | **EUR 125,568** |
| **Net savings (after platform)** | **EUR 100,568** |
| **ROI** | **402%** |
| **Payback period** | **2.4 months** |

---

## Section 5: Non-Financial Benefits

Include these in the pilot proposal alongside the financial ROI:

| Benefit | Impact |
|---|---|
| **Reduced SLA breach rate** | Faster execution means fewer tickets breach response or resolution SLAs |
| **Faster onboarding** | New employee access provisioned in minutes instead of days |
| **Audit readiness** | Continuous audit evidence replaces quarterly scrambles |
| **Staff capacity** | Operations team redirected to higher-value work (process improvement, incident response) |
| **Consistency** | Every execution follows the same policy — no human variance |
| **Scalability** | Handle volume spikes without temporary staff or overtime |

---

## Section 6: Sensitivity Analysis

Show the prospect how savings scale with volume:

| Monthly Volume | Annual Manual Cost | Annual Savings (80%) | Payback (EUR 25K pilot) |
|---|---|---|---|
| 200 | EUR 29,545 | EUR 31,392 | 9.6 months |
| 500 | EUR 73,864 | EUR 72,730 | 4.1 months |
| 800 | EUR 118,182 | EUR 125,568 | 2.4 months |
| 1,200 | EUR 177,273 | EUR 185,068 | 1.6 months |
| 2,000 | EUR 295,455 | EUR 303,068 | 1.0 months |

*Savings include labour, rework, and audit components. Assumes EUR 65K FTE cost, 20 min/task, 5% error rate, 120 hrs/quarter audit prep.*

---

## Usage Notes

- Use conservative inputs in proposals — round down volumes, round up times, use lower-bound FTE costs
- Always validate inputs with the prospect during Discovery
- Present the range (optimistic / conservative) rather than a single number
- Include the sensitivity table to show the prospect how savings scale
- The non-financial benefits section often matters more to CISOs and compliance leads than the financial ROI
