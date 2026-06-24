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
