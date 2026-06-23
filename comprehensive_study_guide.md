# Comprehensive Study Guide: Cloud Load Balancing on Kubernetes

## 1. System Architecture & Core Components

### 1.1 Azure Kubernetes Service (AKS)
- **Concept:** A managed container orchestration service based on Kubernetes. It simplifies the deployment, management, and scaling of containerized applications.
- **Analogy:** Think of AKS as an automated factory manager. You tell the manager, "I need 2 workers (pods) running this machine (container)," and the manager automatically hires them, monitors their health, and automatically replaces them if they fall sick.
- **Project Context:** A 2-node cluster was deployed using `Standard_D2s_v4` VMs (4 vCPU, 16GB RAM total).
- **Nodes vs. Pods:** Nodes are the underlying Virtual Machines (VMs) — the factory floor. Pods are the smallest deployable computing units in Kubernetes, encapsulating the actual application containers — the workers on the floor.

### 1.2 The Application Layer
- **Container Image:** `mendhak/http-https-echo`
- **Purpose:** A lightweight web server that echoes back information about the HTTP request, specifically the `hostname` (which corresponds to the Pod name). This allows precise tracking of which Pod handled a specific request.
- **Resource Limits:** CPU and Memory constraints (`requests` and `limits`) are defined to prevent a single pod from monopolizing node resources, simulating real-world application boundaries and forcing the load balancer to work under constraints.

### 1.3 Networking & Services
- **ClusterIP Service:** The default Kubernetes service type. It exposes the application on a cluster-internal IP, acting as a baseline internal load balancer across the deployment's pods.
- **NGINX Ingress Controller:** A specialized, high-performance load balancer (built on NGINX) that acts as the "front gate" to the cluster. It receives a public External IP from an Azure Load Balancer and routes external HTTP traffic to internal ClusterIP services based on explicitly defined routing rules.

---

## 2. Load Balancing Algorithms Explored

The core of this study evaluates three distinct routing strategies configured at the Ingress layer.

### 2.1 Round Robin (Default)
- **How it works:** Distributes incoming requests sequentially across all available backend pods (e.g., Pod A → Pod B → Pod A → Pod B).
- **Analogy:** Like dealing a deck of cards to players sitting in a circle. Everyone gets one card in turn, regardless of how many cards they already have.
- **Ideal Use Case:** When all pods have identical processing power and requests require roughly the same amount of time/resources to process (e.g., serving static web assets).
- **Project Observation:** Displayed perfectly even CPU distribution across pods during the 100-user load test.
- **Ingress Configuration:** This is the default behavior when no specific algorithm annotation is provided.

### 2.2 Least Connections (Using EWMA)
- **How it works (EWMA vs Raw Least Connections):** Instead of using a raw "Least Connections" algorithm, we configured NGINX to use **EWMA (Exponentially Weighted Moving Average)**. Raw Least Connections blindly counts open network connections, which is flawed because 10 quick requests might finish faster than 2 slow database queries. EWMA solves this by constantly tracking and mathematically averaging the *actual response times* of each pod. It intelligently routes traffic to the pod that is currently responding the fastest.
- **Analogy:** Choosing a checkout lane at the grocery store. You don't just count the number of people in line (Raw Least Connections). You look at how full their carts are (Response Time/EWMA). You join the line that is moving the fastest.
- **Ideal Use Case:** When requests have highly variable processing times (e.g., mixing quick homepage loads with heavy database queries). It prevents "pile-ups" on a single pod.
- **Project Observation:** Maintained balanced CPU distribution even when Locust "Heavy Requests" simulated artificial processing delays.
- **Ingress Configuration:**
  ```yaml
  annotations:
    nginx.ingress.kubernetes.io/load-balance: "ewma"
  ```

### 2.3 IP Hashing
- **How it works:** Computes a mathematical hash based on the client's IP address to determine which pod receives the request. The same client IP will *always* reach the exact same pod.
- **Analogy:** A bouncer at a club who recognizes your face and always escorts you to the exact same VIP room every time you visit.
- **Ideal Use Case:** "Sticky sessions" where a user's state (e.g., a shopping cart or login session) is stored locally in the pod's memory rather than a shared database like Redis.
- **Project Observation:** During testing from a single local machine, **one pod received 100% of the traffic** while the other sat idle. This perfectly demonstrated the severe limitation of IP Hashing when traffic originates from a single proxy, NAT gateway, or corporate firewall.
- **Ingress Configuration:**
  ```yaml
  annotations:
    nginx.ingress.kubernetes.io/upstream-hash-by: "$remote_addr"
  ```
- **Crucial Infrastructure Detail (SNAT):** Source Network Address Translation (SNAT) by the external Azure Load Balancer masks the true client IP by default.
  - *Analogy:* Imagine calling a company extension through a receptionist. The worker only sees the receptionist's internal phone number, not your original cell phone number.
  - *Fix:* To make IP Hashing work correctly, the NGINX controller must be patched with `externalTrafficPolicy: Local` to bypass the receptionist and preserve the original incoming client IP.

---

## 3. Performance Metrics & Load Testing (Locust)

### 3.1 Locust Load Testing Framework
Locust is an open-source, Python-based load testing tool. It allows developers to define user behavior in code and simulate thousands of concurrent users in a distributed fashion.

**Key Locustfile Segment:**
```python
class NormalUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def light_request(self):
        self.client.get("/", name="Light Request")

    @task(1)
    def heavy_request(self):
        self.client.get("/?heavy=true", name="Heavy Request")
        time.sleep(0.5)
```
- **Task Weighting (`@task(3)` vs `@task(1)`):** This simulates realistic, asymmetric traffic patterns where simple requests are 3 times more frequent than heavy, processing-intensive requests. The `time.sleep(0.5)` simulates server-side processing delay.

### 3.2 Key Metrics Evaluated
1. **Latency (Average Response Time in ms):** The time taken for the server to process the request and respond. Crucial for determining User Experience (UX).
2. **Throughput (Requests/sec):** The volume of traffic the system can handle simultaneously. Crucial for evaluating scalability and saturation points.
3. **Resource Utilization (CPU Millicores):** Monitored via `kubectl top pods`. Proves whether the load balancing algorithm is actually distributing the computational burden fairly.

---

## 4. High Availability & Fault Tolerance

### 4.1 The Concept of High Availability (HA)
HA ensures an application remains accessible even if underlying hardware or software fails. In Kubernetes, this is achieved via Deployments managing `replicas` ensuring a desired state is always maintained.

### 4.2 The Fault Tolerance Experiment (200 Users)
- **Scenario:** A massive load (200 users) is applied. At exactly 2 minutes, a pod is intentionally deleted (`kubectl delete pod <name>`) simulating a severe node crash.
- **Kubernetes Behavior:** The ReplicaSet immediately detects the desired state (2 pods) mismatches the actual state (1 pod) and begins spinning up a replacement pod.
- **NGINX Ingress Behavior:** NGINX detects the dead backend pod and instantly reroutes all incoming traffic to the surviving pod.
- **Observed Metrics:**
  - **Failure Count:** 0. (The architecture successfully achieved 100% availability).
  - **Latency Spike:** The system incurs a massive temporary latency spike (the "Recovery Window", often hitting 4,000ms - 5,000ms). This represents the penalty incurred while traffic shifts and the sole surviving pod handles double the load until the new pod initializes.

---

## 5. Data Analysis Automation (Python/Pandas)

To objectively evaluate the algorithms, Python (Pandas/Matplotlib) was used to parse Locust CSV outputs and Kubernetes text logs.

### 5.1 Data Cleaning & The "Data Slice Trick"
When analyzing system scalability (comparing Latency and Throughput across 50 vs 100 vs 200 users), taking the raw average of the entire 5-minute 200-user test is fundamentally flawed because it includes the chaotic 5-second recovery window from the intentionally killed pod.

**The Implementation Solution:**
```python
# Calculate relative time from the start of the test in seconds
df_agg['Relative Time'] = df_agg['Timestamp'] - df_agg['Timestamp'].iloc[0]

# Only calculate averages for pure data collected BEFORE the 120-second kill event
clean_data = df_agg[df_agg['Relative Time'] < 110]
average_latency = clean_data['Total Average Response Time'].mean()
```
This data-slicing logic guarantees an "apples-to-apples" scalability comparison between fully warmed-up, perfectly healthy clusters across all three user tiers.

---

## 6. Master Metrics Table & Data Breakdown

This table summarizes the core metrics mathematically extracted across all load tests.

| Metric | Round Robin | Least Connections | IP Hashing |
|---|---|---|---|
| **Avg Latency (ms)** | 89.8 | 86.9 | 87.3 |
| **P95 Latency (ms)** | 95.0 | 94.0 | 93.0 |
| **P99 Latency (ms)** | 170.0 | 120.0 | 110.0 |
| **Throughput (RPS)** | 22.3 | 22.2 | 22.2 |
| **Error Rate (%)** | 0.00% | 0.00% | 0.00% |
| **Recovery Time (ms spike)** | 5111 | 5111 | 504 |
| **CPU Evenness (CV %)** | 0.1% | 10.8% | 95.5% |

### What these numbers actually mean:
1. **Average Latency vs. Percentiles (P95/P99):** Notice how the *Average Latency* is basically identical across all algorithms (~87-89ms). If you stopped there, you'd think they perform identically. However, looking at the **P99 Latency** (the worst 1% of requests), Round Robin spikes to 170ms, while Least Connections and IP Hashing remain around 110-120ms. This proves that Round Robin occasionally dumps heavy traffic onto a busy pod, ruining the experience for unlucky users.
2. **CPU Evenness (Coefficient of Variation):** CV% measures statistical variance. A lower number means the load was distributed perfectly evenly. 
   - **Round Robin (0.1%):** Mathematically perfect, because it blindly deals cards one by one.
   - **Least Connections (10.8%):** Very balanced, but inherently slightly varied because it constantly adjusts routing based on live traffic.
   - **IP Hashing (95.5%):** Terrible distribution in our test. Because all requests came from a single computer (one IP), the hash routed *everything* to a single pod, leaving the other pod completely idle.
3. **Recovery Time (Fault Tolerance):** When the pod was violently deleted during the 200-user test, the surviving pod was instantly overwhelmed, causing a massive 5-second (5111ms) latency spike for Round Robin and Least Connections until Kubernetes spun up a replacement.

---

## 7. Final Comparative Summary

| Algorithm | Distribution Fairness | Latency Profile | Best Used For | Architectural Drawbacks |
|---|---|---|---|---|
| **Round Robin** | Excellent (if requests are uniform) | Consistent baseline | Standard microservices, identical stateless nodes. | Can overwhelm a pod if it randomly receives sequential "heavy" requests. |
| **EWMA (Least Conn)** | Excellent (adapts dynamically to varying load) | Highly optimized under stress | APIs with highly variable processing times, distinct heavy/light tasks. | Slight computational overhead in calculating moving averages. |
| **IP Hash** | Poor (from single proxy) | Highly variable | Stateful legacy applications requiring sticky sessions (e.g., caching, auth). | Terrible load distribution if many users are behind a single corporate NAT/VPN. |

---

## 8. Key Takeaways & Engineering Principles

1. **Algorithm Selection is Context-Dependent:** There is no universal "best" algorithm. Round Robin is great for static content, EWMA is superior for complex APIs, and IP Hashing is a necessary evil for stateful systems.
2. **Averages Hide Spikes:** When testing fault tolerance, evaluating the `Average Response Time` is deceptive. You must analyze the `Max Response Time` or high percentiles (`p99`) to expose the true cost of a system failure.
3. **Infrastructure as Code (IaC):** Defining the entire routing layer, deployments, and services via Kubernetes YAML allows for rapid, reproducible testing of complex network topologies.
4. **Resiliency over Perfection:** Modern cloud systems assume failure is inevitable. The goal is not to prevent pods from dying, but to build load balancing topologies that route around the failure so quickly that the end-user experiences zero dropped requests.

---

## 9. Interview Preparation: Terminology Dictionary

This section breaks down the foundational buzzwords used throughout this project into easy-to-digest explanations for technical discussions.

### Cloud Computing & Azure
- **Cloud Computing:** Renting servers, storage, and databases over the internet instead of buying and maintaining physical hardware in a server room.
- **Azure:** Microsoft's cloud computing platform (a primary competitor to AWS and Google Cloud).
- **Virtual Machine (VM):** A digital version of a physical computer. It runs its own operating system (like Linux or Windows) completely isolated from other VMs on the same physical server.
- **Resource Group:** In Azure, a logical "folder" used to group related resources (like VMs, networks, and IP addresses) so they can be managed or deleted together.

### Advanced Metrics & Statistics
- **P95 / P99 Latency (Percentiles):** Average latency can hide massive, temporary spikes. P99 Latency tells you the exact response time experienced by the slowest 1% of your users. Cloud SLAs (Service Level Agreements) are almost entirely based on P99, not averages.
- **Throughput (RPS):** Requests Per Second. A measure of sheer volume—how much traffic the system is chewing through at any given moment.
- **Coefficient of Variation (CV %):** A statistical measurement used to prove distribution evenness. It represents the ratio of the standard deviation to the mean. A lower CV% (like 0.1%) proves that all pods are working exactly as hard as each other.
- **Error Rate:** The percentage of HTTP requests that resulted in a failure (like a 500 Internal Server Error) due to the system being overwhelmed or crashing.

### Kubernetes (K8s) & AKS
- **Container:** A standardized, lightweight, standalone package of software that includes everything needed to run an application (code, runtime, system tools, libraries). Unlike VMs, containers share the host's operating system, making them much faster and lighter.
- **Kubernetes (K8s):** An open-source system originally designed by Google for automating the deployment, scaling, and management of containerized applications. It acts as the "operating system for the cloud."
- **AKS (Azure Kubernetes Service):** A managed Kubernetes service provided by Azure. Microsoft handles the complex "control plane" (the brain of Kubernetes), while you just manage the "worker nodes" (the muscles).
- **Node:** A physical or virtual machine that runs the Kubernetes agent and actually executes the containers.
- **Pod:** The smallest deployable unit in Kubernetes. A pod usually contains one container (like our web server). You don't scale containers directly; you scale pods.
- **Deployment:** A Kubernetes object that manages the creation and scaling of Pods. You tell it "I want 2 copies of this Pod," and it ensures exactly 2 are always running.
- **Service:** An abstraction that gives a reliable, unchanging IP address to a group of Pods. Since Pods die and get replaced constantly (changing their IPs), the Service acts as a stable middleman.
- **Ingress:** A set of routing rules that manage external access to the Services in a cluster, typically HTTP/HTTPS.
- **Load Balancer:** A device or software that distributes network traffic across multiple servers to ensure no single server becomes overwhelmed.

### Python Data Science Stack
- **Pandas:** A powerful Python library used for data manipulation and analysis. It introduces "DataFrames" (essentially highly programmable Excel spreadsheets) that allow you to easily filter, group, and calculate statistics on massive CSV datasets.
- **Matplotlib:** The foundational plotting library in Python. It is used to generate the bar charts and line graphs from the data processed by Pandas.
- **NumPy:** A library adding support for large, multi-dimensional arrays and matrices, along with high-level mathematical functions. In our script, it was used to perfectly align the X-axis positions of the multi-bar charts (`np.arange`).
