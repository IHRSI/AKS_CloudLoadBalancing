<h1 align="center">
  Kubernetes Ingress Load Balancing:<br/>A Quantitative Analysis
</h1>

<p align="center">
  <img src="https://img.shields.io/badge/Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white" alt="Kubernetes" />
  <img src="https://img.shields.io/badge/Azure_AKS-0089D6?style=for-the-badge&logo=microsoft-azure&logoColor=white" alt="Azure AKS" />
  <img src="https://img.shields.io/badge/NGINX-009639?style=for-the-badge&logo=nginx&logoColor=white" alt="NGINX" />
  <img src="https://img.shields.io/badge/Locust-43B02A?style=for-the-badge&logoColor=white" alt="Locust" />
  <br/>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Numpy-777BB4?style=for-the-badge&logo=numpy&logoColor=white" alt="NumPy" />
  <img src="https://img.shields.io/badge/Pandas-150458?style=for-the-badge&logo=pandas&logoColor=white" alt="Pandas" />
  <img src="https://img.shields.io/badge/Matplotlib-11557c?style=for-the-badge&logoColor=white" alt="Matplotlib" />
</p>

<p align="center">
  <em>A rigorous, data-driven study evaluating NGINX Ingress routing strategies on Azure Kubernetes Service under simulated high-stress and fault-tolerant scenarios.</em>
</p>

---

## 📖 Overview

This project provides a comprehensive quantitative analysis of three distinct Kubernetes Ingress load-balancing algorithms:
1. **Round Robin** (Default)
2. **Least Connections** (Powered by EWMA - Exponentially Weighted Moving Average)
3. **IP Hashing** (Session Stickiness)

By subjecting a containerized web server (`mendhak/http-https-echo`) to simulated traffic using **Locust**, this project evaluates how different routing algorithms handle asymmetric workloads, large-scale traffic saturation, and sudden node failures (High Availability tests).

---

## ⚡ Core Findings

The following table summarizes the data automatically extracted and mathematically calculated across the 50-user, 100-user, and 200-user (Fault Tolerance) load tests:

| Metric | Round Robin | Least Connections (EWMA) | IP Hashing |
|---|---|---|---|
| **Avg Latency (ms)** | 89.8 | 86.9 | 87.3 |
| **P99 Latency (ms)** | 170.0 | 120.0 | 110.0 |
| **Throughput (RPS)** | 22.3 | 22.2 | 22.2 |
| **CPU Evenness (CV %)** | 0.1% | 10.8% | 95.5% |
| **Recovery Time (ms)** | 5111 | 5111 | 504 |

> [!NOTE] 
> **Coefficient of Variation (CV %)** measures statistical variance. A lower number means the load was distributed perfectly evenly across all Pods. **P99 Latency** reveals the worst-case response times hidden by simple averages.

---

## 🛠️ Architecture & Tools

* **Cloud Provider:** Azure Kubernetes Service (AKS) (2x `Standard_D2s_v4` VMs)
* **Ingress Controller:** NGINX Ingress Controller
* **Load Generator:** Locust (Python-based distributed testing framework)
* **Data Processing Pipeline:** Python, Pandas, Matplotlib, NumPy

---

## 📂 Project Documentation

This repository serves as both a codebase and an academic study guide.

* 🎓 **[`Comparative_Analysis_of_NGINX_Ingress_Load_Balancing_Algos.pdf`](./A_Comparative_Analysis_of_NGINX_Ingress_Load_Balancing_Algorithms.pdf)**: The final academic research paper formatted for IEEE, detailing the methodology, results, and conclusions of this study.
* 📄 **[`master_implementation_plan.md`](./master_implementation_plan.md)**: The step-by-step architectural blueprint, setup instructions, and the embedded Python analysis script.
* 📚 **[`comprehensive_study_guide.md`](./comprehensive_study_guide.md)**: A deeply theoretical breakdown of Cloud Computing, Kubernetes architecture, and what the data actually means.
* 📊 **[`analyze_results.py`](./analyze_results.py)**: A fully automated Python data extraction and visualization pipeline.

---

## 🗂️ Repository Structure

```text
.
├── 🎓 A_Comparative_Analysis_of_NGINX_Ingress_Load_Balancing_Algorithms.pdf
├── 📝 IEEE_Report_code.tex
├── 📄 master_implementation_plan.md
├── 📚 comprehensive_study_guide.md
├── 📊 analyze_results.py
├── 🐍 locustfile.py
├── ⚙️ deployment.yaml, service.yaml, ingress-*.yaml (Kubernetes Configs)
├── 🗂️ Metrics-Graphs_Tables/    # Auto-generated visualization graphs & MD tables
├── 🗂️ users_baseline_50/        # Raw Locust data for baseline testing
├── 🗂️ users_cpu_100/            # Raw CPU metrics for load distribution testing
└── 🗂️ users_fault_200/          # Raw Locust data for HA/recovery testing
```

---

## 🚀 Getting Started

To independently generate the graphs and data tables from the raw Locust CSV logs:

### 1. Install Dependencies
Ensure you have Python installed, then install the required data science libraries:
```powershell
py -m pip install pandas matplotlib numpy
```

### 2. Run the Analysis Engine
Execute the Python script to parse the raw data and generate the visualizations:
```powershell
py analyze_results.py
```

### 3. Review the Output
The script will automatically generate:
* **8 High-Resolution Graphs** (`.png`) detailing latency distributions, scalability limits, and CPU usage.
* **1 Markdown Table** (`final_metrics_table.md`) containing the mathematically calculated summaries.

---

<p align="center">
  Built for Advanced Cloud Computing & Systems Integration
</p>
