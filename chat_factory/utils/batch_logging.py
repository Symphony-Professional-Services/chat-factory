import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
import json

class SummaryStatisticsLogger:
    def __init__(self, config, run_id, advisor_client_interactions=None, all_timestamps=None, manifest_logger=None, client_advisor_map=None, generation_strategy=None):
        self.config = config
        self.run_id = run_id
        self.advisor_client_interactions = advisor_client_interactions or {}
        self.all_timestamps = all_timestamps or []
        self.manifest_logger = manifest_logger
        self.client_advisor_map = client_advisor_map or {}
        self.generation_strategy = generation_strategy

    def log_temporal_distribution(self):
        """Logs summary of temporal distribution (by day, week, month)."""
        if self.all_timestamps:
            date_counts = {}
            month_counts = {}
            week_counts = {}
            day_counts = {}

            for ts in self.all_timestamps:
                dt = datetime.fromisoformat(ts)
                date_str = dt.date().isoformat()
                month_str = dt.strftime('%Y-%m')
                week_str = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
                day_str = dt.strftime('%A')

                date_counts[date_str] = date_counts.get(date_str, 0) + 1
                month_counts[month_str] = month_counts.get(month_str, 0) + 1
                week_counts[week_str] = week_counts.get(week_str, 0) + 1
                day_counts[day_str] = day_counts.get(day_str, 0) + 1

            logging.info("\n===== TEMPORAL DISTRIBUTION SUMMARY =====")
            logging.info("\n----- Daily Distribution -----")
            for date, count in sorted(date_counts.items()):
                logging.info(f"{date}: {count} conversations")

            logging.info("\n----- Weekly Distribution -----")
            for week, count in sorted(week_counts.items()):
                logging.info(f"{week}: {count} conversations")

            logging.info("\n----- Monthly Distribution -----")
            for month, count in sorted(month_counts.items()):
                logging.info(f"{month}: {count} conversations")

            logging.info("\n----- Day of Week Distribution -----")
            for day, count in sorted(day_counts.items(), key=lambda x: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'].index(x[0])):
                logging.info(f"{day}: {count} conversations")

    def log_advisor_client_distribution(self):
        """Logs summary of advisor-client distribution and interactions."""
        if self.client_advisor_map:
            client_counts = {advisor: len(clients) for advisor, clients in self.client_advisor_map.items()}
            sorted_counts = sorted(client_counts.items(), key=lambda x: x[1], reverse=True)

            total_clients = sum(client_counts.values())
            avg_clients = total_clients / len(client_counts) if client_counts else 0
            min_clients = min(client_counts.values()) if client_counts else 0
            max_clients = max(client_counts.values()) if client_counts else 0

            logging.info("\n===== CLIENT-ADVISOR DISTRIBUTION =====")
            logging.info(f"Total unique client-advisor pairings: {total_clients}")
            logging.info(f"Average clients per advisor: {avg_clients:.2f}")
            logging.info(f"Range: {min_clients} to {max_clients} clients per advisor")

            logging.info("\n----- Clients per Advisor -----")
            for advisor, count in sorted_counts:
                percentage = (count / len(self.config.CLIENT_NAMES)) * 100
                bar = "█" * int(percentage / 5)
                logging.info(f"{advisor}: {count} clients ({percentage:.1f}%) {bar}")

        if self.advisor_client_interactions:
            sorted_interactions = sorted(self.advisor_client_interactions.items(), key=lambda x: x[1], reverse=True)
            advisor_interaction_counts = {}
            advisor_unique_clients = {}

            for pair, count in sorted_interactions:
                advisor, client = pair.split('|')
                advisor_interaction_counts[advisor] = advisor_interaction_counts.get(advisor, 0) + count
                advisor_unique_clients.setdefault(advisor, set()).add(client)

            logging.info("\n===== ADVISOR-CLIENT INTERACTION SUMMARY =====")
            logging.info(f"Total unique advisor-client pairs with conversations: {len(self.advisor_client_interactions)}")

            logging.info("\n----- Advisor Activity (by conversation count) -----")
            max_advisor_count = max(advisor_interaction_counts.values()) if advisor_interaction_counts else 0

            for advisor, count in sorted(advisor_interaction_counts.items(), key=lambda x: x[1], reverse=True):
                unique_count = len(advisor_unique_clients[advisor])
                percentage = (count / self.config.NUM_CONVERSATIONS) * 100
                bar = "█" * int(percentage / 5)
                logging.info(f"{advisor}: {count} conversations ({percentage:.1f}%), {unique_count} unique clients {bar}")

            client_advisor_counts = {}
            for pair in self.advisor_client_interactions:
                advisor, client = pair.split('|')
                client_advisor_counts.setdefault(client, set()).add(advisor)

            client_advisor_counts = {client: len(advisors) for client, advisors in client_advisor_counts.items()}
            advisors_per_client = {}
            for client, count in client_advisor_counts.items():
                advisors_per_client[count] = advisors_per_client.get(count, 0) + 1

            logging.info("\n----- Client Distribution (by advisor count) -----")
            for adv_count in sorted(advisors_per_client.keys()):
                client_count = advisors_per_client[adv_count]
                percentage = (client_count / len(client_advisor_counts)) * 100
                bar = "█" * int(percentage / 5)
                logging.info(f"Clients with {adv_count} advisors: {client_count} clients ({percentage:.1f}%) {bar}")

            clients_per_advisor_histogram = {}
            for advisor, clients in advisor_unique_clients.items():
                client_count = len(clients)
                clients_per_advisor_histogram[client_count] = clients_per_advisor_histogram.get(client_count, 0) + 1

            logging.info("\n----- Distribution of Advisors by Client Count -----")
            for client_count in sorted(clients_per_advisor_histogram.keys()):
                advisor_count = clients_per_advisor_histogram[client_count]
                percentage = (advisor_count / len(advisor_unique_clients)) * 100
                bar = "█" * int(percentage / 5)
                logging.info(f"Advisors with {client_count} clients: {advisor_count} advisors ({percentage:.1f}%) {bar}")

            logging.info("\n----- Conversation Density Heat Map -----")
            top_advisors = [adv for adv, _ in sorted(advisor_interaction_counts.items(), key=lambda x: x[1], reverse=True)[:5]]
            top_clients = []
            for advisor in top_advisors:
                for pair in self.advisor_client_interactions:
                    adv, client = pair.split('|')
                    if adv == advisor and client not in top_clients:
                        top_clients.append(client)
                        if len(top_clients) >= 5:
                            break

            logging.info(f"{'Advisor/Client':<20} | " + " | ".join(f"{client:<15}" for client in top_clients))
            logging.info("-" * 20 + "-+-" + "-+-".join("-" * 15 for _ in top_clients))

            for advisor in top_advisors:
                row = f"{advisor:<20} | "
                for client in top_clients:
                    pair_key = f"{advisor}|{client}"
                    conv_count = self.advisor_client_interactions.get(pair_key, 0)
                    if conv_count == 0:
                        heat = " " * 15
                    else:
                        heat_chars = " ▂▃▄▅▆▇█"
                        max_pair_count = max(self.advisor_client_interactions.values())
                        heat_idx = min(7, int((conv_count / max_pair_count) * 8)) if max_pair_count > 0 else 0
                        heat = f"{conv_count} {heat_chars[heat_idx] * 5:<10}"
                    row += f"{heat:<15} | "
                logging.info(row)

            logging.info("\n----- Top Advisor-Client Pairs -----")
            for i, (pair, count) in enumerate(sorted_interactions[:10]):
                advisor, client = pair.split('|')
                percentage = (count / self.config.NUM_CONVERSATIONS) * 100
                bar = "█" * int(percentage / 5)
                logging.info(f"{i+1}. {advisor} - {client}: {count} conversations ({percentage:.1f}%) {bar}")

            self.write_advisor_client_interactions_to_file()

    def write_advisor_client_interactions_to_file(self):
        """Writes detailed advisor-client interaction data to a file."""
        try:
            interaction_path = Path(self.config.OUTPUT_DIR) / f"advisor_client_interactions_{self.run_id}.txt"
            with open(interaction_path, 'w') as f:
                f.write("===== ADVISOR-CLIENT INTERACTIONS =====\n")
                f.write(f"Total pairs: {len(self.advisor_client_interactions)}\n\n")

                advisor_interaction_counts = {}
                advisor_unique_clients = {}

                for pair, count in self.advisor_client_interactions.items():
                    advisor, client = pair.split('|')
                    advisor_interaction_counts[advisor] = advisor_interaction_counts.get(advisor, 0) + count
                    advisor_unique_clients.setdefault(advisor, set()).add(client)

                f.write("--- Advisor Activity Histogram ---\n")
                max_name_length = max(len(advisor) for advisor in advisor_interaction_counts.keys())
                max_count = max(advisor_interaction_counts.values())
                histogram_width = 50

                for advisor, count in sorted(advisor_interaction_counts.items(), key=lambda x: x[1], reverse=True):
                    unique_count = len(advisor_unique_clients[advisor])
                    bar_length = int((count / max_count) * histogram_width) if max_count > 0 else 0
                    bar = '█' * bar_length
                    percentage = (count / self.config.NUM_CONVERSATIONS) * 100
                    f.write(f"{advisor:<{max_name_length}} | {bar} {count} ({percentage:.1f}%), {unique_count} clients\n")

                clients_per_advisor_histogram = {}
                for advisor, clients in advisor_unique_clients.items():
                    client_count = len(clients)
                    clients_per_advisor_histogram[client_count] = clients_per_advisor_histogram.get(client_count, 0) + 1

                f.write("\n--- Distribution of Advisors by Client Count ---\n")
                for client_count in sorted(clients_per_advisor_histogram.keys()):
                    advisor_count = clients_per_advisor_histogram[client_count]
                    f.write(f"Advisors with {client_count} clients: {advisor_count}\n")

                client_advisor_counts = {}
                for pair in self.advisor_client_interactions:
                    advisor, client = pair.split('|')
                    client_advisor_counts.setdefault(client, set()).add(advisor)

                client_advisor_counts = {client: len(advisors) for client, advisors in client_advisor_counts.items()}
                advisors_per_client = {}
                for client, count in client_advisor_counts.items():
                    advisors_per_client[count] = advisors_per_client.get(count, 0) + 1

                f.write("\n--- Distribution of Clients by Advisor Count ---\n")
                for adv_count in sorted(advisors_per_client.keys()):
                    client_count = advisors_per_client[adv_count]
                    f.write(f"Clients with {adv_count} advisors: {client_count}\n")

                f.write("\n--- Complete Interaction Matrix ---\n")
                all_clients = sorted(list(set(client for pair in self.advisor_client_interactions.keys() for _, client in [pair.split('|')])))
                f.write("Advisor," + ",".join(all_clients) + "\n")

                for advisor in sorted(advisor_interaction_counts.keys()):
                    row = [advisor]
                    for client in all_clients:
                        pair_key = f"{advisor}|{client}"
                        conv_count = self.advisor_client_interactions.get(pair_key, 0)
                        row.append(str(conv_count))
                    f.write(",".join(row) + "\n")

                f.write("\n--- By Advisor ---\n")
                for advisor, count in sorted(advisor_interaction_counts.items(), key=lambda x: x[1], reverse=True):
                    unique_count = len(advisor_unique_clients[advisor])
                    f.write(f"{advisor}: {count} conversations, {unique_count} unique clients\n")
                    for client in sorted(advisor_unique_clients[advisor]):
                        pair_key = f"{advisor}|{client}"
                        conv_count = self.advisor_client_interactions.get(pair_key, 0)
                        f.write(f"  - {client}: {conv_count} conversations\n")

                f.write("\n--- By Client ---\n")
                client_conversation_counts = {}
                for pair, count in self.advisor_client_interactions.items():
                    _, client = pair.split('|')
                    client_conversation_counts[client] = client_conversation_counts.get(client, 0) + count

                for client, count in sorted(client_conversation_counts.items(), key=lambda x: x[1], reverse=True):
                    f.write(f"{client}: {count} total conversations\n")
                    for advisor in [adv for adv, cli in [pair.split('|') for pair in self.advisor_client_interactions if client in pair]]:
                        pair_key = f"{advisor}|{client}"
                        conv_count = self.advisor_client_interactions.get(pair_key, 0)
                        if conv_count > 0:
                            f.write(f"  - {advisor}: {conv_count} conversations\n")

                f.write("\n--- By Advisor-Client Pair ---\n")
                for pair, count in sorted(self.advisor_client_interactions.items(), key=lambda x: x[1], reverse=True):
                    advisor, client = pair.split('|')
                    f.write(f"{advisor} - {client}: {count}\n")

            logging.info(f"\nDetailed advisor-client interaction data written to: {interaction_path}")

        except Exception as e:
            logging.warning(f"Could not write advisor-client interaction file: {e}")

    def log_company_metrics(self):
        """Logs company targeting metrics."""
        if self.manifest_logger:
            try:
                company_metrics = {
                    'total_conversations': self.config.NUM_CONVERSATIONS,
                    'total_conversations_with_companies': 0,
                    'total_company_mentions': 0,
                    'company_mention_counts': Counter(),
                    'company_enabled_count': 0,
                    'conversations_with_companies': {
                        '1_company': 0,
                        '2_companies': 0,
                        '3+_companies': 0
                    }
                }

                manifest_log_file = None
                if hasattr(self.config, 'CONVERSATION_MANIFEST_DIR'):
                    manifest_dir = Path(self.config.CONVERSATION_MANIFEST_DIR)
                    manifest_log_file = manifest_dir / f"conversation_manifest_{self.run_id}.log"

                if manifest_log_file and manifest_log_file.exists():
                    with open(manifest_log_file, 'r') as f:
                        for line in f:
                            try:
                                data = json.loads(line.strip())
                                if data.get('company_targeting_enabled'):
                                    company_metrics['company_enabled_count'] += 1
                                    companies_found = data.get('companies_found', [])
                                    is_targeted_conversation = data.get('company_targeting_enabled', False)
                                    if is_targeted_conversation:
                                        if companies_found:
                                            company_metrics['total_conversations_with_companies'] += 1
                                            num_companies = len(companies_found)
                                            if num_companies == 1:
                                                company_metrics['conversations_with_companies']['1_company'] += 1
                                            elif num_companies == 2:
                                                company_metrics['conversations_with_companies']['2_companies'] += 1
                                            elif num_companies >= 3:
                                                company_metrics['conversations_with_companies']['3+_companies'] += 1
                                            for company in companies_found:
                                                company_metrics['company_mention_counts'][company] += 1
                                                company_metrics['total_company_mentions'] += 1
                            except json.JSONDecodeError:
                                continue

                    if company_metrics['company_enabled_count'] > 0:
                        logging.info("\n===== COMPANY TARGETING METRICS =====")
                        probability = self.generation_strategy.company_targeting.get("probability", 0.4) if hasattr(self.generation_strategy, 'company_targeting') else 0.4
                        logging.info(f"Company targeting configuration: probability={probability:.2f}, min_companies={self.generation_strategy.company_targeting.get('min_companies', 1)}, max_companies={self.generation_strategy.company_targeting.get('max_companies', 3)}")
                        enabled_pct = (company_metrics['company_enabled_count'] / company_metrics['total_conversations'] * 100)
                        logging.info(f"Conversations with company targeting enabled: {company_metrics['company_enabled_count']} ({enabled_pct:.1f}% of all conversations)")
                        expected_count = int(company_metrics['total_conversations'] * probability)
                        logging.info(f"Expected conversations with company targeting: {expected_count} ({probability*100:.1f}% of all conversations)")
                        success_pct = (company_metrics['total_conversations_with_companies'] / company_metrics['company_enabled_count'] * 100) if company_metrics['company_enabled_count'] > 0 else 0
                        overall_pct = (company_metrics['total_conversations_with_companies'] / company_metrics['total_conversations'] * 100)
                        logging.info(f"Conversations with at least one company mentioned: {company_metrics['total_conversations_with_companies']} ({success_pct:.1f}% success rate, {overall_pct:.1f}% of all conversations)")
                        logging.info("\n----- Company Count Distribution -----")
                        for company_count, count in company_metrics['conversations_with_companies'].items():
                            if company_metrics['total_conversations_with_companies'] > 0:
                                percentage = (count / company_metrics['total_conversations_with_companies']) * 100
                                bar = "█" * int(percentage / 5)
                                logging.info(f"{company_count}: {count} conversations ({percentage:.1f}%) {bar}")
                        if company_metrics['total_conversations_with_companies'] > 0:
                            avg_mentions = company_metrics['total_company_mentions'] / company_metrics['total_conversations_with_companies']
                            logging.info(f"\nAverage company mentions per conversation (when present): {avg_mentions:.2f}")
                            mention_counts = Counter()
                            for line in open(manifest_log_file, 'r'):
                                try:
                                    data = json.loads(line.strip())
                                    if data.get('has_company_mentions', False):
                                        count = data.get('company_mention_count', 0)
                                        mention_counts[count] += 1
                                except json.JSONDecodeError:
                                    continue
                            if mention_counts:
                                logging.info("\n----- Company Mentions Distribution -----")
                                for count in sorted(mention_counts.keys()):
                                    frequency = mention_counts[count]
                                    pct = (frequency / company_metrics['total_conversations_with_companies']) * 100 if company_metrics['total_conversations_with_companies'] > 0 else 0
                                    bar = "█" * int(pct / 5)
                                    logging.info(f"{count} mentions: {frequency} conversations ({pct:.1f}%) {bar}")
                        top_companies = company_metrics['company_mention_counts'].most_common(10)
                        if top_companies:
                            logging.info("\n----- Top 10 Company Mentions -----")
                            for company, count in top_companies:
                                percentage = (count / company_metrics['total_company_mentions']) * 100 if company_metrics['total_company_mentions'] > 0 else 0
                                bar = "█" * int(percentage / 5)
                                logging.info(f"{company}: {count} mentions ({percentage:.1f}%) {bar}")
                        not_found = company_metrics['company_enabled_count'] - company_metrics['total_conversations_with_companies']
                        if not_found > 0:
                            not_found_pct = (not_found / company_metrics['company_enabled_count']) * 100
                            logging.warning(f"\nTarget companies not found in {not_found} conversations ({not_found_pct:.1f}% miss rate)")
                            if not_found_pct > 20:
                                logging.warning(f"High miss rate may indicate prompt engineering issues or LLM compliance problems")
            except Exception as e:
                logging.warning(f"Error processing company metrics: {e}")

    def log_run_stats(self):
        logging.info("="*57)
        logging.info("\n" + "="*20 + " FINAL ANALYTICS " + "="*20)
        
        self.log_advisor_client_distribution()
        if self.manifest_logger:
            self.log_company_metrics()
        if self.all_timestamps:
            self.log_temporal_distribution()

        logging.info("="*57)