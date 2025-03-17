# #!/usr/bin/env python3

# import os
# import json
# from pathlib import Path
# from collections import defaultdict, Counter
# import pandas as pd
# import argparse
# from datetime import datetime

# def parse_arguments():
#     """
#     Parses command-line arguments.
#     """
#     parser = argparse.ArgumentParser(description="Analyze synthetic chat data and log metrics.")
#     parser.add_argument('--run_id', type=str, required=True, help='Unique identifier for the run (e.g., timestamp)')
#     parser.add_argument('--metadata', type=str, default='', help='Additional metadata for the run')
#     return parser.parse_args()

# def analyze_data(data_dir):
#     """
#     Analyzes the synthetic chat data.

#     Parameters:
#     - data_dir (Path): Path to the synthetic_data directory.

#     Returns:
#     - dict: Dictionary containing all the computed metrics.
#     """
#     # Initialize counters and data structures
#     total_conversations = 0
#     advisor_conversations = defaultdict(int)
#     client_conversations = defaultdict(int)
#     topic_counter = Counter()
#     category_counter = Counter()
    
#     # Iterate through the advisor and client directories
#     for advisor_dir in data_dir.iterdir():
#         if advisor_dir.is_dir():
#             advisor_name = advisor_dir.name
#             for client_file in advisor_dir.glob('*.json'):
#                 client_name = client_file.stem
#                 try:
#                     with open(client_file, 'r', encoding='utf-8') as f:
#                         data = json.load(f)
                    
#                     conversations = data.get('conversations', [])
                    
#                     # Update total conversations
#                     num_convs = len(conversations)
#                     total_conversations += num_convs
                    
#                     # Update advisor and client conversation cts
#                     advisor_conversations[advisor_name] += num_convs
#                     client_conversations[client_name] += num_convs
                    
#                     # Update ct for metrics
#                     for conv in conversations:
#                         topic = conv.get('topic', 'Unknown')
#                         category = conv.get('category', 'Unknown')
#                         topic_counter[topic] += 1
#                         category_counter[category] += 1
                        
#                 except json.JSONDecodeError:
#                     print(f"Error decoding JSON in file: {client_file}")
#                 except Exception as e:
#                     print(f"Unexpected error processing file {client_file}: {e}")
    
#     num_advisors = len([d for d in data_dir.iterdir() if d.is_dir()])
#     num_clients = len(set(client_conversations.keys()))
    
#     metrics = {
#         'total_conversations': total_conversations,
#         'num_advisors': num_advisors,
#         'num_clients': num_clients,
#         'advisor_conversations': dict(advisor_conversations),
#         'client_conversations': dict(client_conversations),
#         'top_topics': topic_counter.most_common(10),
#         'top_categories': category_counter.most_common(10)
#     }
    
#     return metrics

# def display_metrics(metrics):
#     """
#     Displays the metrics on the console.

#     Parameters:
#     - metrics (dict): Dictionary containing all the computed metrics.
#     """
#     print("\n=== Synthetic Chat Data Analytics ===\n")
    
#     print(f"Total Number of Conversations: {metrics['total_conversations']}\n")
    
#     print("Number of Conversations per Advisor:")
#     advisor_df = pd.DataFrame.from_dict(metrics['advisor_conversations'], orient='index', columns=['Conversations'])
#     advisor_df = advisor_df.sort_values(by='Conversations', ascending=False)
#     print(advisor_df)
#     print("\n")
    
#     print("Number of Conversations per Client:")
#     client_df = pd.DataFrame.from_dict(metrics['client_conversations'], orient='index', columns=['Conversations'])
#     client_df = client_df.sort_values(by='Conversations', ascending=False)
#     print(client_df)
#     print("\n")
    
#     print(f"Total Number of Advisors (Channels): {metrics['num_advisors']}\n")
#     print(f"Total Number of Clients: {metrics['num_clients']}\n")
    
#     print("Top 10 Topics:")
#     topic_df = pd.DataFrame(metrics['top_topics'], columns=['Topic', 'Count'])
#     print(topic_df)
#     print("\n")
    
#     print("Top 10 Categories:")
#     category_df = pd.DataFrame(metrics['top_categories'], columns=['Category', 'Count'])
#     print(category_df)
#     print("\n")
    
#     print("=== End of Analytics ===\n")

# def log_metrics(run_id, metadata, metrics, csv_file='metrics_log.csv'):
#     """
#     Logs the metrics to a CSV file.

#     Parameters:
#     - run_id (str): Unique identifier for the run.
#     - metadata (str): Additional metadata for the run.
#     - metrics (dict): Dictionary containing all the computed metrics.
#     - csv_file (str): Path to the CSV file for logging metrics.
#     """
#     # Prepare data for logging
#     log_entry = {
#         'run_id': run_id,
#         'metadata': metadata,
#         'timestamp': datetime.utcnow().isoformat() + "Z",
#         'total_conversations': metrics['total_conversations'],
#         'num_advisors': metrics['num_advisors'],
#         'num_clients': metrics['num_clients']
#     }
    
#     # Flatten conversations
#     for advisor, count in metrics['advisor_conversations'].items():
#         key = f'advisor_{advisor}_conversations'
#         log_entry[key] = count
    
#     # Flatten conversations
#     for client, count in metrics['client_conversations'].items():
#         key = f'client_{client}_conversations'
#         log_entry[key] = count
    
#     # Flatten top_topics
#     for i, (topic, count) in enumerate(metrics['top_topics'], start=1):
#         key = f'top_topic_{i}'
#         log_entry[key] = topic
#         log_entry[f'top_topic_{i}_count'] = count
    
#     # Flatten top_categories
#     for i, (category, count) in enumerate(metrics['top_categories'], start=1):
#         key = f'top_category_{i}'
#         log_entry[key] = category
#         log_entry[f'top_category_{i}_count'] = count
    
#     file_exists = Path(csv_file).is_file()
#     df = pd.DataFrame([log_entry])
    
#     try:
#         if not file_exists:
#             df.to_csv(csv_file, index=False)
#             print(f"Created new metrics log file: {csv_file}")
#         else:
#             df.to_csv(csv_file, mode='a', header=False, index=False)
#             print(f"Appended metrics to existing log file: {csv_file}")
#     except Exception as e:
#         print(f"Error writing to CSV file {csv_file}: {e}")

# def main():
#     args = parse_arguments()
#     run_id = args.run_id
#     metadata = args.metadata
    
#     DATA_DIR = Path('synthetic_data')
    
#     metrics = analyze_data(DATA_DIR)
    
#     display_metrics(metrics)
    
#     log_metrics(run_id, metadata, metrics)

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3

import os
import json
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd
import argparse
from datetime import datetime
import glob

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Analyze synthetic chat data and log metrics.")
    parser.add_argument('--run_id', type=str, default=None, help='Unique identifier for the run (e.g., timestamp) - for run-specific metrics.')
    parser.add_argument('--metadata', type=str, default='', help='Additional metadata for the run.')
    parser.add_argument('--repo_metrics', action='store_true', help='Analyze metrics for the entire synthetic data repository (ignores --run_id and --metadata).')
    return parser.parse_args()

def analyze_data(data_dir, is_repository_analysis=False):
    """
    Analyzes synthetic chat data, either for a specific run or the entire repository.

    Parameters:
    - data_dir (Path): Path to the synthetic_data directory or a run-specific subdirectory.
    - is_repository_analysis (bool): Flag to indicate if it's a repository-wide analysis.

    Returns:
    - dict: Dictionary containing all the computed metrics.
    """
    # Initialize counters and data structures
    total_conversations = 0
    advisor_conversations = defaultdict(int)
    client_conversations = defaultdict(int)
    topic_counter = Counter()
    category_counter = Counter()
    processed_files = 0 # Track files processed for accurate conversation count

    file_list = []
    if is_repository_analysis:
        # For repository analysis, find all JSON files in all advisor directories
        for advisor_dir in data_dir.iterdir():
            if advisor_dir.is_dir():
                file_list.extend(glob.glob(str(advisor_dir / "*.json"))) # Use glob for broader file finding
    else:
        # For run-specific analysis, data_dir is already the run directory
        file_list.extend(glob.glob(str(data_dir / "*/*.json"))) # Look for files in subdirectories


    for filepath_str in file_list:
        client_file = Path(filepath_str) # Recreate Path object for consistency
        advisor_name = client_file.parent.name # Get advisor name from parent dir name
        client_name = client_file.stem # Get client name from filename

        try:
            with open(client_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Assuming each JSON file contains a SINGLE conversation
                # conversation data is now directly the list of messages
                conversation_data = data # No need to get 'conversations' as it's the root

                if isinstance(conversation_data, list): # Check if it is a list of messages (as expected)
                    total_conversations += 1 # Increment for each file processed as one conversation
                    processed_files += 1

                    advisor_conversations[advisor_name] += 1
                    client_conversations[client_name] += 1

                    # Extract topic and category - assuming they are at the file level metadata, not in messages
                    topic = data.get('conversation_type', 'Unknown') # Get conversation_type as topic
                    category = 'Financial Chat' # Generic Category, can be updated if needed

                    topic_counter[topic] += 1
                    category_counter[category] += 1
                else:
                    print(f"Warning: Unexpected JSON structure in file: {client_file}. Expected a JSON array (list of messages) at the root.")

        except json.JSONDecodeError:
            print(f"Error decoding JSON in file: {client_file}")
        except Exception as e:
            print(f"Unexpected error processing file {client_file}: {e}")

    num_advisors = len([d for d in data_dir.iterdir() if d.is_dir() and any(f.suffix == '.json' for f in d.iterdir())]) # Count advisor dirs with json files inside
    num_clients = len(set(client_conversations.keys()))

    metrics = {
        'total_conversations': total_conversations,
        'processed_json_files': processed_files, # Add count of JSON files actually processed
        'num_advisors': num_advisors,
        'num_clients': num_clients,
        'advisor_conversations': dict(advisor_conversations),
        'client_conversations': dict(client_conversations),
        'top_topics': topic_counter.most_common(10),
        'top_categories': category_counter.most_common(10)
    }
    return metrics

def display_metrics(metrics, is_repository_analysis=False):
    """
    Displays the metrics on the console.

    Parameters:
    - metrics (dict): Dictionary containing all the computed metrics.
    - is_repository_analysis (bool): Flag to indicate if it's repository-wide metrics.
    """
    analysis_type = "Synthetic Data Repository" if is_repository_analysis else "Synthetic Data Generation Run"

    print(f"\n=== {analysis_type} Analytics ===\n")
    print(f"Total Number of Conversations Analyzed: {metrics['total_conversations']}")
    print(f"Total JSON files Processed: {metrics['processed_json_files']}\n") # Show processed file count for debug

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

    print(f"Total Number of Advisors (Channels) with Data: {metrics['num_advisors']}\n") # Updated descriptor
    print(f"Total Number of Clients: {metrics['num_clients']}\n")

    print("Top 10 Conversation Types (Topics):") # Updated descriptor
    topic_df = pd.DataFrame(metrics['top_topics'], columns=['Topic', 'Count'])
    print(topic_df)
    print("\n")

    print("Top 10 Categories (General):") # Updated descriptor
    category_df = pd.DataFrame(metrics['top_categories'], columns=['Category', 'Count'])
    print(category_df)
    print("\n")

    print(f"=== End of {analysis_type} Analytics ===\n")

def log_metrics(run_id, metadata, metrics, csv_file='metrics_log.csv', is_repository_analysis=False):
    """
    Logs the metrics to a CSV file, differentiating between run and repository metrics.

    Parameters:
    - run_id (str): Unique identifier for the run (or 'repository' for repo metrics).
    - metadata (str): Additional metadata for the run (or 'repository_analysis' for repo metrics).
    - metrics (dict): Dictionary containing all the computed metrics.
    - csv_file (str): Path to the CSV file for logging metrics.
    - is_repository_analysis (bool): Flag to differentiate repository metrics.
    """
    log_type = "repository_metrics" if is_repository_analysis else "run_metrics"
    run_identifier = run_id if run_id else "repository_analysis" # Use 'repository_analysis' for repo metrics

    # Prepare data for logging
    log_entry = {
        'type': log_type, # Add type to differentiate run vs repo metrics
        'run_id': run_identifier, # Use run_id or 'repository_analysis'
        'metadata': metadata if metadata else "repository_analysis", # Use metadata or 'repository_analysis'
        'timestamp': datetime.utcnow().isoformat() + "Z",
        'total_conversations': metrics['total_conversations'],
        'processed_json_files': metrics['processed_json_files'], # Log processed json files
        'num_advisors': metrics['num_advisors'],
        'num_clients': metrics['num_clients']
    }

    # Flatten and log advisor conversations
    for advisor, count in metrics['advisor_conversations'].items():
        key = f'advisor_{advisor.replace(" ", "_")}_conversations' # Sanitize advisor name for CSV
        log_entry[key] = count

    # Flatten and log client conversations
    for client, count in metrics['client_conversations'].items():
        key = f'client_{client.replace(" ", "_")}_conversations' # Sanitize client name
        log_entry[key] = count

    # Flatten top_topics
    for i, (topic, count) in enumerate(metrics['top_topics'], start=1):
        key = f'top_topic_{i}'.replace(" ", "_") # Sanitize topic name
        log_entry[key] = topic
        log_entry[f'top_topic_{i}_count'] = count

    # Flatten top_categories
    for i, (category, count) in enumerate(metrics['top_categories'], start=1):
        key = f'top_category_{i}'.replace(" ", "_") # Sanitize category name
        log_entry[key] = category
        log_entry[f'top_category_{i}_count'] = count

    csv_file_name = csv_file if not is_repository_analysis else 'repository_metrics_log.csv' # Separate log file for repo metrics
    file_exists = Path(csv_file_name).is_file()
    df = pd.DataFrame([log_entry])

    try:
        if not file_exists:
            df.to_csv(csv_file_name, index=False)
            print(f"Created new metrics log file: {csv_file_name}")
        else:
            df.to_csv(csv_file_name, mode='a', header=False, index=False)
            print(f"Appended metrics to existing log file: {csv_file_name}")
    except Exception as e:
        print(f"Error writing to CSV file {csv_file_name}: {e}")

def main():
    args = parse_arguments()
    run_id = args.run_id
    metadata = args.metadata
    repo_metrics = args.repo_metrics

    DATA_DIR = Path('synthetic_data')

    if repo_metrics:
        print("Analyzing metrics for the entire synthetic data repository...")
        metrics = analyze_data(DATA_DIR, is_repository_analysis=True)
        display_metrics(metrics, is_repository_analysis=True)
        log_metrics('repository', 'repository_analysis', metrics, is_repository_analysis=True) # Consistent log parameters

    elif run_id:
        RUN_DATA_DIR = DATA_DIR / run_id # Run-specific data directory
        if not RUN_DATA_DIR.exists() or not RUN_DATA_DIR.is_dir():
            print(f"Error: Run directory not found: {RUN_DATA_DIR}. Please provide a valid --run_id.")
            return

        print(f"Analyzing metrics for run: {run_id}...")
        metrics = analyze_data(RUN_DATA_DIR) # Analyze run-specific dir
        display_metrics(metrics)
        log_metrics(run_id, metadata, metrics) # Log run-specific metrics
    else:
        print("Error: Please provide either --run_id for a specific run or --repo_metrics for repository analysis.")
        return

if __name__ == "__main__":
    main()