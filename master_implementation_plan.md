# Master Execution Guide: Comparative Study of Cloud Load Balancing Techniques Using Kubernetes on Azure AKS

## Project Summary

**Problem Statement:** Implement and evaluate Round Robin, Least Connections, and IP Hashing load balancing strategies in a Kubernetes cluster on Azure, measuring throughput, latency, and fault tolerance at varying user loads (50, 100, 200).

**Your Setup:**
- **Nodes:** 2 × Standard_D2s_v4 (2 vCPU, 8 GB RAM each → **total: 4 vCPU, 16 GB RAM**)
- **Cluster Name:** `myAKSCluster`
- **Resource Group:** `LoadBalancingResearch`
- **Working Directory:** `c:\_Work_\Cloud_Compute_SI\Execution` (all YAML files, scripts, and results go here)

---

## ⏱️ Time Estimate

| Phase | What | Time |
|---|---|---|
| Phase 0 | Azure setup + AKS cluster creation | **20–30 min** |
| Phase 1 | Deploy app + service | **5 min** |
| Phase 2 | Install NGINX Ingress | **10 min** |
| Phase 3 | Create & test 3 Ingress configs | **15 min** |
| Phase 4 | Load & Resource testing (50 & 100 users) | **25 min** |
| Phase 5 | Fault tolerance tests (200 users) | **40 min** |
| Phase 6 | Monitoring & distribution checks | **10 min** |
| Phase 7 | Data analysis & charts | **20 min** |
| Phase 8 | Cleanup | **5 min** |
| | **Total hands-on time** | **~2.5 to 4 hours** |

> [!TIP]
> Most of the waiting is during cluster creation (Phase 0) and load tests (Phase 4-5). During those waits you can prep the next phase's files.

---

## About the Working Directory

> [!NOTE]
> **Yes, work entirely in `c:\_Work_\Cloud_Compute_SI\Execution`.** This is ideal because:
> - All your YAML files, Python scripts, and CSV results will be in one place.
> - Kubernetes reads these files from your local machine and sends them to the cluster, so the folder location doesn't strictly matter to Azure.

---

## Phase 0: Azure Setup From Scratch (~20-30 min)

### What this phase does (Layman explanation)
You're renting servers from Microsoft Azure. First you need to log in to Azure, create a "folder" (Resource Group) to keep everything organized, and then ask Azure to create a Kubernetes cluster (a set of 2 virtual machines that work together).

---

### Step 1: Log in to Azure CLI

Open PowerShell in the Execution folder and run:

```powershell
az login
```

Verify you're on the student subscription:
```powershell
az account show --query "{Name:name, Credits:id}" -o table
```

---

### Step 2: Create the Resource Group

```powershell
az group create --name LoadBalancingResearch --location centralindia
```

> [!NOTE]
> **Why `centralindia`?** It's the closest Azure region to you (based on your timezone IST). This gives you the lowest latency during tests. You can use `eastus` instead if you prefer — it often has better availability for student subscriptions.
>
> **Check which regions have your VM size available:**
> ```powershell
> az vm list-skus --size Standard_D2s_v4 --query "[].{Location:locationInfo[0].location}" -o table
> ```

---

### Step 3: Create the AKS Cluster (2 Nodes)

**Readable Multi-line format** (make sure there are no spaces after each backtick `):
```powershell
az aks create `
  --resource-group LoadBalancingResearch `
  --name myAKSCluster `
  --node-count 2 `
  --node-vm-size Standard_D2s_v4 `
  --generate-ssh-keys `
  --tier free `
  --network-plugin kubenet
```

**Single-line format** (safer for exact copy-paste):
```powershell
az aks create --resource-group LoadBalancingResearch --name myAKSCluster --node-count 2 --node-vm-size Standard_D2s_v4 --generate-ssh-keys --tier free --network-plugin kubenet
```

**Command Breakdown:**
- `--node-count 2` → Creates 2 virtual machines (your 2 worker nodes).
- `--node-vm-size Standard_D2s_v4` → Each VM gets 2 vCPU + 8 GB RAM.
- `--generate-ssh-keys` → Creates security keys automatically so you can connect.
- `--tier free` → No management fee (saves your $100 credits).
- `--network-plugin kubenet` → Simple networking model, perfect for this research.

> [!IMPORTANT]
> **This takes 5–10 minutes.** Don't close the terminal. While it runs, you can open a new terminal and prepare the YAML files for Phase 1.

---

### Step 4: Connect kubectl to Your Cluster

```powershell
az aks get-credentials --resource-group LoadBalancingResearch --name myAKSCluster
```

Verify connection:
```powershell
kubectl get nodes
```

**Expected output:**
```
NAME                                STATUS   ROLES   AGE   VERSION
aks-nodepool1-12345678-vmss000000   Ready    agent   5m    v1.29.x
aks-nodepool1-12345678-vmss000001   Ready    agent   5m    v1.29.x
```
You should see **2 nodes**, both with status **Ready**. ✅

---

## Phase 1: Deploy the Application (~5 min)

### What this phase does (Layman explanation)
You're placing 2 copies of a small web server onto your 2 nodes. Each copy (called a "pod") will respond to web requests and tell you its name, so you can see exactly which pod handled which request.

---

### Step 5: Create and Apply the Deployment

**Create `deployment.yaml`:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-server
  labels:
    app: web-server
spec:
  replicas: 2                           # 2 pods = 1 per node
  selector:
    matchLabels:
      app: web-server                   # Links deployment to the pods
  template:
    metadata:
      labels:
        app: web-server
    spec:
      containers:
      - name: web-server
        image: mendhak/http-https-echo  # Returns pod name in response
        ports:
        - containerPort: 8080
        resources:
          requests:
            cpu: "100m"                 # Reserves 0.1 CPU core
            memory: "64Mi"              # Reserves 64 MB RAM
          limits:
            cpu: "250m"                 # Max 0.25 CPU core
            memory: "128Mi"             # Max 128 MB RAM
        env:
        - name: HTTP_PORT
          value: "8080"
```

Apply it:
```powershell
kubectl apply -f deployment.yaml
```

Verify pods are running:
```powershell
kubectl get pods -o wide
```

---

### Step 6: Create and Apply the Service

**Create `service.yaml`:**
```yaml
apiVersion: v1
kind: Service
metadata:
  name: web-service
spec:
  selector:
    app: web-server                     # Routes traffic to pods with this label
  ports:
  - protocol: TCP
    port: 80                            # Port exposed by the service
    targetPort: 8080                    # Port the container listens on
  type: ClusterIP                       # Internal cluster IP (default)
```

Apply it:
```powershell
kubectl apply -f service.yaml
```

---

## Phase 2: Install the NGINX Ingress Controller (~10 min)

### What this phase does (Layman explanation)
Your pods are running but hidden inside the cluster. The NGINX Ingress Controller is a **front gate** that gets a public IP address from Azure and forwards internet traffic to your pods. This is where the load balancing algorithms actually operate.

---

### Step 7: Install Helm

```powershell
winget install Helm.Helm
```

---

### Step 8: Install NGINX Ingress Controller

```powershell
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```

**Readable Multi-line format:**
```powershell
helm install ingress-nginx ingress-nginx/ingress-nginx `
  --namespace ingress-nginx `
  --create-namespace `
  --set controller.replicaCount=1 `
  --set controller.resources.requests.cpu=100m `
  --set controller.resources.requests.memory=128Mi `
  --set controller.resources.limits.cpu=250m `
  --set controller.resources.limits.memory=256Mi
```

**Single-line format:**
```powershell
helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --set controller.replicaCount=1 --set controller.resources.requests.cpu=100m --set controller.resources.requests.memory=128Mi --set controller.resources.limits.cpu=250m --set controller.resources.limits.memory=256Mi
```

**Command Breakdown:**
- `--namespace ingress-nginx` → Creates a dedicated space for the controller.
- `--create-namespace` → Automatically creates the namespace if it doesn't exist.
- `--set controller.replicaCount=1` → Deploys exactly 1 NGINX pod to act as the single entry point.
- `--set controller.resources...` → Sets CPU and Memory limits so NGINX doesn't crash the nodes.

**Wait for the External IP (takes 2–5 min):**
```powershell
kubectl get svc -n ingress-nginx --watch
```
When `EXTERNAL-IP` changes from `<pending>` to a real IP, press **Ctrl+C** to stop watching.

**Save the IP — you'll use it everywhere:**
```powershell
kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

> [!CAUTION]
> **Cost:** The NGINX Ingress creates an Azure Load Balancer. When you're done for the day, stop your cluster: `az aks stop --resource-group LoadBalancingResearch --name myAKSCluster`

---

## Phase 3: Configure the Load Balancing Algorithms (~15 min)

### What this phase does (Layman explanation)
You'll create 3 different "rulebook" files (Ingress YAMLs). Each one tells the front gate (NGINX) a different strategy for choosing which pod handles a request:
- **Round Robin** = take turns (Pod A → Pod B → Pod A → Pod B...)
- **Least Connections** = send to whichever pod is less busy right now
- **IP Hashing** = always send the same person to the same pod

---

### Step 9: Round Robin (Default)

**`ingress-round-robin.yaml`:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /    # Removes sub-paths before sending to pods
spec:
  ingressClassName: nginx                            # Binds this rule to our NGINX controller
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service                        # The service we created in Phase 1
            port:
              number: 80
```

---

### Step 10: Least Connections

**`ingress-least-conn.yaml`:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/load-balance: "ewma"  # Forces EWMA (Exponentially Weighted Moving Average) algorithm
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

---

### Step 11: IP Hashing

**`ingress-ip-hash.yaml`:**
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: web-ingress
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/upstream-hash-by: "$remote_addr"  # Forces IP Hashing algorithm
spec:
  ingressClassName: nginx
  rules:
  - http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-service
            port:
              number: 80
```

> [!NOTE]
> **SNAT Issue:** Azure Load Balancers mask client IPs by default. To make IP Hashing work correctly, you must patch the NGINX controller to preserve client IPs using:
> `kubectl patch svc ingress-nginx-controller -n ingress-nginx -p '{"spec":{"externalTrafficPolicy":"Local"}}'`

---

## Phase 4: Load & Resource Testing (~25 min)

### What this phase does (Layman explanation)
You're going to blast your cluster with fake traffic — simulating 50 and 100 people visiting at the same time — and recording how fast the server responds. You do this for each algorithm to compare the numbers.

---

### Step 12: Prepare Locust

```powershell
py -m pip install locust
```

**Create `locustfile.py`:**
```python
from locust import HttpUser, task, between
import time

class NormalUser(HttpUser):
    """Simulates users making a mix of quick and slow requests."""
    wait_time = between(1, 3)

    @task(3)
    def light_request(self):
        """Quick page load."""
        self.client.get("/", name="Light Request")

    @task(1)
    def heavy_request(self):
        """Slower request — simulates processing."""
        self.client.get("/?heavy=true", name="Heavy Request")
        time.sleep(0.5)
```

---

### Step 13: Phase 4.1 - Baseline Latency Testing (50 Users)
*Save outputs in folder: `users_baseline_50`*

**Command Breakdown:**
- `--host` → The NGINX External IP.
- `--users 50` → Total concurrent users.
- `--spawn-rate 5` → Adds 5 users per second until it hits 50.
- `--run-time 5m` → Runs the test for exactly 5 minutes.
- `--csv` → Saves the metrics to CSV files.

**Round Robin:**
```powershell
kubectl apply -f ingress-round-robin.yaml
```

*(Optional) Run Step 16 (Phase 6) to visibly verify the request distribution before proceeding with the Locust test.*

```powershell
# Single-line:
py -m locust -f locustfile.py --host=http://<EXTERNAL-IP> --headless --users 50 --spawn-rate 5 --run-time 5m --csv=results_round_robin_50

# Multi-line:
py -m locust -f locustfile.py `
  --host=http://<EXTERNAL-IP> `
  --headless `
  --users 50 `
  --spawn-rate 5 `
  --run-time 5m `
  --csv=results_round_robin_50
```

*(Repeat logic for `ingress-least-conn.yaml` and `ingress-ip-hash.yaml`, changing the `--csv` parameter accordingly).*

---

### Step 14: Phase 4.2 - Resource Distribution Testing (100 Users)
*Save outputs in folder: `users_cpu_100`*

For this phase, you will open **two terminals**. Terminal 1 logs the CPU, Terminal 2 runs Locust.

**Round Robin (100 Users):**

1. Apply Ingress:
   ```powershell
   kubectl apply -f ingress-round-robin.yaml
   ```

2. Start CPU Logger (**Terminal 1**):
   *This PowerShell loop checks pod CPU usage every 5 seconds and appends it to a text file.*
   ```powershell
   while ($true) { Get-Date >> cpu_rr_100.txt; kubectl top pods >> cpu_rr_100.txt; Start-Sleep -Seconds 5 }
   ```

3. Start Load Test (**Terminal 2**):
   **Single-line:**
   ```powershell
   py -m locust -f locustfile.py --host=http://<EXTERNAL-IP> --headless --users 100 --spawn-rate 10 --run-time 5m --csv=results_round_robin_100
   ```
   **Multi-line:**
   ```powershell
   py -m locust -f locustfile.py `
     --host=http://<EXTERNAL-IP> `
     --headless `
     --users 100 `
     --spawn-rate 10 `
     --run-time 5m `
     --csv=results_round_robin_100
   ```

4. When Locust finishes (after 5m), go to Terminal 1 and press `Ctrl+C` to stop the CPU logger.

*(Repeat for Least Connections and IP Hash, changing file names to `cpu_lc_100.txt` and `cpu_ih_100.txt`).*

---

## Phase 5: Fault Tolerance Stress Test (200 Users)

### What this phase does (Layman explanation)
You kill a pod while heavy traffic (200 users) is flowing to measure how long the system takes to recover. With 2 nodes, when you kill a pod, Kubernetes replaces it — during that gap, all traffic funnels to the surviving pod. You compare how each algorithm handles this massive recovery spike.

*Save outputs in folder: `users_fault_200`*

**Round Robin (200 Users):**

1. Apply Ingress:
   ```powershell
   kubectl apply -f ingress-round-robin.yaml
   ```

2. Start Stress Test (**Terminal 1**):
   **Single-line:**
   ```powershell
   py -m locust -f locustfile.py --host=http://<EXTERNAL-IP> --headless --users 200 --spawn-rate 20 --run-time 5m --csv=fault_round_robin_200
   ```
   **Multi-line:**
   ```powershell
   py -m locust -f locustfile.py `
     --host=http://<EXTERNAL-IP> `
     --headless `
     --users 200 `
     --spawn-rate 20 `
     --run-time 5m `
     --csv=fault_round_robin_200
   ```

3. Kill a Pod (**Terminal 2 - Exactly 2 minutes after Locust starts**):
   ```powershell
   kubectl get pods
   kubectl delete pod <type-your-pod-name-here>
   ```

> [!NOTE]
> **Locust's `_stats_history.csv`** logs the exact timestamp of every request. You do not need to manually record the time. Our Python script scans this history file to find exactly when the latency spiked due to the deleted pod, and calculates the recovery window perfectly.

*(Repeat for Least Connections and IP Hash).*

---

## Phase 6: Monitoring & Distribution Verification (~10 min)

### What this phase does (Layman explanation)
This is an interactive step to prove your Load Balancer algorithms are actually working. Instead of sending hundreds of fake requests through Locust, you will manually send 20 requests and visibly watch which pod handles each one on your screen.

### Step 16: Verify Request Distribution

**Run this quick check after applying each algorithm's ingress:**

```powershell
# PowerShell version — sends 20 requests and shows which pod handled each
1..20 | ForEach-Object { (Invoke-WebRequest -Uri "http://<EXTERNAL-IP>/" -UseBasicParsing).Content | ConvertFrom-Json | Select-Object -ExpandProperty os | Select-Object -ExpandProperty hostname }
```

> [!NOTE]
> For Round Robin, you will see responses neatly alternating. For IP Hashing, you will see the exact same pod name printed 20 times!

---

## Phase 7: Data Analysis & Charts

### What this phase does
This Python script parses all the CSV files and CPU logs you generated across the 50, 100, and 200 user tests. It calculates averages, isolates heavy vs light requests, tracks CPU scaling, and cleanly measures the exact latency spike during the Fault Tolerance pod deletion. It generates 8 highly professional graphs for your paper.

1. **Install Dependencies:**
   ```powershell
   py -m pip install pandas matplotlib numpy
   ```

2. **Create `analyze_results.py`:**
   *(Save the following Python code directly to `analyze_results.py`)*

```python
import pandas as pd # Pandas is used for parsing CSV files and manipulating data tables
import matplotlib.pyplot as plt # Matplotlib is used for drawing the actual graphs
import os # OS is used for checking if files exist in the file system
import re # Regex is used for extracting pod names from the raw text logs
import numpy as np # Numpy is used for calculating mathematical spacing for the bar charts

# Set up the overall visual style of the generated graphs
plt.style.use('ggplot')

# Folder paths where the Locust CSVs and CPU logs are stored
DIR_50 = "users_baseline_50"
DIR_100 = "users_cpu_100"
DIR_200 = "users_fault_200"

def analyze_baseline_50():
    """Reads the 50-user CSV files and plots basic Average Latency and Throughput bar charts."""
    print("=== Analyzing Phase 4.1: Baseline Latency & Throughput (50 Users) ===")
    
    files = {
        "Round Robin": os.path.join(DIR_50, "results_round_robin_50_stats.csv"),
        "Least Conn": os.path.join(DIR_50, "results_least_conn_50_stats.csv"),
        "IP Hash": os.path.join(DIR_50, "results_ip_hash_50_stats.csv")
    }
    
    algos = []
    avg_latencies = []
    throughputs = []
    
    for algo, path in files.items():
        if not os.path.exists(path):
            continue
            
        # Load the CSV file into a Pandas DataFrame (a programmable spreadsheet)
        df = pd.read_csv(path)
        # Extract the single row that contains the 'Aggregated' (total) statistics
        agg_row = df[df['Name'] == 'Aggregated']
        if not agg_row.empty:
            # Extract the raw numbers from the specific columns
            avg_latencies.append(agg_row['Average Response Time'].values[0])
            throughputs.append(agg_row['Requests/s'].values[0])
            algos.append(algo)

    if not algos: return

    # Plot 1: Average Latency Bar Chart
    plt.figure(figsize=(8, 5))
    plt.bar(algos, avg_latencies, color=['#3498db', '#e74c3c', '#2ecc71'])
    plt.title("Baseline Average Latency (50 Users)")
    plt.ylabel("Latency (ms)")
    # Add text labels on top of each bar
    for i, v in enumerate(avg_latencies):
        plt.text(i, v + 1, f"{v:.1f}", ha='center', fontweight='bold')
    plt.savefig("graph_1_baseline_latency.png")
    
    # Plot 2: Throughput Bar Chart
    plt.figure(figsize=(8, 5))
    plt.bar(algos, throughputs, color=['#3498db', '#e74c3c', '#2ecc71'])
    plt.title("Baseline Throughput (50 Users)")
    plt.ylabel("Requests per Second")
    for i, v in enumerate(throughputs):
        plt.text(i, v + 1, f"{v:.1f}", ha='center', fontweight='bold')
    plt.savefig("graph_2_baseline_throughput.png")


def analyze_endpoints_50():
    """Separates the latency of 'Light Requests' (homepage) from 'Heavy Requests' (processing)."""
    print("=== Analyzing Endpoint Specifics: Heavy vs Light Requests ===")
    files = {
        "Round Robin": os.path.join(DIR_50, "results_round_robin_50_stats.csv"),
        "Least Conn": os.path.join(DIR_50, "results_least_conn_50_stats.csv"),
        "IP Hash": os.path.join(DIR_50, "results_ip_hash_50_stats.csv")
    }
    
    algos = []
    light_latency = []
    heavy_latency = []
    
    for algo, path in files.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            # Filter the dataframe to only look at specific endpoints
            light = df[df['Name'] == 'Light Request']
            heavy = df[df['Name'] == 'Heavy Request']
            if not light.empty and not heavy.empty:
                algos.append(algo)
                light_latency.append(light['Average Response Time'].values[0])
                heavy_latency.append(heavy['Average Response Time'].values[0])
                
    if algos:
        # np.arange creates mathematical spacing [0, 1, 2] so we can place two bars side-by-side
        x = np.arange(len(algos))
        width = 0.35 # Width of the individual bars
        fig, ax = plt.subplots(figsize=(8, 5))
        # Shift the light bars slightly to the left, and heavy bars slightly to the right
        b1 = ax.bar(x - width/2, light_latency, width, label='Light Request', color='#2ecc71')
        b2 = ax.bar(x + width/2, heavy_latency, width, label='Heavy Request', color='#e74c3c')
        # Add numerical labels on top of the bars
        ax.bar_label(b1, fmt='%.1f')
        ax.bar_label(b2, fmt='%.1f')
        ax.set_ylabel('Average Latency (ms)')
        ax.set_title('Request Type Breakdown (50 Users)')
        ax.set_xticks(x)
        ax.set_xticklabels(algos)
        ax.legend()
        plt.savefig("graph_3_endpoint_breakdown.png")


def analyze_cpu_100():
    """Parses raw text logs from kubectl top to plot CPU usage over time for each pod."""
    print("=== Analyzing Phase 4.2: Resource Distribution (100 Users) ===")
    files = {
        "Round Robin": os.path.join(DIR_100, "cpu_rr_100.txt"),
        "Least Conn": os.path.join(DIR_100, "cpu_lc_100.txt"),
        "IP Hash": os.path.join(DIR_100, "cpu_ih_100.txt")
    }
    
    # Create 3 subplots side-by-side (one for each algorithm)
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    fig.suptitle("Resource Distribution (CPU Usage) - 100 Users", fontsize=16)
    
    for idx, (algo, path) in enumerate(files.items()):
        ax = axes[idx]
        if not os.path.exists(path): continue
            
        pod_data = {}
        # Read the raw text file (handling potential Powershell text encodings)
        with open(path, 'r', encoding='utf-16le', errors='ignore') as f:
            lines = f.readlines()
            if not lines or len(lines) < 2:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f2:
                    lines = f2.readlines()

        # Parse line by line to extract pod name and CPU millicores
        for line in lines:
            line = line.strip()
            if line.startswith("web-server-"):
                parts = re.split(r'\s+', line)
                if len(parts) >= 2:
                    pod_name = parts[0][-5:] # Extract just the unique 5-character hash of the pod name
                    cpu_str = parts[1]
                    cpu_val = int(cpu_str.replace('m', '')) # Remove 'm' to get a clean integer
                    if pod_name not in pod_data:
                        pod_data[pod_name] = []
                    pod_data[pod_name].append(cpu_val)
                    
        # Draw a line for each pod found in the logs
        for pod_name, cpu_values in pod_data.items():
            ax.plot(cpu_values, label=f"Pod {pod_name}")
            
        ax.set_title(f"{algo}")
        ax.set_xlabel("Time intervals (approx 5s)")
        if idx == 0:
            ax.set_ylabel("CPU Usage (millicores)")
        ax.legend()
        
    plt.tight_layout()
    plt.savefig("graph_4_resource_distribution.png")


def analyze_fault_200():
    """Reads the time-series history CSV to track exactly when latency spiked due to pod deletion."""
    print("=== Analyzing Phase 5: Fault Tolerance (200 Users) ===")
    files = {
        "Round Robin": os.path.join(DIR_200, "fault_round_robin_200_stats_history.csv"),
        "Least Conn": os.path.join(DIR_200, "fault_least_conn_200_stats_history.csv"),
        "IP Hash": os.path.join(DIR_200, "fault_ip_hash_200_stats_history.csv")
    }
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5), sharey=True)
    fig.suptitle("Fault Tolerance Recovery Window (Max Response Time Spike)", fontsize=16)
    
    for idx, (algo, path) in enumerate(files.items()):
        ax = axes[idx]
        if not os.path.exists(path): continue
            
        df = pd.read_csv(path)
        df_agg = df[df['Name'] == 'Aggregated'].copy()
        if df_agg.empty: df_agg = df.copy()
            
        # Convert Unix timestamp to a relative timeline starting at 0 seconds
        df_agg['Relative Time'] = df_agg['Timestamp'] - df_agg['Timestamp'].iloc[0]
        
        # Plot the massive spike in Maximum Response Time
        ax.plot(df_agg['Relative Time'], df_agg['Total Max Response Time'], color='#e74c3c')
        ax.set_title(algo)
        ax.set_xlabel("Test Duration (Seconds)")
        if idx == 0: ax.set_ylabel("Max Response Time (ms)")
            
        # Automatically find the absolute peak of the spike and label it
        max_spike = df_agg['Total Max Response Time'].max()
        ax.axhline(y=max_spike, color='r', linestyle='--', alpha=0.3)
        ax.text(10, max_spike + 100, f"Recovery Window Peak: {max_spike}ms", color='red')

    plt.tight_layout()
    plt.savefig("graph_5_fault_tolerance.png")

def analyze_scaling():
    """Compares metrics across 50, 100, and 200 users. Uses data slicing to remove the 200-user pod crash chaos."""
    print("=== Analyzing Scaling: 50 vs 100 vs 200 Users ===")
    algos = ["Round Robin", "Least Conn", "IP Hash"]
    user_counts = [50, 100, 200]
    
    latencies = {algo: [] for algo in algos}
    throughputs = {algo: [] for algo in algos}
    
    file_map = {
        "Round Robin": {
            50: os.path.join(DIR_50, "results_round_robin_50_stats.csv"),
            100: os.path.join(DIR_100, "results_round_robin_100_stats.csv"),
            200: os.path.join(DIR_200, "fault_round_robin_200_stats_history.csv")
        },
        "Least Conn": {
            50: os.path.join(DIR_50, "results_least_conn_50_stats.csv"),
            100: os.path.join(DIR_100, "results_least_conn_100_stats.csv"),
            200: os.path.join(DIR_200, "fault_least_conn_200_stats_history.csv")
        },
        "IP Hash": {
            50: os.path.join(DIR_50, "results_ip_hash_50_stats.csv"),
            100: os.path.join(DIR_100, "results_ip_hash_100_stats.csv"),
            200: os.path.join(DIR_200, "fault_ip_hash_200_stats_history.csv")
        }
    }
    
    has_data = False
    for algo in algos:
        for count in user_counts:
            path = file_map[algo][count]
            if os.path.exists(path):
                df = pd.read_csv(path)
                if count == 200:
                    df_agg = df[df['Name'] == 'Aggregated'].copy()
                    if df_agg.empty: df_agg = df.copy()
                    
                    df_agg['Relative Time'] = df_agg['Timestamp'] - df_agg['Timestamp'].iloc[0]
                    # DATA SLICE TRICK: Ignore data after 110s to calculate pure scalability without the crash penalty
                    clean_data = df_agg[df_agg['Relative Time'] < 110]
                    if not clean_data.empty:
                        latencies[algo].append(clean_data['Total Average Response Time'].mean())
                        throughputs[algo].append(clean_data['Requests/s'].mean())
                        has_data = True
                    else:
                        latencies[algo].append(0)
                        throughputs[algo].append(0)
                else:
                    agg_row = df[df['Name'] == 'Aggregated']
                    if not agg_row.empty:
                        latencies[algo].append(agg_row['Average Response Time'].values[0])
                        throughputs[algo].append(agg_row['Requests/s'].values[0])
                        has_data = True
                    else:
                        latencies[algo].append(0)
                        throughputs[algo].append(0)
            else:
                latencies[algo].append(0)
                throughputs[algo].append(0)
                
    if not has_data: return
        
    x = np.arange(len(user_counts))
    width = 0.25
    
    # Graph 6: Scaling Latency
    fig1, ax1 = plt.subplots(figsize=(10, 6))
    b1 = ax1.bar(x - width, latencies["Round Robin"], width, label='Round Robin', color='#3498db')
    b2 = ax1.bar(x, latencies["Least Conn"], width, label='Least Conn', color='#e74c3c')
    b3 = ax1.bar(x + width, latencies["IP Hash"], width, label='IP Hash', color='#2ecc71')
    ax1.bar_label(b1, fmt='%.1f')
    ax1.bar_label(b2, fmt='%.1f')
    ax1.bar_label(b3, fmt='%.1f')
    ax1.set_ylabel('Average Latency (ms)')
    ax1.set_title('Scaling Latency (50 vs 100 vs 200 Users)')
    ax1.set_xticks(x)
    ax1.set_xticklabels([f"{c} Users" for c in user_counts])
    ax1.legend()
    plt.savefig("graph_6_scaling_latency.png")

    # Graph 7: Scaling Throughput
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    b1 = ax2.bar(x - width, throughputs["Round Robin"], width, label='Round Robin', color='#3498db')
    b2 = ax2.bar(x, throughputs["Least Conn"], width, label='Least Conn', color='#e74c3c')
    b3 = ax2.bar(x + width, throughputs["IP Hash"], width, label='IP Hash', color='#2ecc71')
    ax2.bar_label(b1, fmt='%.1f')
    ax2.bar_label(b2, fmt='%.1f')
    ax2.bar_label(b3, fmt='%.1f')
    ax2.set_ylabel('Throughput (Requests/sec)')
    ax2.set_title('Scaling Throughput (50 vs 100 vs 200 Users)')
    ax2.set_xticks(x)
    ax2.set_xticklabels([f"{c} Users" for c in user_counts])
    ax2.legend()
    plt.savefig("graph_7_scaling_throughput.png")

def analyze_percentiles_50():
    """Plots the Average Latency vs 95th (P95) vs 99th (P99) Percentile Latencies side by side."""
    print("=== Analyzing Percentiles: Avg vs P95 vs P99 (50 Users) ===")
    files = {
        "Round Robin": os.path.join(DIR_50, "results_round_robin_50_stats.csv"),
        "Least Conn": os.path.join(DIR_50, "results_least_conn_50_stats.csv"),
        "IP Hash": os.path.join(DIR_50, "results_ip_hash_50_stats.csv")
    }
    
    algos = []
    avg_lat = []
    p95_lat = []
    p99_lat = []
    
    for algo, path in files.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            agg_row = df[df['Name'] == 'Aggregated']
            if not agg_row.empty:
                algos.append(algo)
                avg_lat.append(agg_row['Average Response Time'].values[0])
                # P95 and P99 reveal the worst-case scenario for the slowest 5% and 1% of users
                p95_lat.append(agg_row['95%'].values[0])
                p99_lat.append(agg_row['99%'].values[0])
                
    if not algos: return
    
    x = np.arange(len(algos))
    width = 0.25 # Make bars slightly thinner to fit 3 bars per group
    fig, ax = plt.subplots(figsize=(10, 6))
    
    b1 = ax.bar(x - width, avg_lat, width, label='Average Latency', color='#3498db')
    b2 = ax.bar(x, p95_lat, width, label='95th Percentile (P95)', color='#f1c40f')
    b3 = ax.bar(x + width, p99_lat, width, label='99th Percentile (P99)', color='#e74c3c')
    ax.bar_label(b1, fmt='%.1f')
    ax.bar_label(b2, fmt='%.1f')
    ax.bar_label(b3, fmt='%.1f')
    
    ax.set_ylabel('Latency (ms)')
    ax.set_title('Latency Percentiles Comparison (50 Users)')
    ax.set_xticks(x)
    ax.set_xticklabels(algos)
    ax.legend()
    plt.savefig("graph_8_latency_percentiles.png")

def generate_markdown_table():
    """Extracts all core metrics across the algorithms and generates a clean Markdown table."""
    print("=== Generating Combined Markdown Table ===")
    
    algos = ["Round Robin", "Least Conn", "IP Hash"]
    metrics = {
        "Avg Latency (ms)": {},
        "P95 Latency (ms)": {},
        "P99 Latency (ms)": {},
        "Throughput (RPS)": {},
        "Error Rate (%)": {},
        "Recovery Time (ms spike)": {},
        "CPU Evenness (CV %)": {}
    }
    
    # 1. Baseline (50 Users)
    files_50 = {
        "Round Robin": os.path.join(DIR_50, "results_round_robin_50_stats.csv"),
        "Least Conn": os.path.join(DIR_50, "results_least_conn_50_stats.csv"),
        "IP Hash": os.path.join(DIR_50, "results_ip_hash_50_stats.csv")
    }
    for algo, path in files_50.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            agg = df[df['Name'] == 'Aggregated']
            if not agg.empty:
                metrics["Avg Latency (ms)"][algo] = f"{agg['Average Response Time'].values[0]:.1f}"
                metrics["P95 Latency (ms)"][algo] = f"{agg['95%'].values[0]:.1f}"
                metrics["P99 Latency (ms)"][algo] = f"{agg['99%'].values[0]:.1f}"
                metrics["Throughput (RPS)"][algo] = f"{agg['Requests/s'].values[0]:.1f}"
                # Calculate Error Rate
                fails = agg['Failure Count'].values[0]
                reqs = agg['Request Count'].values[0]
                err_rate = (fails / reqs * 100) if reqs > 0 else 0
                metrics["Error Rate (%)"][algo] = f"{err_rate:.2f}%"
        else:
            for k in ["Avg Latency (ms)", "P95 Latency (ms)", "P99 Latency (ms)", "Throughput (RPS)", "Error Rate (%)"]:
                metrics[k][algo] = "N/A"

    # 2. Recovery Time (200 Users)
    files_200 = {
        "Round Robin": os.path.join(DIR_200, "fault_round_robin_200_stats_history.csv"),
        "Least Conn": os.path.join(DIR_200, "fault_least_conn_200_stats_history.csv"),
        "IP Hash": os.path.join(DIR_200, "fault_ip_hash_200_stats_history.csv")
    }
    for algo, path in files_200.items():
        if os.path.exists(path):
            df = pd.read_csv(path)
            df_agg = df[df['Name'] == 'Aggregated'].copy()
            if df_agg.empty: df_agg = df.copy()
            metrics["Recovery Time (ms spike)"][algo] = f"{df_agg['Total Max Response Time'].max():.0f}"
        else:
            metrics["Recovery Time (ms spike)"][algo] = "N/A"

    # 3. CPU Evenness (100 Users) - Coefficient of Variation
    files_100 = {
        "Round Robin": os.path.join(DIR_100, "cpu_rr_100.txt"),
        "Least Conn": os.path.join(DIR_100, "cpu_lc_100.txt"),
        "IP Hash": os.path.join(DIR_100, "cpu_ih_100.txt")
    }
    for algo, path in files_100.items():
        if os.path.exists(path):
            pod_data = {}
            with open(path, 'r', encoding='utf-16le', errors='ignore') as f:
                lines = f.readlines()
                if not lines or len(lines) < 2:
                    with open(path, 'r', encoding='utf-8', errors='ignore') as f2:
                        lines = f2.readlines()
            for line in lines:
                line = line.strip()
                if line.startswith("web-server-"):
                    parts = re.split(r'\s+', line)
                    if len(parts) >= 2:
                        pod_name = parts[0][-5:] 
                        cpu_val = int(parts[1].replace('m', ''))
                        if pod_name not in pod_data: pod_data[pod_name] = []
                        pod_data[pod_name].append(cpu_val)
            
            # Avg CPU per pod over time
            pod_avgs = [np.mean(vals) for vals in pod_data.values()] if pod_data else []
            if len(pod_avgs) > 1:
                mean_val = np.mean(pod_avgs)
                std_val = np.std(pod_avgs)
                cv = (std_val / mean_val * 100) if mean_val > 0 else 0
                metrics["CPU Evenness (CV %)"][algo] = f"{cv:.1f}%"
            else:
                metrics["CPU Evenness (CV %)"][algo] = "N/A"
        else:
            metrics["CPU Evenness (CV %)"][algo] = "N/A"

    # 4. Write Markdown
    md_content = "# Load Balancing Performance Metrics\n\n"
    md_content += "This table summarizes the core metrics extracted across all tests. For the Coefficient of Variation (CV %), a **lower number means better/more even distribution**.\n\n"
    md_content += "| Metric | Round Robin | Least Connections | IP Hashing |\n"
    md_content += "|---|---|---|---|\n"
    
    for metric_name, algo_dict in metrics.items():
        rr = algo_dict.get("Round Robin", "N/A")
        lc = algo_dict.get("Least Conn", "N/A")
        ih = algo_dict.get("IP Hash", "N/A")
        md_content += f"| **{metric_name}** | {rr} | {lc} | {ih} |\n"
        
    with open("final_metrics_table.md", "w") as f:
        f.write(md_content)
        
    print("Table generated successfully -> final_metrics_table.md")

if __name__ == "__main__":
    print("Starting Analysis script...\n")
    # Call all the individual plotting functions defined above
    analyze_baseline_50()
    analyze_endpoints_50()
    analyze_cpu_100()
    analyze_fault_200()
    analyze_scaling()
    analyze_percentiles_50()
    generate_markdown_table()
    print("Analysis Complete! 8 graphs and 1 table have been generated.")
```

3. **Run the Script:**
   ```powershell
   py analyze_results.py
   ```

---

## Phase 8: Cleanup — Save Your Credits!

To completely delete the cluster and halt all Azure billing permanently:

**Single-line command:**
```powershell
az group delete --name LoadBalancingResearch --yes --no-wait
```

**Command Breakdown:**
- `--yes` → Skips the confirmation prompt.
- `--no-wait` → Allows the command to return immediately so you don't have to keep your terminal open while Azure deletes it in the background (takes 5-10 mins).

---

## 📋 Quick Reference Summary

This is the exact sequence of terminal commands used across the entire lifecycle of the research project, stripped of explanations for rapid execution.

```powershell
# PHASE 0 — Setup
az login
az group create --name LoadBalancingResearch --location centralindia
az aks create --resource-group LoadBalancingResearch --name myAKSCluster --node-count 2 --node-vm-size Standard_D2s_v4 --generate-ssh-keys --tier free --network-plugin kubenet
az aks get-credentials --resource-group LoadBalancingResearch --name myAKSCluster

# PHASE 1 — Deploy App
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

# PHASE 2 — NGINX Ingress
winget install Helm.Helm
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace --set controller.replicaCount=1 --set controller.resources.requests.cpu=100m --set controller.resources.requests.memory=128Mi --set controller.resources.limits.cpu=250m --set controller.resources.limits.memory=256Mi
kubectl get svc -n ingress-nginx --watch
# PATCH SNAT for IP Hash:
kubectl patch svc ingress-nginx-controller -n ingress-nginx -p '{"spec":{"externalTrafficPolicy":"Local"}}'

# PHASE 4 & 5 — Testing (Repeat for each algorithm modifying Ingress and CSV name)
# Apply ingress rules
kubectl apply -f ingress-round-robin.yaml

# Phase 4.1: Baseline (50 Users)
py -m locust -f locustfile.py --host=http://<EXTERNAL-IP> --headless --users 50 --spawn-rate 5 --run-time 5m --csv=results_round_robin_50

# Phase 4.2: Resource Logging (100 Users) - Run logger in Terminal 1, Locust in Terminal 2
while ($true) { Get-Date >> cpu_rr_100.txt; kubectl top pods >> cpu_rr_100.txt; Start-Sleep -Seconds 5 }
py -m locust -f locustfile.py --host=http://<EXTERNAL-IP> --headless --users 100 --spawn-rate 10 --run-time 5m --csv=results_round_robin_100

# Phase 5: Fault Tolerance (200 Users) - Run Locust, then delete a pod at 2:00 mins
py -m locust -f locustfile.py --host=http://<EXTERNAL-IP> --headless --users 200 --spawn-rate 20 --run-time 5m --csv=fault_round_robin_200
kubectl delete pod <target-pod>

# PHASE 6 — Distribution Check (Optional)
1..20 | ForEach-Object { (Invoke-WebRequest -Uri "http://<EXTERNAL-IP>/" -UseBasicParsing).Content | ConvertFrom-Json | Select-Object -ExpandProperty os | Select-Object -ExpandProperty hostname }

# PHASE 7 — Analysis
py -m pip install pandas matplotlib numpy
py analyze_results.py

# PHASE 8 — Cleanup
az group delete --name LoadBalancingResearch --yes --no-wait
```
