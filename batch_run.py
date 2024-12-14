import csv
import time
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
from scipy import stats
from itertools import combinations
import json
from constants import CUSTOMER_RANDOM_SPAWN_RATE, CustomerState
from world import World
import numpy as np

# Filter scipy warnings
warnings.filterwarnings('ignore', category=RuntimeWarning)
warnings.filterwarnings('ignore', category=UserWarning)

def create_insights_directory():
    """Create insights directory if it doesn't exist."""
    os.makedirs("insights", exist_ok=True)

def run_trials(num_servos, num_trials=30):
    """Run trials for a specific number of servos."""
    results = []
    for trial in range(num_trials):
        world = World(num_servos=num_servos, seed=trial, render=False)
        print(f"\nSEED={trial}  CUSTOMER_RANDOM_SPAWN_RATE={CUSTOMER_RANDOM_SPAWN_RATE}")
        print(f"Starting profit=${world.profit:.2f}, max_ticks={world.max_ticks}")
        cpu_ms = 0.0
        
        # Run until all customers are served or leave
        tick = 0
        while tick < 250 or len(world.customers) > 0:
            start = time.perf_counter()
            world._do_one_simulation_tick()
            end = time.perf_counter()
            cpu_ms += (end - start) * 1000.0
            tick += 1
            
            # Only spawn new customers up to tick 250
            if tick >= 250:
                world.spawn_rate = 0
        
        # Process any remaining customers
        print(f"\nProcessing completed at tick {tick}:")
        print(f"Final profit: ${world.profit:.2f}")
        
        # Calculate metrics
        total_customers = len(world.completed_customers)
        served_customers = len([c for c in world.completed_customers if c.finished_eating])
        satisfied_customers = len([c for c in world.completed_customers if c.satisfaction >= 30])
        service_rate = served_customers / total_customers * 100 if total_customers > 0 else 0
        satisfaction_rate = satisfied_customers / total_customers * 100 if total_customers > 0 else 0
        avg_wait_time = sum(c.wait_time for c in world.completed_customers) / len(world.completed_customers) if world.completed_customers else 0
        
        print(f"Total customers: {total_customers}")
        print(f"Served customers: {served_customers}")
        print(f"Satisfied customers: {satisfied_customers}")
        print(f"Service rate: {service_rate:.2f}%")
        print(f"Satisfaction rate: {satisfaction_rate:.2f}%")
        print(f"Average wait time: {avg_wait_time:.2f} minutes")
        print("-" * 80)
        
        # Store results
        results.append({
            'trial': trial,
            'num_servos': num_servos,
            'profit': world.profit - 500,
            'service_rate': service_rate,
            'satisfaction_rate': satisfaction_rate,
            'avg_wait_time': avg_wait_time,
            'cpu_ms': cpu_ms / tick,
            'total_customers': total_customers,
            'served_customers': served_customers,
            'satisfied_customers': satisfied_customers
        })
    
    # Print summary statistics
    avg_profit = sum(r['profit'] for r in results) / len(results)
    avg_service_rate = sum(r['service_rate'] for r in results) / len(results)
    avg_satisfaction_rate = sum(r['satisfaction_rate'] for r in results) / len(results)
    avg_wait_time = sum(r['avg_wait_time'] for r in results) / len(results)
    avg_cpu_ms = sum(r['cpu_ms'] for r in results) / len(results)
    
    print(f"\nResults for {num_servos} servo(s):")
    print(f"  Average Profit: ${avg_profit:.2f}")
    print(f"  Service Rate: {avg_service_rate:.2f}%")
    print(f"  Satisfaction Rate: {avg_satisfaction_rate:.2f}%")
    print(f"  Average Wait Time: {avg_wait_time:.2f} minutes")
    print(f"  Average CPU Time: {avg_cpu_ms:.2f}ms per tick")
    
    return results

def analyze_and_visualize_results(df):
    """Perform statistical analysis and create visualizations."""
    # --- 1. DETAILED STATS SUMMARY ---
    summary_stats = df.groupby('num_servos').agg({
        'avg_wait_time': ['mean', 'std'],
        'satisfaction_rate': ['mean', 'std'],
        'service_rate': ['mean', 'std'],
        'profit': ['mean', 'std'],
        'cpu_ms': ['mean', 'std']
    }).round(2)
    
    summary_stats.columns = ['_'.join(col).strip() for col in summary_stats.columns.values]
    summary_stats.to_csv('insights/summary_stats.csv')
    print("\n" + "="*80)
    print("DETAILED STATISTICS SUMMARY")
    print("="*80)
    print(summary_stats)

    # --- 2. COMPARATIVE ANALYSIS ---
    print("\n" + "="*80)
    print("COMPARATIVE ANALYSIS")
    print("="*80)
    
    metrics = ['avg_wait_time', 'satisfaction_rate', 'service_rate', 'profit', 'cpu_ms']
    servo_configs = sorted(df['num_servos'].unique())
    servo_pairs = list(combinations(servo_configs, 2))
    
    statistical_results = []
    graphing_data = {}

    for metric in metrics:
        graphing_data[metric] = {'Servos': [], 'Values': [], 'Changes': ['']}
        
        # Populate base values for graphing
        for servos in servo_configs:
             graphing_data[metric]['Servos'].append(f'{servos} Servo' + ('s' if servos > 1 else ''))
             graphing_data[metric]['Values'].append(summary_stats.loc[servos][f'{metric}_mean'])

        print(f"\n----- {metric.replace('_', ' ').title()} -----")
        
        for servo1, servo2 in servo_pairs:
            group1 = df[df['num_servos'] == servo1][metric]
            group2 = df[df['num_servos'] == servo2][metric]
            
            # Perform appropriate statistical test
            _, p_norm1 = stats.shapiro(group1)
            _, p_norm2 = stats.shapiro(group2)
            if p_norm1 > 0.05 and p_norm2 > 0.05:
                test_type = "Welch's t-test"
                _, p_val = stats.ttest_ind(group1, group2, equal_var=False)
            else:
                test_type = "Mann-Whitney U"
                _, p_val = stats.mannwhitneyu(group1, group2, alternative='two-sided')
            
            # Calculate effect size and percentage difference
            mean1, mean2 = group1.mean(), group2.mean()
            std1, std2 = group1.std(), group2.std()
            pooled_std = np.sqrt((std1**2 + std2**2) / 2)
            cohens_d = abs(mean1 - mean2) / pooled_std if pooled_std > 0 else float('inf')
            pct_diff = ((mean2 - mean1) / abs(mean1)) * 100 if mean1 != 0 else float('inf')

            graphing_data[metric]['Changes'].append(f"{pct_diff:+.1f}%")
            
            # Store results
            result = {
                'Metric': metric,
                'Comparison': f"{servo1} vs {servo2}",
                'Test_Type': test_type,
                'P_Value': f"{p_val:.4f}",
                'Significant': p_val < 0.05,
                'Cohens_D': f"{cohens_d:.2f}",
                'Effect_Size': 'Large' if cohens_d > 0.8 else 'Medium' if cohens_d > 0.5 else 'Small',
                f'Mean_{servo1}s': f"{mean1:.2f}",
                f'Mean_{servo2}s': f"{mean2:.2f}",
                'Change_Pct': f"{pct_diff:+.1f}%"
            }
            statistical_results.append(result)
            
            print(f"{servo1} vs {servo2} Servos: Change: {pct_diff:+.1f}% ({mean1:.2f} -> {mean2:.2f}), p={p_val:.4f}, effect={result['Effect_Size']}")

    # Save statistical results
    pd.DataFrame(statistical_results).to_csv('insights/statistical_analysis.csv', index=False)
    print("\nDetailed statistical results saved to 'insights/statistical_analysis.csv'")

    # --- 3. VISUALIZATION ---
    print("\nGenerating visualizations...")
    
    # Define colors for consistency
    metric_colors = {
        'Average Wait Time': '#3498db',
        'Satisfaction Rate': '#2ecc71',
        'Profit': '#e74c3c',
        'Service Rate': '#f1c40f',
        'CPU Performance': '#9b59b6'
    }
    
    # Create a single figure with subplots
    fig, axes = plt.subplots(len(metrics), 1, figsize=(12, 5 * len(metrics)))
    fig.suptitle('DinnerAutoDash Performance Analysis', fontsize=20, y=1.02)

    for i, metric_key in enumerate(metrics):
        metric_name = metric_key.replace('_', ' ').title()
        data = graphing_data[metric_key]
        ax = axes[i]
        
        bars = ax.bar(data['Servos'], data['Values'], color=metric_colors.get(metric_name, '#bdc3c7'), alpha=0.8)
        ax.set_title(metric_name, fontsize=14)
        ax.set_ylabel(metric_name)
        ax.grid(True, axis='y', linestyle='--', alpha=0.6)
        plt.setp(ax.get_xticklabels(), rotation=10, ha="right")

        for bar, change in zip(bars, data['Changes']):
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2.0, yval, f'{yval:.2f}', va='bottom', ha='center', fontsize=10)
            if change:
                 ax.text(bar.get_x() + bar.get_width()/2.0, yval / 2, change, va='center', ha='center', fontsize=12, color='white', weight='bold')

    plt.tight_layout(pad=3.0)
    plt.savefig('insights/performance_analysis.png', dpi=300, bbox_inches='tight')
    plt.close()

    print("Comprehensive performance analysis graph saved to 'insights/performance_analysis.png'")

def main(servo_configs_to_run=None):
    """Run the batch simulation."""
    if servo_configs_to_run is None:
        servo_configs_to_run = [1, 2, 3]

    all_results = []
    
    create_insights_directory()

    # Run trials for specified servo configurations
    for num_servos in servo_configs_to_run:
        results = run_trials(num_servos)
        all_results.extend(results)

    # Create and analyze the final DataFrame
    df = pd.DataFrame(all_results)
    df.to_csv('insights/results.csv', index=False)
    print("\nFull results saved to 'insights/results.csv'")
    
    if len(df['num_servos'].unique()) > 1:
        analyze_and_visualize_results(df)
    else:
        print("\nNeed at least two servo configurations to perform comparative analysis.")

if __name__ == "__main__":
    # To run for specific configurations, you can pass a list, e.g., main([1, 2, 3])
    main([1, 2, 3])
    
