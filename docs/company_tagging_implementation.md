# Company Tagging Implementation Plan

## Overview
This document outlines the implementation plan for integrating the company tagging feature into the Chat Factory framework, based on our successful integration of Gemini 2.0 support.

## Implementation Status

1. ✅ **LLM Provider Update**:
   - Updated VertexAIProvider to support both Vertex AI SDK and GenAI SDK
   - Added auto-detection of SDK based on model name
   - Maintained backward compatibility with existing code
   - Added unit tests for the VertexAIProvider class

2. 🔄 **Next Implementation Steps**:
   - Implement CompanyTaggingTaxonomyStrategy class
   - Implement CompanyTaggingGenerationStrategy class 
   - Create company data CSV with variations and misspellings
   - Create few-shot examples specific to company tagging scenarios
   - Implement tracking mechanism for company mentions

## Component Design

### 1. CompanyTaggingTaxonomyStrategy

This class will extend the base TaxonomyStrategy and handle:
- Loading and parsing company data
- Selecting companies based on conversation type
- Creating conversation manifests with company targeting information

```python
class CompanyTaggingTaxonomyStrategy(BaseTaxonomyStrategy):
    """Strategy for selecting companies to be mentioned in conversations."""
    
    def __init__(self, config):
        super().__init__(config)
        self.company_data = self.load_company_data()
        self.conversation_type_metadata = self._extract_metadata_from_taxonomy()
    
    def load_company_data(self):
        """Load company data from CSV file."""
        company_data = []
        with open(self.config.COMPANY_DATA_FILE, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Process variations and misspellings
                variations = row.get('variations', '').split(';') if row.get('variations') else []
                misspellings = row.get('misspellings', '').split(';') if row.get('misspellings') else []
                
                company_data.append({
                    'name': row['name'],
                    'ticker': row.get('ticker', ''),
                    'sector': row.get('sector', ''),
                    'variations': variations,
                    'misspellings': misspellings,
                    'formal_name': row.get('formal_name', row['name']),
                    'metadata': row.get('other_metadata', '')
                })
        return company_data
    
    def _extract_metadata_from_taxonomy(self):
        """Extract company tagging metadata from taxonomy."""
        metadata = {}
        for conv_type, details in self.taxonomy.get('conversation_types', {}).items():
            if 'company_tagging' in details:
                metadata[conv_type] = details['company_tagging']
        return metadata
    
    def select_company_count(self, conversation_type):
        """Select number of companies to target based on conversation type."""
        metadata = self.conversation_type_metadata.get(conversation_type, {})
        company_count_options = metadata.get('company_count_options', [])
        
        if company_count_options:
            return random.choice(company_count_options)
        
        # Default fallback if not specified in taxonomy
        return random.randint(
            self.config.COMPANY_TARGETING.get('min_companies', 1),
            self.config.COMPANY_TARGETING.get('max_companies', 3)
        )
    
    def select_companies(self, conversation_type, count=None):
        """Select companies to be mentioned in a conversation."""
        if count is None:
            count = self.select_company_count(conversation_type)
        
        # Select companies - can be enhanced with industry or context awareness
        selected_companies = random.sample(self.company_data, min(count, len(self.company_data)))
        return selected_companies
    
    def create_manifest_blueprint(self, conversation_type, num_messages, **kwargs):
        """Create a blueprint for the conversation manifest."""
        # Check if company targeting is enabled
        targeting_enabled = self.conversation_type_metadata.get(
            conversation_type, {}).get('enabled', self.config.COMPANY_TARGETING.get('enabled', False))
        
        # Create basic blueprint
        blueprint = super().create_manifest_blueprint(conversation_type, num_messages, **kwargs)
        
        # Add company targeting information
        blueprint['company_targeting_enabled'] = targeting_enabled
        
        if targeting_enabled:
            # Apply targeting probability
            targeting_probability = self.conversation_type_metadata.get(
                conversation_type, {}).get('probability', self.config.COMPANY_TARGETING.get('probability', 0.5))
            
            should_target = random.random() < targeting_probability
            
            if should_target:
                # Select companies
                company_count = kwargs.get('company_count', self.select_company_count(conversation_type))
                selected_companies = self.select_companies(conversation_type, company_count)
                
                # Add to blueprint
                blueprint['key_companies'] = [
                    {
                        'name': company['name'],
                        'ticker': company['ticker'],
                        'sector': company['sector'],
                        'variations': company['variations'],
                        'formal_name': company['formal_name']
                    }
                    for company in selected_companies
                ]
            else:
                blueprint['key_companies'] = []
        else:
            blueprint['key_companies'] = []
            
        return blueprint
```

### 2. CompanyTaggingGenerationStrategy

This class will extend the base GenerationStrategy and handle:
- Incorporating company mentions into the prompt
- Post-processing to track company mentions in the generated text

```python
class CompanyTaggingGenerationStrategy(BaseGenerationStrategy):
    """Strategy for generating conversations with company mentions."""
    
    def construct_prompt(self, advisor_name, client_name, conversation_type, 
                        num_messages, manifest_blueprint):
        """Construct a prompt that includes instructions for company mentions."""
        # Start with base prompt
        prompt = super().construct_prompt(
            advisor_name, client_name, conversation_type, num_messages, manifest_blueprint)
        
        # Add company targeting instructions if enabled
        if manifest_blueprint.get('company_targeting_enabled', False) and manifest_blueprint.get('key_companies'):
            companies = manifest_blueprint['key_companies']
            
            company_section = "\n\nInclude mentions of the following companies in the conversation:\n"
            for company in companies:
                company_section += f"- {company['name']}"
                if company['ticker']:
                    company_section += f" ({company['ticker']})"
                if company['variations']:
                    company_section += f", variations: {', '.join(company['variations'])}"
                company_section += "\n"
            
            prompt += company_section
            prompt += "\nEnsure the company mentions feel natural and contextually appropriate to the conversation."
            
        return prompt
    
    def post_process_conversation(self, conversation, manifest_blueprint):
        """Post-process the conversation to track company mentions."""
        # Track which companies were mentioned
        if manifest_blueprint.get('company_targeting_enabled', False) and manifest_blueprint.get('key_companies'):
            mentioned_companies = []
            
            # Extract all text from the conversation
            all_text = " ".join([line['text'] for line in conversation])
            
            # Check for each company and its variations
            for company in manifest_blueprint['key_companies']:
                # Check main name
                if company['name'] in all_text:
                    mentioned_companies.append(company['name'])
                
                # Check ticker
                if company['ticker'] and company['ticker'] in all_text:
                    mentioned_companies.append(company['ticker'])
                
                # Check variations
                for variation in company['variations']:
                    if variation in all_text:
                        mentioned_companies.append(variation)
            
            # Add the tracked mentions to the conversation metadata
            conversation.company_mentions = mentioned_companies
        
        return conversation
```

### 3. Company Data CSV Format

Create a comprehensive CSV file with company data:

```csv
name,ticker,sector,variations,misspellings,formal_name,other_metadata
Apple,AAPL,Technology,"Apple Inc;APPL","Aple;Appel","Apple Inc.","Founded by Steve Jobs"
Microsoft,MSFT,Technology,"MSFT;MS","Microsft;Micosoft","Microsoft Corporation","Founded by Bill Gates"
Amazon,AMZN,E-commerce,"Amazon.com;AMZN","Amazn;Amazone","Amazon.com Inc.","Founded by Jeff Bezos"
```

### 4. Few-Shot Examples

Create company-specific few-shot examples in the following categories:
1. Trade discussions with company comparisons
2. Earnings report analysis
3. Market news
4. Investment strategy with specific companies
5. Product discussions

Example template:
```
advisor: Let's discuss Apple's recent earnings report. The company reported revenue of $95.7 billion, exceeding analyst expectations.
client: How does this compare to Microsoft's performance?
advisor: Microsoft (MSFT) reported stronger-than-expected earnings as well, with their cloud services division showing particular growth at 21% year-over-year.
client: Do you think AAPL's strong hardware sales will continue into the next quarter?
advisor: There are some concerns about supply chain constraints affecting Apple's production capacity, but their services revenue has been growing steadily to offset potential hardware slowdowns.
```

## Testing Strategy

1. **Unit Tests**:
   - `test_company_tagging_taxonomy_strategy.py`: Test selection logic, company count, and manifest creation
   - `test_company_tagging_generation_strategy.py`: Test prompt construction and post-processing

2. **Integration Tests**:
   - Test the full conversation generation pipeline with company tagging
   - Verify tracking and reporting of company mentions

3. **Evaluation Metrics**:
   - Company mention frequency per conversation
   - Distribution of companies across generated data
   - Usage of variations vs. standard names

## Documentation Updates

1. Update existing `company_tagging.md` with implementation details
2. Add examples of prompt construction with company instructions
3. Include metrics for analyzing company mention frequency

## Timeline

1. CompanyTaggingTaxonomyStrategy implementation: 2 days
2. CompanyTaggingGenerationStrategy implementation: 2 days
3. CSV data creation and few-shot examples: 1 day
4. Testing and refinements: 2 days
5. Documentation updates: 1 day

Total: 8 days