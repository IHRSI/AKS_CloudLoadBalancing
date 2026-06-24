# Load Balancing Performance Metrics

This table summarizes the core metrics extracted across all tests. For the Coefficient of Variation (CV %), a **lower number means better/more even distribution**.

| Metric | Round Robin | Least Connections | IP Hashing |
|---|---|---|---|
| **Avg Latency (ms)** | 89.8 | 86.9 | 87.3 |
| **P95 Latency (ms)** | 95.0 | 94.0 | 93.0 |
| **P99 Latency (ms)** | 170.0 | 120.0 | 110.0 |
| **Throughput (RPS)** | 22.3 | 22.2 | 22.2 |
| **Error Rate (%)** | 0.00% | 0.00% | 0.00% |
| **Recovery Time (ms spike)** | 5111 | 5111 | 504 |
| **CPU Evenness (CV %)** | 0.1% | 10.8% | 95.5% |
