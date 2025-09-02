#!/usr/bin/env python3

import os
import json
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd
import argparse
from datetime import datetime
import glob
import statistics
import logging

# Import config so we can load company data file path
import configs.config as config

def parse_arguments():
    """
    Parses command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Analyze synthetic chat data and log metrics.")
    parser.add_argument('--run_id', type=str, default=None, help='Unique identifier for the run (e.g., timestamp) - for run-specific metrics.')
    parser.add_argument('--metadata', type=str, default='', help='Additional metadata for the run.')
    parser.add_argument('--repo_metrics', action='store_true', help='Analyze metrics for the entire synthetic data repository (ignores --run_id and --metadata).')
    return parser.parse_args()

import os
import json
import glob
import statistics
import logging
from pathlib import Path
from collections import defaultdict, Counter
import pandas as pd

def analyze_data(data_dir, is_repository_analysis=False):
    """
    Analyzes synthetic chat data, either for a specific run or the entire repository.
    
    Expects each JSON file to be a dictionary with a key "conversations" that is a list.
    
    Logs detailed warnings for files that are skipped because they do not match the expected structure,
    and writes a summary of these skipped files to a text file for further review.
    
    Parameters:
      - data_dir (Path): Path to the synthetic_data directory or a run-specific subdirectory.
      - is_repository_analysis (bool): Flag to indicate if it's a repository-wide analysis.
    
    Returns:
      dict: Dictionary containing all the computed metrics.
    """
    total_conversations = 0
    advisor_conversations = defaultdict(int)
    client_conversations = defaultdict(int)
    topic_counter = Counter()
    category_counter = Counter()
    processed_files = 0
    conversation_lengths = []  # To store number of messages per conversation
    overall_company_mentions = Counter()  # For company mention stats
    company_mentions_per_conversation = []  # Total company mentions per conversation

    # List to keep track of files that are skipped along with reasons
    skipped_files = []

    file_list = []
    if is_repository_analysis:
        # For repository analysis, search all JSON files in advisor directories
        for advisor_dir in data_dir.iterdir():
            if advisor_dir.is_dir():
                file_list.extend(glob.glob(str(advisor_dir / "*.json")))
    else:
        # For run-specific analysis, assume data_dir is the run directory with subdirectories per advisor
        file_list.extend(glob.glob(str(data_dir / "*/*.json")))

    for filepath_str in file_list:
        client_file = Path(filepath_str)
        advisor_name = client_file.parent.name
        client_name = client_file.stem
        try:
            with open(client_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate the structure: expect a dict with key "conversations" that is a list.
            if isinstance(data, dict) and "conversations" in data and isinstance(data["conversations"], list):
                conversations = data["conversations"]
                num_convs = len(conversations)
                total_conversations += num_convs
                processed_files += 1

                advisor_conversations[advisor_name] += num_convs
                client_conversations[client_name] += num_convs

                for conv in conversations:
                    # Track conversation lengths based on the "lines" key (default to empty list if not found)
                    lines = conv.get("lines", [])
                    conversation_lengths.append(len(lines))
                    
                    # Count company mentions using a simple case-insensitive substring match.
                    conv_mention_count = 0
                    text_aggregate = " ".join([line.get("text", "").lower() for line in lines])
                    try:
                        companies_df = pd.read_csv(config.COMPANY_DATA_FILE, engine="python", on_bad_lines='warn')
                        company_list = companies_df["name"].dropna().tolist()
                    except Exception as e:
                        logging.error(f"Error loading company data from {config.COMPANY_DATA_FILE}: {e}")
                        company_list = []
                    for company in company_list:
                        count = text_aggregate.count(company.lower())
                        if count > 0:
                            overall_company_mentions[company] += count
                            conv_mention_count += count
                    company_mentions_per_conversation.append(conv_mention_count)
                    
                    # Update topic and category metrics.
                    topic = conv.get('topic', 'Unknown')
                    category = conv.get('category', 'Unknown')
                    topic_counter[topic] += 1
                    category_counter[category] += 1
            else:
                reason = f"Unexpected structure: Type={type(data)}"
                if isinstance(data, dict):
                    reason += f", Keys={list(data.keys())}"
                logging.info(f"Skipping file {client_file}: {reason}")
                skipped_files.append((str(client_file), reason))
        except json.JSONDecodeError as e:
            err_msg = f"JSON decoding error: {e}"
            logging.error(f"Error decoding JSON in file {client_file}: {err_msg}")
            skipped_files.append((str(client_file), err_msg))
        except Exception as e:
            err_msg = f"Unexpected error: {e}"
            logging.error(f"Unexpected error processing file {client_file}: {err_msg}")
            skipped_files.append((str(client_file), err_msg))
    
    # Write the list of skipped files to a log file for further review.
    # if skipped_files:
    #     logs_dir = Path("logs")
    #     logs_dir.mkdir(exist_ok=True)
    #     skipped_log_path = logs_dir / "skipped_files.txt"
    #     with skipped_log_path.open("w", encoding="utf-8") as f:
    #         for fname, reason in skipped_files:
    #             f.write(f"{fname}: {reason}\n")
    #     logging.info(f"Details of skipped files written to {skipped_log_path.resolve()}")
    #     logging.info(f"Skipped {len(skipped_files)} files due to unexpected structure or errors:")
    #     for fname, reason in skipped_files:
    #         logging.info(f"  - {fname}: {reason}")

    if skipped_files:
        # Use an absolute path where you expect to see the logs (adjust as needed)
        logs_dir = Path("/app/output/logs")
        logs_dir.mkdir(parents=True, exist_ok=True)
        skipped_log_path = logs_dir / "skipped_files.txt"
        with skipped_log_path.open("w", encoding="utf-8") as f:
            for fname, reason in skipped_files:
                f.write(f"{fname}: {reason}\n")
        logging.info(f"Details of skipped files written to {skipped_log_path.resolve()}")
        logging.info(f"Skipped {len(skipped_files)} files due to unexpected structure or errors:")
        for fname, reason in skipped_files:
            logging.info(f"  - {fname}: {reason}")
    
    num_advisors = len([d for d in data_dir.iterdir() if d.is_dir() and any(f.suffix == '.json' for f in d.iterdir())])
    num_clients = len(set(client_conversations.keys()))

    # Compute conversation length statistics.
    if conversation_lengths:
        min_length = min(conversation_lengths)
        max_length = max(conversation_lengths)
        avg_length = sum(conversation_lengths) / len(conversation_lengths)
        med_length = statistics.median(conversation_lengths)
    else:
        min_length = max_length = avg_length = med_length = 0

    # Compute company mention statistics.
    total_company_mentions = sum(overall_company_mentions.values())
    if company_mentions_per_conversation:
        avg_mentions = sum(company_mentions_per_conversation) / len(company_mentions_per_conversation)
    else:
        avg_mentions = 0

    metrics = {
        'total_conversations': total_conversations,
        'processed_json_files': processed_files,
        'num_advisors': num_advisors,
        'num_clients': num_clients,
        'advisor_conversations': dict(advisor_conversations),
        'client_conversations': dict(client_conversations),
        'top_topics': topic_counter.most_common(10),
        'top_categories': category_counter.most_common(10),
        # Conversation length metrics:
        'conversation_lengths': conversation_lengths,
        'min_conversation_length': min_length,
        'max_conversation_length': max_length,
        'avg_conversation_length': avg_length,
        'med_conversation_length': med_length,
        # Company mention metrics:
        'total_company_mentions': total_company_mentions,
        'avg_company_mentions_per_conversation': avg_mentions,
        'top_company_mentions': overall_company_mentions.most_common(5)
    }
    
    return metrics


def display_metrics(metrics, is_repository_analysis=False):
    analysis_type = "Synthetic Data Repository" if is_repository_analysis else "Synthetic Data Generation Run"
    print(f"\n=== {analysis_type} Analytics ===\n")
    print(f"Total Number of Conversations: {metrics['total_conversations']}")
    print(f"Total JSON Files Processed: {metrics['processed_json_files']}\n")
    
    print("Conversations per Advisor:")
    advisor_df = pd.DataFrame.from_dict(metrics['advisor_conversations'], orient='index', columns=['Conversations'])
    advisor_df = advisor_df.sort_values(by='Conversations', ascending=False)
    print(advisor_df, "\n")
    
    print("Conversations per Client:")
    client_df = pd.DataFrame.from_dict(metrics['client_conversations'], orient='index', columns=['Conversations'])
    client_df = client_df.sort_values(by='Conversations', ascending=False)
    print(client_df, "\n")
    
    print(f"Total Number of Advisors (Channels): {metrics['num_advisors']}")
    print(f"Total Number of Clients: {metrics['num_clients']}\n")
    
    print("Top 10 Topics:")
    topic_df = pd.DataFrame(metrics['top_topics'], columns=['Topic', 'Count'])
    print(topic_df, "\n")
    
    print("Top 10 Categories:")
    category_df = pd.DataFrame(metrics['top_categories'], columns=['Category', 'Count'])
    print(category_df, "\n")
    
    # Display conversation length metrics
    print("Conversation Length Distribution:")
    print(f"  Min: {metrics.get('min_conversation_length', 0)}, "
          f"Max: {metrics.get('max_conversation_length', 0)}, "
          f"Average: {metrics.get('avg_conversation_length', 0):.2f}, "
          f"Median: {metrics.get('med_conversation_length', 0)}\n")
    
    # Display company mention metrics
    print("Company Mentions:")
    print(f"  Total Mentions: {metrics.get('total_company_mentions', 0)}")
    print(f"  Average Mentions per Conversation: {metrics.get('avg_company_mentions_per_conversation', 0):.2f}")
    print("  Top 5 Company Mentions:")
    for company, count in metrics.get('top_company_mentions', []):
        print(f"    {company}: {count}")
    
    print(f"\n=== End of {analysis_type} Analytics ===\n")


def log_metrics(run_id, metadata, metrics, csv_file='metrics_log.csv', is_repository_analysis=False):
    log_type = "repository_metrics" if is_repository_analysis else "run_metrics"
    run_identifier = run_id if run_id else "repository_analysis"

    log_entry = {
        'type': log_type,
        'run_id': run_identifier,
        'metadata': metadata if metadata else "repository_analysis",
        'timestamp': datetime.utcnow().isoformat() + "Z",
        'total_conversations': metrics['total_conversations'],
        'processed_json_files': metrics['processed_json_files'],
        'num_advisors': metrics['num_advisors'],
        'num_clients': metrics['num_clients'],
        # New fields for conversation lengths
        'min_conversation_length': metrics['min_conversation_length'],
        'max_conversation_length': metrics['max_conversation_length'],
        'avg_conversation_length': metrics['avg_conversation_length'],
        'med_conversation_length': metrics['med_conversation_length'],
        # New fields for company mentions
        'total_company_mentions': metrics['total_company_mentions'],
        'avg_company_mentions_per_conversation': metrics['avg_company_mentions_per_conversation']
    }
    
    for advisor, count in metrics['advisor_conversations'].items():
        key = f'advisor_{advisor.replace(" ", "_")}_conversations'
        log_entry[key] = count

    for client, count in metrics['client_conversations'].items():
        key = f'client_{client.replace(" ", "_")}_conversations'
        log_entry[key] = count

    for i, (topic, count) in enumerate(metrics['top_topics'], start=1):
        log_entry[f'top_topic_{i}'] = topic
        log_entry[f'top_topic_{i}_count'] = count

    for i, (category, count) in enumerate(metrics['top_categories'], start=1):
        log_entry[f'top_category_{i}'] = category
        log_entry[f'top_category_{i}_count'] = count

    # Also log top company mentions
    for i, (company, count) in enumerate(metrics['top_company_mentions'], start=1):
        log_entry[f'top_company_{i}'] = company
        log_entry[f'top_company_{i}_count'] = count

    csv_file_name = csv_file if not is_repository_analysis else 'repository_metrics_log.csv'
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
        log_metrics('repository', 'repository_analysis', metrics, is_repository_analysis=True)
    elif run_id:
        RUN_DATA_DIR = DATA_DIR / run_id
        if not RUN_DATA_DIR.exists() or not RUN_DATA_DIR.is_dir():
            print(f"Error: Run directory not found: {RUN_DATA_DIR}. Please provide a valid --run_id.")
            print("Available run directories in", DATA_DIR, "are:")
            for d in DATA_DIR.iterdir():
                if d.is_dir():
                    print(" -", d.name)
            return

        print(f"Analyzing metrics for run: {run_id}...")
        metrics = analyze_data(RUN_DATA_DIR)
        display_metrics(metrics)
        log_metrics(run_id, metadata, metrics)
    else:
        print("Error: Please provide either --run_id for a specific run or --repo_metrics for repository analysis.")
        return

if __name__ == "__main__":
    main()
