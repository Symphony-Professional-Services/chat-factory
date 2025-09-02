# Company Tagging Strategies README

This directory contains the concrete strategy implementations for the **company tagging** use case. These strategies are designed to generate synthetic conversations that are rich with company mentions, which is useful for training and evaluating named entity recognition (NER) models.

## Overview

The primary goal of the company tagging strategies is to ensure that the generated conversations include specific company names, tickers, and other variations in a natural and contextually relevant manner. This is achieved through specialized implementations of the `TaxonomyStrategy` and `GenerationStrategy`.

## `CompanyTaggingTaxonomyStrategy`

*   **Purpose:** This strategy is responsible for handling the `company_tagging.json` taxonomy file.
*   **Key Responsibilities:**
    *   **Loading the Taxonomy:** It loads the taxonomy file, which includes not only conversation topics but also a `conversation_types` section with detailed settings for company tagging.
    *   **Parsing Conversation Types:** It parses the `conversation_types` section to understand the specific requirements for each type of conversation, such as the probability of including company mentions and the number of companies to include.
    *   **Topic Selection:** It selects a topic for each conversation from the taxonomy, which is then used to guide the content of the conversation.

## `CompanyTaggingGenerationStrategy`

*   **Purpose:** This strategy is responsible for constructing the prompts that instruct the LLM to generate conversations with company mentions.
*   **Key Responsibilities:**
    *   **Company Selection:** It randomly selects a set of companies from the provided company data file (`data/companies.csv`) based on the settings in the taxonomy.
    *   **Prompt Construction:** It constructs a detailed prompt that explicitly instructs the LLM to include the selected companies in the conversation. The prompt also provides guidance on how to mention the companies naturally, using a mix of names, tickers, and other variations.
    *   **Response Processing:** It processes the LLM's response to extract the generated conversation and format it into the standard data structure.

## How it Works

1.  The `CompanyTaggingTaxonomyStrategy` loads the `company_tagging.json` taxonomy and selects a topic.
2.  The `CompanyTaggingGenerationStrategy` creates a manifest blueprint for the conversation, which includes a list of companies to be mentioned.
3.  The `CompanyTaggingGenerationStrategy` then constructs a prompt that includes the selected topic and the list of companies, along with detailed instructions on how to include them in the conversation.
4.  The LLM generates a conversation based on the prompt.
5.  The `CompanyTaggingGenerationStrategy` processes the LLM's response and creates the final conversation object, which includes a `company_mentions` field with the list of companies that were included in the conversation.
