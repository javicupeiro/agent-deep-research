# Agentic Deep Research

A deep-research architecture that decomposes user queries into scoped subtasks, orchestrates specialized agents for parallel investigation, and aggregates the results into a unified, structured report.

## Architecture
```mermaid
flowchart LR
    %% Nodes 
    U[User query]:::plainText
    RP[Research<br>Plan]:::Box
    SS[Split<br>subtasks]:::Box
    RC1[Research<br>Coordinator]:::Box
    SA1[subagent_1]:::Box
    SA2[subagent_2]:::Box
    SA3[...]:::Box
    SA4[subagent_n]:::Box
    RC2[Research<br>Coordinator]:::Box
    R[Result]:::plainText

    %% Connections
    U --> RP
    RP --> SS
    SS --> RC1

    RC1 --> SA1
    RC1 --> SA2
    RC1 --> SA3
    RC1 --> SA4

    SA1 --> RC2
    SA2 --> RC2
    SA3 --> RC2
    SA4 --> RC2

    RC2 --> R
```


## Set-up
### Use UV to handle dependencies and venv 

1. ```uv init```

2. ```uv venv```

3. ```source . venv/bin/activate```

4. ```uv add 'smolagents[mcp]' firecrawl huggingface_hub```

### Add your API keys to your ```.env```file:
```
HF_TOKEN="your_hf_token"
FIRECRAWL_API_KEY="your_firecrawl_api_key"
```
