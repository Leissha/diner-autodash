import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set style
plt.style.use('default')
sns.set_theme(style="whitegrid")
sns.set_palette("husl")

# Create data for the three metrics
metrics_data = {
    'Average Wait Time': {
        'Servos': ['1 Servo', '2 Servos', '3 Servos'],
        'Values': [29.14, 28.28, 26.11],
        'Changes': ['', '-3.0%', '-7.7%']
    },
    'Satisfaction Rate': {
        'Servos': ['1 Servo', '2 Servos', '3 Servos'],
        'Values': [30.56, 47.22, 66.67],
        'Changes': ['', '+54.5%', '+41.2%']
    },
    'Profit': {
        'Servos': ['1 Servo', '2 Servos', '3 Servos'],
        'Values': [303.00, 746.67, 1278.00],
        'Changes': ['', '+146.4%', '+71.2%']
    }
}

# Create subplots
fig, axes = plt.subplots(1, 3, figsize=(20, 6))
fig.suptitle('DinnerAutoDash Performance Metrics by Number of Servos', fontsize=16, y=1.05)

# Plot each metric
for idx, (metric, data) in enumerate(metrics_data.items()):
    ax = axes[idx]
    
    # Create bar plot
    bars = ax.bar(data['Servos'], data['Values'])
    
    # Add value labels on top of bars
    for i, bar in enumerate(bars):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{data["Values"][i]:.2f}\n{data["Changes"][i]}',
                ha='center', va='bottom')
    
    # Customize plot
    ax.set_title(metric)
    ax.set_ylabel('Value')
    
    # Add grid for better readability
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)
    
    # Rotate x-axis labels for better readability
    plt.setp(ax.get_xticklabels(), rotation=45)

# Adjust layout and save
plt.tight_layout()
plt.savefig('insights/performance_metrics.png', dpi=300, bbox_inches='tight')


print("Graphs have been generated and saved in the insights directory!")