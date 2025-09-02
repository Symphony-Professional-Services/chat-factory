#!/usr/bin/env python3
"""
validate_data.py - Enhanced Data Quality and Validation Script

Performs configurable checks on raw synthetic conversation data output by the generator.
Reads generated JSON files and extracts manifest metadata BY PARSING the main
generator log file to produce a validation report.

Input: Generator output directory (e.g., synthetic_data/run_id_123/)
       Generator log file (e.g., output/logs/run_id_123.log)

Requires: pandas, sentence-transformers, scikit-learn, numpy, pyyaml, jsonschema
Install: pip install pandas sentence-transformers scikit-learn numpy pyyaml jsonschema
"""

import argparse
import json
import logging
import warnings
import importlib.util
import sys
import re # For parsing log lines
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd
import numpy as np
import yaml
import random
from jsonschema import validate as validate_json_schema
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

# --- Configuration Loading ---
DEFAULT_VALIDATION_CONFIG = {
    'tests_enabled': {
        'completeness': True,           # Checks based on extracted manifest count
        'schema': True,                 # Checks generator output file schema
        'temporal': True,               # Checks based on extracted manifest timestamps
        'distributions': True,          # Checks based on extracted manifest metadata
        'company_mentions': True,       # Checks based on extracted manifest flags
        'conversation_stats': True,     # Checks length based on extracted manifest
        'deduplication': True,          # Expensive, uses file content
    },
    # --- Thresholds & Parameters ---
    'completeness_tolerance_percent': 1.0,
    'schema_sample_size': 50,
    # Schema for the GENERATOR's output files (multi-convo)
    'expected_generator_output_schema': {
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "advisor": {"type": "string"},
            "client": {"type": "string"},
            "conversations": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "conversation_id": {"type": "string"},
                        "timestamp": {"type": "string", "format": "date-time"},
                        "category": {"type": "string"},
                        "topic": {"type": "string"},
                        "lines": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "speaker": {"type": "string"},
                                    "text": {"type": "string"},
                                    "timestamp": {"type": ["string", "null"], "format": "date-time"} # Allow null message timestamps
                                },
                                "required": ["speaker", "text"]
                            }
                        },
                        "company_mentions": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["conversation_id", "timestamp", "category", "topic", "lines"]
                }
            }
        },
        "required": ["version", "advisor", "client", "conversations"]
    },
    'min_temporal_coverage_percent': 90.0,
    'max_allowed_temporal_gap_days': 7,
    'max_dow_deviation_percent': 30.0,
    'min_company_mention_success_rate': 0.65,
    'dedup_similarity_threshold': 0.95,
    'dedup_embedding_model': 'all-MiniLM-L6-v2',
    'dedup_max_conversations_to_check': 10000,
    'min_topic_coverage_percent': 85.0,
    # --- Parameters potentially from Generator Config ---
    'generator_config_path': None, # Optional path to generator's config.py
    'taxonomy_path': None,
    'total_topics_in_taxonomy': None,
    'target_conversation_count': None, # Ideally derived from generator_config or manifest size
    'min_conversation_messages': None,
    'max_conversation_messages': None,
}

# Global cache
loaded_data_cache = {
        "manifest_df": None,
        "conversation_content": None, # This might hold convo_id -> lines mapping if loaded elsewhere
        "file_content_cache": {},   # <<< ADDED KEY FOR FILE-PATH BASED CACHING
        "generator_config": None,
        "taxonomy_topics": None,
    }

# --- Logging Setup ---
# (setup_logging function remains the same)
def setup_logging(log_file='validation.log'):
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)-7s] %(message)s',
        handlers=[
            logging.FileHandler(log_path, mode='w'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.getLogger('sentence_transformers').setLevel(logging.WARNING)

# --- Config & Data Loading Helpers ---
# (load_config, load_generator_config remain the same)
def load_config(config_path: Optional[str]) -> Dict:
    config = DEFAULT_VALIDATION_CONFIG.copy()
    if config_path and Path(config_path).exists():
        try:
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
            if user_config:
                config.update(user_config) # Simple merge, consider deep merge if needed
            logging.info(f"Loaded validation config from: {config_path}")
        except Exception as e:
            logging.warning(f"Could not load validation config {config_path}: {e}. Using defaults.")
    else:
        logging.info("Using default validation config.")
    return config

def load_generator_config(config_path: Optional[str]) -> Optional[object]:
    if not config_path or not Path(config_path).exists():
        logging.warning(f"Generator config path not provided or not found: {config_path}")
        return None
    # (importlib logic remains the same)
    try:
        config_path_obj = Path(config_path).resolve()
        spec = importlib.util.spec_from_file_location("generator_config", config_path_obj)
        if spec and spec.loader:
            gen_config_module = importlib.util.module_from_spec(spec)
            sys.modules['generator_config'] = gen_config_module # Needed for relative imports in config
            spec.loader.exec_module(gen_config_module)
            logging.info(f"Successfully loaded generator config from: {config_path}")
            return gen_config_module
        else:
            logging.error(f"Could not create module spec for generator config: {config_path}")
            return None
    except Exception as e:
        logging.error(f"Failed to load generator config {config_path}: {e}", exc_info=True)
        return None

# --- *** NEW MANIFEST PARSING FUNCTION *** ---
def load_manifest_from_generator_log(log_path: Path) -> Optional[pd.DataFrame]:
    """
    Parses the main generator log file to extract manifest JSON data logged by
    the 'conversation_manifest' logger.
    """
    if loaded_data_cache["manifest_df"] is not None:
        return loaded_data_cache["manifest_df"]

    if not log_path.exists():
        logging.error(f"Generator log file not found: {log_path}")
        return None

    logging.info(f"Attempting to extract manifest data from generator log: {log_path}")
    manifest_data = []
    # Regex to find lines from the specific logger and capture the JSON part
    # Adjust 'conversation_manifest - INFO - ' if your logger name/level format differs
    log_pattern = re.compile(r"conversation_manifest\s+-\s+INFO\s+-\s+(\{.*\})\s*$")

    try:
        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
            for i, line in enumerate(f):
                match = log_pattern.search(line)
                if match:
                    json_str = match.group(1)
                    try:
                        data = json.loads(json_str)
                        # Basic check for expected keys
                        if "conversation_id" in data and "conv_index" in data:
                            manifest_data.append(data)
                        else:
                             logging.warning(f"Log line {i+1}: Parsed JSON missing expected keys: {json_str[:100]}...")
                    except json.JSONDecodeError:
                        logging.warning(f"Log line {i+1}: Failed to decode JSON: {json_str[:100]}...")

        if not manifest_data:
             logging.error(f"No manifest data found in generator log file: {log_path}. Check log format/content.")
             return None

        df = pd.DataFrame(manifest_data)
        if 'timestamp' in df.columns:
             df['timestamp_dt'] = pd.to_datetime(df['timestamp'], errors='coerce')
        logging.info(f"Extracted {len(df)} manifest entries from {log_path}")
        loaded_data_cache["manifest_df"] = df
        return df
    except Exception as e:
        logging.error(f"Failed to load or parse generator log {log_path}: {e}", exc_info=True)
        return None

# (get_conversation_content remains the same - loads from data_dir)
# (get_taxonomy_topics remains the same)

# --- Validation Test Implementations ---

# (check_completeness - uses manifest_df count) - REVERT to original logic
def check_completeness(manifest_df: Optional[pd.DataFrame], config: Dict, gen_config: Optional[object]) -> Dict:
    test_name = "Completeness Check (Manifest Count)"
    if manifest_df is None: return {"test": test_name, "status": "ERROR", "message": "Manifest unavailable."}

    target_count = config.get('target_conversation_count')
    if target_count is None and gen_config:
        target_count = getattr(gen_config, 'NUM_CONVERSATIONS', None)
    if target_count is None:
        logging.warning("Target conversation count not determined. Using manifest count as base.")
        target_count = len(manifest_df) # Use actual count if target is unknown
        # return {"test": test_name, "status": "SKIP", "message": "Target conversation count not configured."}


    actual_count = len(manifest_df)
    tolerance_percent = config['completeness_tolerance_percent']
    tolerance = tolerance_percent / 100.0
    lower_bound_strict = target_count * (1 - tolerance) # Allow slight undercount

    status = "PASS"
    message = f"PASS: Found {actual_count} manifest entries, meeting target {target_count} (tolerance {tolerance_percent}%)."

    if actual_count < lower_bound_strict:
        status = "FAIL"
        message = f"FAIL: Found {actual_count} manifest entries, below tolerance ({tolerance_percent}%) of target {target_count} (Expected >={lower_bound_strict:.0f})."
    elif actual_count < target_count:
         status = "WARN"
         message = f"WARN: Found {actual_count} manifest entries, slightly below target {target_count}."
    elif actual_count > target_count * (1 + tolerance):
         status = "WARN"
         message = f"PASS: Found {actual_count} manifest entries (>{tolerance_percent}% over target {target_count})."

    # Check for gaps in conv_index if present
    gaps = []
    if 'conv_index' in manifest_df.columns:
        indices = sorted(manifest_df['conv_index'].unique())
        if indices:
             # Handle potential non-integer indices gracefully
             try:
                  numeric_indices = [int(i) for i in indices if isinstance(i, (int, float)) or str(i).isdigit()]
                  if numeric_indices:
                       expected_max = numeric_indices[-1]
                       expected = set(range(1, expected_max + 1)) # Assumes 1-based indexing
                       missing = sorted(list(expected - set(numeric_indices)))
                       if missing:
                            gaps = missing
                            message += f" Found gaps in conv_index: {len(gaps)} missing up to max index {expected_max}."
                            if status == "PASS": status = "WARN" # Downgrade if gaps found
                  else:
                       logging.warning("Could not find numeric values in 'conv_index' for gap analysis.")
             except Exception as e:
                  logging.warning(f"Error during conv_index gap analysis: {e}")


    return {"test": test_name, "status": status, "message": message, "metrics": {"actual_manifest_entries": actual_count, "target_convos": target_count, "missing_indices_count": len(gaps)}}

# (check_schema - needs updated schema and logic)
def check_schema(data_dir: Path, config: Dict) -> Dict:
    """Validates the JSON schema of a sample of GENERATOR output files."""
    test_name = "Schema Validation (Generator Output)"
    schema = config.get('expected_generator_output_schema') # Use the correct schema key
    if not schema:
        return {"test": test_name, "status": "SKIP", "message": "Expected generator output schema not defined."}

    sample_size = config['schema_sample_size']
    # Generator output files are directly in data_dir
    all_files = list(data_dir.glob('*.json'))
    files_to_check = all_files if len(all_files) <= sample_size else random.sample(all_files, sample_size)

    if not files_to_check:
         return {"test": test_name, "status": "WARN", "message": "No JSON files found in data_dir to check schema."}

    errors_found = 0
    error_details = []
    checked_count = 0

    logging.info(f"Checking schema for {len(files_to_check)} sampled generator output files...")
    for file_path in files_to_check:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f) # Load the whole file content
            checked_count += 1
            # Validate the loaded data against the expected generator output schema
            validate_json_schema(instance=data, schema=schema)
        # (Keep error handling similar to previous schema check)
        except json.JSONDecodeError as e:
            errors_found += 1
            error_details.append(f"{file_path.name}: JSON Decode Error - {e}")
        except JsonSchemaValidationError as e:
            errors_found += 1
            error_details.append(f"{file_path.name}: Schema Error - Path: {'/'.join(map(str, e.path))} - Message: {e.message}")
        except Exception as e:
            errors_found += 1
            error_details.append(f"{file_path.name}: General Error - {e}")

        if errors_found >= 10:
             error_details.append("... (additional errors suppressed)")
             break

    if errors_found > 0:
        status = "FAIL"
        message = f"FAIL: Found {errors_found} schema validation errors in {checked_count} sampled files."
        logging.warning("Schema errors found:")
        for detail in error_details:
             logging.warning(f"  - {detail}")
    else:
        status = "PASS"
        message = f"PASS: Schema validation passed for {checked_count} sampled files."

    return {"test": test_name, "status": status, "message": message, "metrics": {"files_checked": checked_count, "errors_found": errors_found}}


# (check_temporal_distribution - uses manifest_df) - REVERT to original
def check_temporal_distribution(manifest_df: Optional[pd.DataFrame], config: Dict) -> Dict:
    test_name = "Temporal Distribution"
    if manifest_df is None or 'timestamp_dt' not in manifest_df.columns:
        return {"test": test_name, "status": "ERROR", "message": "Manifest data/timestamps unavailable."}

    manifest_df = manifest_df.dropna(subset=['timestamp_dt'])
    if manifest_df.empty:
         return {"test": test_name, "status": "WARN", "message": "No valid timestamps found in manifest."}

    min_date = manifest_df['timestamp_dt'].min().date()
    max_date = manifest_df['timestamp_dt'].max().date()
    date_range_days = (max_date - min_date).days + 1 if max_date >= min_date else 0
    days_with_convos = manifest_df['timestamp_dt'].dt.date.nunique()

    coverage_percent = (days_with_convos / date_range_days * 100) if date_range_days > 0 else 0
    min_coverage_cfg = config.get('min_temporal_coverage_percent', 0)

    status = "PASS"
    message = f"Date range: {min_date} to {max_date} ({date_range_days} days). Days with conversations: {days_with_convos} ({coverage_percent:.1f}% coverage)."

    if coverage_percent < min_coverage_cfg:
        status = "FAIL"
        message += f" FAIL: Coverage below threshold ({min_coverage_cfg}%)."
    else:
        message += f" PASS: Coverage meets threshold ({min_coverage_cfg}%)."


    # Distribution checks (example)
    dow_counts = Counter(manifest_df['timestamp_dt'].dt.day_name())
    month_counts = Counter(manifest_df['timestamp_dt'].dt.strftime('%Y-%m'))
    avg_dow = len(manifest_df) / 7
    max_dev_pct = config.get('max_dow_deviation_percent', 1000) # Default high if not set
    dow_deviation_issues = []
    for day, count in dow_counts.items():
        deviation = abs(count - avg_dow) / avg_dow if avg_dow > 0 else 0
        if deviation * 100 > max_dev_pct:
            dow_deviation_issues.append(f"{day} ({count}, {deviation:.1%})")
    if dow_deviation_issues:
         message += f" WARN: Day-of-week distribution deviates significantly (> {max_dev_pct}%): {', '.join(dow_deviation_issues)}."
         if status == "PASS": status = "WARN"


    return {
        "test": test_name, "status": status, "message": message,
        "metrics": {
            "min_date": str(min_date), "max_date": str(max_date),
            "date_range_days": date_range_days, "days_with_convos": days_with_convos,
            "coverage_percent": round(coverage_percent, 2),
            "dow_distribution": dict(dow_counts),
            "month_distribution": dict(month_counts)
            }
        }

# (check_distributions - placeholder, uses manifest_df)
def check_distributions(manifest_df: Optional[pd.DataFrame], config: Dict, gen_config: Optional[object]) -> Dict:
     test_name = "Distribution Checks (Topic/Advisor/Client)"
     if manifest_df is None: return {"test": test_name, "status": "ERROR", "message": "Manifest unavailable."}

     results = {}
     warnings = []

     # Topic Distribution (Example)
     if 'category' in manifest_df.columns and 'topic' in manifest_df.columns:
        manifest_df['full_topic'] = manifest_df.apply(
            lambda row: f"{row.get('category','NA')}/{row.get('topic','NA')}" + (f"/{row.get('subtopic','NA')}" if pd.notna(row.get('subtopic')) and row.get('subtopic') else ""),
            axis=1
        )
        topic_counts = Counter(manifest_df['full_topic'])
        results['topic_distribution_summary'] = {"unique_topics_found": len(topic_counts), "top_5": topic_counts.most_common(5)}
        # Add checks for min/max counts if needed
     else:
        warnings.append("Topic/Category columns not found in manifest.")

     # Advisor/Client Distribution (Example)
     if 'advisor' in manifest_df.columns and 'client' in manifest_df.columns:
        advisor_counts = Counter(manifest_df['advisor'])
        client_counts = Counter(manifest_df['client'])
        pair_counts = Counter(zip(manifest_df['advisor'], manifest_df['client']))
        results['advisor_distribution_summary'] = {"unique_advisors": len(advisor_counts), "top_5": advisor_counts.most_common(5)}
        results['client_distribution_summary'] = {"unique_clients": len(client_counts), "top_5": client_counts.most_common(5)}
        results['pair_distribution_summary'] = {"unique_pairs": len(pair_counts), "top_5": pair_counts.most_common(5)}
        # Add checks for expected counts based on generator config if loaded
     else:
        warnings.append("Advisor/Client columns not found in manifest.")

     status = "PASS" if not warnings else "WARN"
     message = "Distribution summaries generated."
     if warnings: message += " Some columns missing for checks: " + "; ".join(warnings)

     return {"test": test_name, "status": status, "message": message, "metrics": results}


# (check_company_mentions - uses manifest_df) - REVERT to original
def check_company_mentions(manifest_df: Optional[pd.DataFrame], config: Dict) -> Dict:
    test_name = "Company Mention Rate"
    if manifest_df is None or 'company_targeting_enabled' not in manifest_df.columns or 'has_company_mentions' not in manifest_df.columns:
         return {"test": test_name, "status": "ERROR", "message": "Required company mention columns missing in manifest."}

    # Handle potential non-boolean values if parsing was imperfect
    manifest_df['company_targeting_enabled'] = manifest_df['company_targeting_enabled'].apply(lambda x: x is True or str(x).lower() == 'true')
    manifest_df['has_company_mentions'] = manifest_df['has_company_mentions'].apply(lambda x: x is True or str(x).lower() == 'true')


    targeted_df = manifest_df[manifest_df['company_targeting_enabled'] == True]
    if targeted_df.empty:
         return {"test": test_name, "status": "SKIP", "message": "No conversations were flagged for company targeting in manifest."}

    total_targeted = len(targeted_df)
    mentions_found_count = targeted_df['has_company_mentions'].sum()
    success_rate = (mentions_found_count / total_targeted) if total_targeted > 0 else 0
    min_rate = config.get('min_company_mention_success_rate', 0.0)

    if success_rate >= min_rate:
        status = "PASS"
        message = f"PASS: Company mention success rate {success_rate:.1%} >= threshold {min_rate:.1%}"
    else:
        status = "FAIL"
        message = f"FAIL: Company mention success rate {success_rate:.1%} < threshold {min_rate:.1%}"

    # Count specific companies mentioned
    company_counts = Counter()
    if 'companies_found' in targeted_df.columns:
         # Explode the lists of found companies and count
         all_mentions = targeted_df['companies_found'].dropna().explode()
         company_counts = Counter(all_mentions)

    return {"test": test_name, "status": status, "message": message, "metrics": {"total_targeted": total_targeted, "mentions_found_convos": int(mentions_found_count), "success_rate": round(success_rate, 3), "threshold": min_rate, "top_5_companies_mentioned": company_counts.most_common(5)}}

# (check_conversation_stats - uses manifest_df) - REVERT to using manifest
def check_conversation_stats(manifest_df: Optional[pd.DataFrame], config: Dict, gen_config: Optional[object]) -> Dict:
    test_name = "Conversation Stats (Length, etc.)"
    if manifest_df is None or 'num_messages_actual' not in manifest_df.columns:
         return {"test": test_name, "status": "ERROR", "message": "Required 'num_messages_actual' column missing in manifest."}

    min_allowed = config.get('min_conversation_messages')
    max_allowed = config.get('max_conversation_messages')
    # Get from gen_config if not set in validation config
    if min_allowed is None and gen_config: min_allowed = getattr(gen_config, 'MIN_MESSAGES', None)
    if max_allowed is None and gen_config: max_allowed = getattr(gen_config, 'MAX_MESSAGES', None)

    if min_allowed is None or max_allowed is None:
         return {"test": test_name, "status": "SKIP", "message": "Min/Max conversation messages not configured."}

    # Ensure column is numeric
    lengths = pd.to_numeric(manifest_df['num_messages_actual'], errors='coerce').dropna()
    if lengths.empty:
         return {"test": test_name, "status": "WARN", "message": "No valid numeric message counts found in manifest."}

    min_actual = lengths.min()
    max_actual = lengths.max()
    avg_actual = lengths.mean()
    out_of_bounds = lengths[(lengths < min_allowed) | (lengths > max_allowed)]
    num_out_of_bounds = len(out_of_bounds)
    checked_count = len(lengths)

    if num_out_of_bounds > 0:
        status = "WARN" # Or FAIL
        message = f"{status}: {num_out_of_bounds} conversations out of {checked_count} have lengths outside range [{min_allowed}, {max_allowed}]. Min/Max found: [{min_actual}, {max_actual}]."
    else:
        status = "PASS"
        message = f"PASS: All {checked_count} conversation lengths within manifest are within range [{min_allowed}, {max_allowed}]."

    # Add more stats: speaker turns, etc. if speaker data is reliable in manifest/content
    # ...

    return {"test": test_name, "status": status, "message": message, "metrics": {"checked_count": checked_count, "min_actual": int(min_actual), "max_actual": int(max_actual), "avg_actual": f"{avg_actual:.2f}", "num_out_of_bounds": num_out_of_bounds, "min_allowed": min_allowed, "max_allowed": max_allowed}}

def get_conversation_content_for_files(files_to_load: List[Path]) -> Dict[str, List[Dict]]:
    """
    Loads lines from a specific list of JSON files, using a file-path based cache
    within the global loaded_data_cache.
    """
    # Ensure the sub-cache exists
    if "file_content_cache" not in loaded_data_cache or loaded_data_cache["file_content_cache"] is None:
            loaded_data_cache["file_content_cache"] = {}

    content_map = {}
    loaded_count = 0
    if not files_to_load:
        logging.warning("get_conversation_content_for_files called with empty file list.")
        return {}

    logging.info(f"Loading/retrieving content for {len(files_to_load)} specified files...")
    for file_path in files_to_load:
        file_key = str(file_path)
        # --- Use the specific sub-cache ---
        if file_key in loaded_data_cache["file_content_cache"]:
            content_map[file_key] = loaded_data_cache["file_content_cache"][file_key]
            continue # Skip loading if already cached

        # --- Load and process if not cached ---
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            lines = [] # Default to empty list
            # Logic to extract lines based on expected generator output format
            if 'conversations' in data and isinstance(data['conversations'], list) and data['conversations']:
                    all_lines_in_file = []
                    for convo in data['conversations']:
                        if isinstance(convo, dict) and 'lines' in convo and isinstance(convo['lines'], list):
                            all_lines_in_file.extend(convo['lines'])
                    lines = all_lines_in_file
                    if not lines: logging.warning(f"File {file_path.name} contained 'conversations' but no valid 'lines'.")
            elif 'lines' in data and isinstance(data['lines'], list):
                    lines = data.get('lines') # Handle potentially formatted files too
            else:
                    logging.warning(f"Could not find 'conversations' list or 'lines' list in {file_path.name}")
                    lines = None # Mark as invalid if structure is totally wrong

            if lines is not None: # Cache even empty lists if structure was valid
                content_map[file_key] = lines
                # --- Store in the specific sub-cache ---
                loaded_data_cache["file_content_cache"][file_key] = lines
                loaded_count += 1
            # else: # Logged warning above if lines is None

        except json.JSONDecodeError:
                logging.warning(f"Skipping malformed JSON file: {file_path.name}")
        except Exception as e:
            logging.warning(f"Could not load or parse content from {file_path.name}: {e}")

    if loaded_count > 0:
        logging.info(f"Loaded content for {loaded_count} new files (total requested: {len(files_to_load)}).")
    elif files_to_load:
            logging.info(f"Content for {len(files_to_load)} requested files was already cached or failed to load.")

    return content_map

# (check_deduplication - uses content) - Keep similar, ensure it loads from data_dir
def check_deduplication(data_dir: Path, config: Dict) -> Dict:
    # This test requires loading content, uses helper get_conversation_content_for_files
    test_name = "Deduplication Check"
    if not config['tests_enabled'].get('deduplication'):
        return {"test": test_name, "status": "SKIP", "message": "Test disabled in config."}

    try:
        from sentence_transformers import SentenceTransformer, util
    except ImportError:
        return {"test": test_name, "status": "ERROR", "message": "Required libraries not found: sentence-transformers, torch."}

    model_name = config['dedup_embedding_model']
    threshold = config['dedup_similarity_threshold']
    max_convos_to_check = config['dedup_max_conversations_to_check']

    # Need to get *all* files first to decide on sampling
    all_files = list(data_dir.glob('*.json'))
    if len(all_files) < 2:
         return {"test": test_name, "status": "SKIP", "message": f"Not enough files ({len(all_files)}) to perform deduplication check."}

    files_to_check = all_files
    is_sample = False
    if len(all_files) > max_convos_to_check:
        logging.warning(f"Dataset file count ({len(all_files)}) exceeds deduplication check limit ({max_convos_to_check}). Sampling...")
        files_to_check = random.sample(all_files, max_convos_to_check)
        is_sample = True

    checked_input_files = len(files_to_check)

    try:
        logging.info(f"Loading sentence transformer model: {model_name}")
        model = SentenceTransformer(model_name)

        logging.info(f"Loading content and extracting text for {checked_input_files} conversations...")
        # Load content only for the files we decided to check
        content_map = get_conversation_content_for_files(files_to_check)

        corpus = []
        corpus_ids = [] # Use file path name as ID

        for file_path_str, lines in content_map.items():
            # Assumes one convo per generator output file based on current generator structure
            text = " ".join([line.get('text', '') for line in lines if line.get('text')])
            if text:
                corpus.append(text)
                corpus_ids.append(Path(file_path_str).name) # Use filename
            else:
                 logging.warning(f"Skipping empty/invalid content from {Path(file_path_str).name} for deduplication.")

        if len(corpus) < 2:
             return {"test": test_name, "status": "SKIP", "message": f"Not enough non-empty conversations ({len(corpus)}) loaded to perform deduplication."}

        logging.info(f"Generating embeddings for {len(corpus)} documents...")
        embeddings = model.encode(corpus, convert_to_tensor=True, show_progress_bar=True)

        logging.info("Calculating cosine similarities...")
        cos_sim_matrix = util.cos_sim(embeddings, embeddings)

        duplicate_pairs = []
        checked_pairs = set()
        for i in range(len(cos_sim_matrix)):
            for j in range(i + 1, len(cos_sim_matrix)):
                 similarity = cos_sim_matrix[i, j].item()
                 if similarity >= threshold:
                      pair = tuple(sorted((corpus_ids[i], corpus_ids[j])))
                      if pair not in checked_pairs:
                           duplicate_pairs.append({"pair": pair, "similarity": similarity})
                           checked_pairs.add(pair)

        num_duplicates = len(duplicate_pairs)
        comparison_count = len(corpus) * (len(corpus) - 1) / 2
        duplicate_rate = (num_duplicates / comparison_count * 100) if comparison_count > 0 else 0

        max_allowed_duplicates = int(len(corpus) * 0.01) # Example: Allow 1%

        if num_duplicates == 0:
            status = "PASS"
            message = f"PASS: No near-duplicate conversations found (threshold={threshold:.2f}) among {len(corpus)} checked documents ({'sampled' if is_sample else 'full dataset sample'})."
        elif num_duplicates <= max_allowed_duplicates:
            status = "WARN"
            message = f"WARN: Found {num_duplicates} near-duplicate pairs (similarity >= {threshold:.2f}) among {len(corpus)} checked documents (~{duplicate_rate:.2f}% duplicate rate)."
        else:
             status = "FAIL"
             message = f"FAIL: Found {num_duplicates} near-duplicate pairs (similarity >= {threshold:.2f}) among {len(corpus)} checked documents (~{duplicate_rate:.2f}% duplicate rate)."

        if 0 < num_duplicates <= 20:
             logging.info("Near-duplicate pairs found:")
             for dp in duplicate_pairs:
                  logging.info(f"  - {dp['pair'][0]} <-> {dp['pair'][1]} (Similarity: {dp['similarity']:.4f})")

        return {"test": test_name, "status": status, "message": message, "metrics": {"checked_documents": len(corpus), "threshold": threshold, "duplicate_pairs_found": num_duplicates, "duplicate_rate_percent": round(duplicate_rate,4), "is_sample": is_sample}}

    except Exception as e:
        logging.error(f"Error during deduplication check: {e}", exc_info=True)
        return {"test": test_name, "status": "ERROR", "message": f"An error occurred: {e}"}


def get_taxonomy_topics(taxonomy_path: Optional[str]) -> Optional[List[str]]:
    """Loads taxonomy and returns a flattened list of unique topic paths, using cache."""
    cache_key = "taxonomy_topics" # Key for the global cache
    # Check cache first
    if loaded_data_cache.get(cache_key) is not None:
        # Can return None if previous attempt failed and cached None
        return loaded_data_cache[cache_key]

    if not taxonomy_path:
        logging.warning("Taxonomy path not provided in config, cannot load topics.")
        loaded_data_cache[cache_key] = None # Cache the failure
        return None

    taxonomy_file = Path(taxonomy_path)
    if not taxonomy_file.is_file(): # Check if it's actually a file
        logging.warning(f"Taxonomy path specified but file not found or not a file: {taxonomy_path}")
        loaded_data_cache[cache_key] = None # Cache the failure
        return None

    try:
        logging.info(f"Loading and flattening taxonomy from: {taxonomy_path}")
        with open(taxonomy_file, 'r', encoding='utf-8') as f:
            taxonomy_data = json.load(f)

        # Flatten (adjust this logic if your taxonomy structure is different)
        flattened = set()
        for category, items in taxonomy_data.items():
            if isinstance(items, dict): # Category -> Topic -> Subtopic(s)
                for topic, subtopics in items.items():
                    # Handle cases where value might not be a list (e.g., topic maps to single string description)
                    if isinstance(subtopics, list) and subtopics:
                        for subtopic in subtopics:
                           if isinstance(subtopic, str): # Ensure subtopic is a string
                                flattened.add(f"{category}/{topic}/{subtopic}")
                    elif isinstance(topic, str): # Topic without subtopics under this category
                         flattened.add(f"{category}/{topic}")
            elif isinstance(items, list): # Category -> Topic(s)
                 for topic in items:
                      if isinstance(topic, str): # Ensure topic is a string
                           flattened.add(f"{category}/{topic}")
            # Add more structure handling if your taxonomy is deeper/different

        topic_list = sorted(list(flattened))
        logging.info(f"Loaded and flattened {len(topic_list)} unique topics from {taxonomy_path}")
        loaded_data_cache[cache_key] = topic_list # Store result in cache
        return topic_list

    except json.JSONDecodeError:
         logging.error(f"Failed to decode JSON from taxonomy file: {taxonomy_path}")
         loaded_data_cache[cache_key] = None # Cache failure
         return None
    except Exception as e:
        logging.error(f"Failed to load/flatten taxonomy {taxonomy_path}: {e}", exc_info=True)
        loaded_data_cache[cache_key] = None # Cache failure
        return None


# (check_topic_coverage - uses manifest_df) - REVERT to original
def check_topic_coverage(manifest_df: Optional[pd.DataFrame], config: Dict) -> Dict:
    test_name = "Topic Coverage"
    if manifest_df is None:
        return {"test": test_name, "status": "ERROR", "message": "Manifest unavailable."}
    if not all(col in manifest_df.columns for col in ['category', 'topic']):
        return {"test": test_name, "status": "WARN", "message": "Manifest missing category/topic columns."}

    # Combine topic/subtopic for unique path check
    manifest_df['full_topic'] = manifest_df.apply(
        lambda row: f"{row.get('category','NA')}/{row.get('topic','NA')}" + (f"/{row.get('subtopic','NA')}" if pd.notna(row.get('subtopic')) and row.get('subtopic') else ""),
        axis=1
    )
    generated_topics = manifest_df['full_topic'].nunique()

    total_possible_topics = config.get('total_topics_in_taxonomy')
    taxonomy_path = config.get('taxonomy_path')
    # Attempt to load from taxonomy file if count not provided
    if total_possible_topics is None and taxonomy_path:
         topic_list = get_taxonomy_topics(taxonomy_path) # Uses cache
         if topic_list:
              total_possible_topics = len(topic_list)
              config['total_topics_in_taxonomy'] = total_possible_topics # Update config for report

    min_coverage_percent = config.get('min_topic_coverage_percent', 0.0)

    if total_possible_topics is None:
        status = "WARN"
        message = f"{status}: Total number of possible topics unknown (configure 'total_topics_in_taxonomy' or 'taxonomy_path'). Found {generated_topics} unique generated topic paths."
        coverage_percent = None
    else:
        coverage_percent = (generated_topics / total_possible_topics * 100) if total_possible_topics > 0 else 0
        if coverage_percent >= min_coverage_percent:
             status = "PASS"
             message = f"PASS: Topic coverage {coverage_percent:.1f}% ({generated_topics}/{total_possible_topics}) >= threshold {min_coverage_percent:.1f}%."
        else:
             status = "FAIL"
             message = f"FAIL: Topic coverage {coverage_percent:.1f}% ({generated_topics}/{total_possible_topics}) < threshold {min_coverage_percent:.1f}%."


    return {"test": test_name, "status": status, "message": message, "metrics": {"generated_topics_unique": generated_topics, "total_possible_topics": total_possible_topics, "coverage_percent": round(coverage_percent, 2) if coverage_percent is not None else None}}

# --- Test Runner ---
def run_validation_suite(data_dir: Path, generator_log_path: Path, config: Dict) -> List[Dict]:
    """Loads data and runs all enabled validation tests."""
    results = []
    enabled_tests = config.get('tests_enabled', {})
    logging.info("--- Starting Validation Suite ---")

    # --- Load Generator Config (Optional) ---
    gen_config_path = config.get('generator_config_path')
    gen_config = load_generator_config(gen_config_path)
    loaded_data_cache["generator_config"] = gen_config
    # --- Update validation config with values from gen_config if needed ---
    if gen_config:
        config['target_conversation_count'] = getattr(gen_config, 'NUM_CONVERSATIONS', config['target_conversation_count'])
        config['min_conversation_messages'] = getattr(gen_config, 'MIN_MESSAGES', config['min_conversation_messages'])
        config['max_conversation_messages'] = getattr(gen_config, 'MAX_MESSAGES', config['max_conversation_messages'])
        config['taxonomy_path'] = getattr(gen_config, 'TAXONOMY_FILE', config['taxonomy_path'])
        # Update required fields if they were None
        if config.get('target_conversation_count') is None:
             logging.warning("Could not determine 'target_conversation_count' from generator config.")
        if config.get('min_conversation_messages') is None or config.get('max_conversation_messages') is None:
             logging.warning("Could not determine 'min/max_conversation_messages' from generator config.")


    # --- Load Manifest from Generator Log (Required for most tests) ---
    manifest_df = load_manifest_from_generator_log(generator_log_path)
    if manifest_df is None:
         # Allow schema and dedup to run even if manifest fails, but skip others
         logging.error(f"Failed to load manifest data from {generator_log_path}. Skipping manifest-dependent tests.")
         # Add a specific error result
         results.append({"test": "Manifest Loading", "status": "ERROR", "message": f"Failed to parse manifest data from log: {generator_log_path}"})
    loaded_data_cache["manifest_df"] = manifest_df # Store None if failed

    # --- Run Tests ---
    if enabled_tests.get('completeness'):
        results.append(check_completeness(manifest_df, config, gen_config))

    if enabled_tests.get('schema'):
        # Schema check reads files directly from data_dir
        results.append(check_schema(data_dir, config))

    if enabled_tests.get('temporal'):
        results.append(check_temporal_distribution(manifest_df, config))

    if enabled_tests.get('distributions'):
         results.append(check_distributions(manifest_df, config, gen_config))

    if enabled_tests.get('company_mentions'):
        results.append(check_company_mentions(manifest_df, config))

    if enabled_tests.get('conversation_stats'):
         results.append(check_conversation_stats(manifest_df, config, gen_config))

    if enabled_tests.get('topic_coverage'):
         results.append(check_topic_coverage(manifest_df, config)) # Will try to load taxonomy if path available

    # --- Deduplication (Loads content - Run last) ---
    if enabled_tests.get('deduplication'):
        # Pass data_dir, check_dedup will load content as needed via helper
        results.append(check_deduplication(data_dir, config))

    logging.info("--- Validation Suite Finished ---")
    return results


# --- Main Execution Logic ---
# (generate_report remains the same)
def generate_report(results: List[Dict], report_path: Path):
    logging.info(f"Generating validation report to: {report_path}")
    # (Keep previous generate_report implementation)
    overall_status = "PASS"
    summary = []
    status_counts = Counter()
    summary.append("="*60)
    summary.append("Data Validation Report")
    summary.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary.append("="*60 + "\n")
    for result in results:
        status = result.get("status", "ERROR")
        status_counts[status] += 1
        summary.append(f"Test:    {result.get('test', 'Unknown Test')}")
        summary.append(f"Status:  {status}")
        summary.append(f"Message: {result.get('message', 'No message.')}")
        if "metrics" in result and result["metrics"]:
             try:
                metrics_str = json.dumps(result['metrics'], indent=2, default=str)
                summary.append(f"Metrics:\n{metrics_str}")
             except TypeError:
                  summary.append(f"Metrics: (Could not serialize: {result['metrics']})")
        summary.append("-"*40)
        if status == "FAIL": overall_status = "FAIL"
        elif status in ["WARN", "ERROR"] and overall_status == "PASS": overall_status = "WARN"
    summary.append("\n" + "="*60)
    summary.append("Status Summary:")
    for status, count in status_counts.items(): summary.append(f"- {status}: {count}")
    summary.append(f"\nOverall Validation Status: {overall_status}")
    summary.append("="*60)
    report_content = "\n".join(summary); print(f"\nValidation Report Summary:\n{report_content}")
    try:
        with open(report_path, 'w') as f: f.write(report_content)
        logging.info(f"Validation report saved successfully.")
    except IOError as e: logging.error(f"Failed to write report file {report_path}: {e}")
    if overall_status == "FAIL": logging.error("One or more critical validation checks failed.")


def exit_with_error(message: str):
    logging.error(message)
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Validate raw synthetic conversation data using generator log for manifest.",
        formatter_class=argparse.RawDescriptionHelpFormatter
        )
    parser.add_argument('--data-dir', required=True, help='Path to the GENERATOR OUTPUT directory (e.g., synthetic_data/run_id_123).')
    parser.add_argument('--generator-log', required=True, help='Path to the main generator log file containing manifest entries.')
    parser.add_argument('--report-dir', default='validation_reports', help='Directory to save the validation report and log.')
    parser.add_argument('--config', help='Path to the YAML validation configuration file.')
    parser.add_argument('--generator-config', help='Optional path to the Python config file used for generation.')

    args = parser.parse_args()

    data_dir = Path(args.data_dir).resolve()
    generator_log_path = Path(args.generator_log).resolve()
    report_dir = Path(args.report_dir).resolve()
    report_dir.mkdir(parents=True, exist_ok=True)

    run_id = data_dir.name
    report_file = report_dir / f"validation_report_{run_id}.txt"
    log_file = report_dir / f"validation_process_{run_id}.log" # Log for the validation process itself

    setup_logging(log_file)
    logging.info(f"Starting validation for run '{run_id}' using Generator Log Mode")
    logging.info(f"Data Directory: {data_dir}")
    logging.info(f"Generator Log File: {generator_log_path}")
    logging.info(f"Report Directory: {report_dir}")
    if args.config: logging.info(f"Validation Config: {args.config}")
    if args.generator_config: logging.info(f"Generator Config: {args.generator_config}")

    if not data_dir.is_dir(): exit_with_error(f"Data directory not found: {data_dir}")
    if not generator_log_path.is_file(): exit_with_error(f"Generator log file not found: {generator_log_path}")

    config = load_config(args.config)
    config['generator_config_path'] = args.generator_config # Store path if provided

    results = run_validation_suite(data_dir, generator_log_path, config)

    generate_report(results, report_file)

    logging.info("Validation process finished.")
    print(f"\nValidation finished. Report saved to: {report_file}")


if __name__ == "__main__":
    main()