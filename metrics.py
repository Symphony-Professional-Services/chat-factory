#!/usr/bin/env python3

import os
import json
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd
import argparse
from datetime import datetime

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Analyze synthetic chat data and log metrics.")
    parser.add_argument('--run_id', type=str, required=True, help='Unique identifier for the run (e.g., timestamp)')
    parser.add_argument('--metadata', type=str, default='', help='Additional metadata for the run')
    return parser.parse_args()

def analyze_data(data_dir):
    """
    Analyzes the synthetic chat data.

    Parameters:
    - data_dir (Path): Path to the synthetic_data directory.

    Returns:
    - dict: Dictionary containing all the computed metrics.
    """
    # Initialize counters and data structures
    total_conversations = 0
    advisor_conversations = defaultdict(int)
    client_conversations = defaultdict(int)
    topic_counter = Counter()
    category_counter = Counter()
    
    # Iterate through the advisor and client directories
    for advisor_dir in data_dir.iterdir():
        if advisor_dir.is_dir():
            advisor_name = advisor_dir.name
            for client_file in advisor_dir.glob('*.json'):
                client_name = client_file.stem
                try:
                    with open(client_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    conversations = data.get('conversations', [])
                    
                    # Update total conversations
                    num_convs = len(conversations)
                    total_conversations += num_convs
                    
                    # Update advisor and client conversation cts
                    advisor_conversations[advisor_name] += num_convs
                    client_conversations[client_name] += num_convs
                    
                    # Update ct for metrics
                    for conv in conversations:
                        topic = conv.get('topic', 'Unknown')
                        category = conv.get('category', 'Unknown')
                        topic_counter[topic] += 1
                        category_counter[category] += 1
                        
                except json.JSONDecodeError:
                    print(f"Error decoding JSON in file: {client_file}")
                except Exception as e:
                    print(f"Unexpected error processing file {client_file}: {e}")
    
    num_advisors = len([d for d in data_dir.iterdir() if d.is_dir()])
    num_clients = len(set(client_conversations.keys()))
    
    metrics = {
        'total_conversations': total_conversations,
        'num_advisors': num_advisors,
        'num_clients': num_clients,
        'advisor_conversations': dict(advisor_conversations),
        'client_conversations': dict(client_conversations),
        'top_topics': topic_counter.most_common(10),
        'top_categories': category_counter.most_common(10)
    }
    
    return metrics

def display_metrics(metrics):
    """
    Displays the metrics on the console.

    Parameters:
    - metrics (dict): Dictionary containing all the computed metrics.
    """
    print("\n=== Synthetic Chat Data Analytics ===\n")
    
    print(f"Total Number of Conversations: {metrics['total_conversations']}\n")
    
    print("Number of Conversations per Advisor:")
    advisor_df = pd.DataFrame.from_dict(metrics['advisor_conversations'], orient='index', columns=['Conversations'])
    advisor_df = advisor_df.sort_values(by='Conversations', ascending=False)
    print(advisor_df)
    print("\n")
    
    print("Number of Conversations per Client:")
    client_df = pd.DataFrame.from_dict(metrics['client_conversations'], orient='index', columns=['Conversations'])
    client_df = client_df.sort_values(by='Conversations', ascending=False)
    print(client_df)
    print("\n")
    
    print(f"Total Number of Advisors (Channels): {metrics['num_advisors']}\n")
    print(f"Total Number of Clients: {metrics['num_clients']}\n")
    
    print("Top 10 Topics:")
    topic_df = pd.DataFrame(metrics['top_topics'], columns=['Topic', 'Count'])
    print(topic_df)
    print("\n")
    
    print("Top 10 Categories:")
    category_df = pd.DataFrame(metrics['top_categories'], columns=['Category', 'Count'])
    print(category_df)
    print("\n")
    
    print("=== End of Analytics ===\n")

def log_metrics(run_id, metadata, metrics, csv_file='metrics_log.csv'):
    """
    Logs the metrics to a CSV file.

    Parameters:
    - run_id (str): Unique identifier for the run.
    - metadata (str): Additional metadata for the run.
    - metrics (dict): Dictionary containing all the computed metrics.
    - csv_file (str): Path to the CSV file for logging metrics.
    """
    # Prepare data for logging
    log_entry = {
        'run_id': run_id,
        'metadata': metadata,
        'timestamp': datetime.utcnow().isoformat() + "Z",
        'total_conversations': metrics['total_conversations'],
        'num_advisors': metrics['num_advisors'],
        'num_clients': metrics['num_clients']
    }
    
    # Flatten conversations
    for advisor, count in metrics['advisor_conversations'].items():
        key = f'advisor_{advisor}_conversations'
        log_entry[key] = count
    
    # Flatten conversations
    for client, count in metrics['client_conversations'].items():
        key = f'client_{client}_conversations'
        log_entry[key] = count
    
    # Flatten top_topics
    for i, (topic, count) in enumerate(metrics['top_topics'], start=1):
        key = f'top_topic_{i}'
        log_entry[key] = topic
        log_entry[f'top_topic_{i}_count'] = count
    
    # Flatten top_categories
    for i, (category, count) in enumerate(metrics['top_categories'], start=1):
        key = f'top_category_{i}'
        log_entry[key] = category
        log_entry[f'top_category_{i}_count'] = count
    
    file_exists = Path(csv_file).is_file()
    df = pd.DataFrame([log_entry])
    
    try:
        if not file_exists:
            df.to_csv(csv_file, index=False)
            print(f"Created new metrics log file: {csv_file}")
        else:
            df.to_csv(csv_file, mode='a', header=False, index=False)
            print(f"Appended metrics to existing log file: {csv_file}")
    except Exception as e:
        print(f"Error writing to CSV file {csv_file}: {e}")

def main():
    args = parse_arguments()
    run_id = args.run_id
    metadata = args.metadata
    
    DATA_DIR = Path('synthetic_data')
    
    metrics = analyze_data(DATA_DIR)
    
    display_metrics(metrics)
    
    log_metrics(run_id, metadata, metrics)

if __name__ == "__main__":
    main()
