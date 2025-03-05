## SpecStory

## Modifying Script for TSV Input Processing (2/28/2025, 1:47:39 PM)

_**User**_

Take a look at this flow and modify it to now take input from a tsv file (like the one in the context @carl_hypotheses.tsv ). For each one of the hypotheses in these , it should call the generate experiment plan, generate protocol, and evaluate protocol flow. Use the key column as the output prefix. And add the equipment file using the new input tsv capability in the generate_experimental_plan_flow in @grounding.py 

---

_**Assistant**_

I'll help you modify the script to process hypotheses from the TSV file. Here's how we should update the script:

````bash:/Users/gkreder/scripts/medium-boat/2025-02-28_carl-update-equipment-list/1-5.sh
cd /Users/gkreder/ragnosis
export PYTHONPATH=$PYTHONPATH:/Users/gkreder/ragnosis

# Set OpenAI API key from .env file
export OPENAI_API_KEY=$(grep OPENAI_API_KEY /Users/gkreder/ragnosis/.env | cut -d '=' -f2)

# Define directories and common paths
OUTPUT_DIR="/Users/gkreder/scripts/medium-boat/2025-02-28_carl-update-equipment-list/carl_output"
HYPOTHESIS_TSV="/Users/gkreder/scripts/medium-boat/2025-02-28_carl-update-equipment-list/carl_hypotheses.tsv"
INDEX_MAPPING="/Users/gkreder/scripts/medium-boat/2024-12-11_abbi-test/index_mapping.yaml"

# Read and process each hypothesis from the TSV file
while IFS=$'\t' read -r key hypothesis context equipment_file || [ -n "$key" ]; do
    # Skip header row
    if [ "$key" = "Key" ]; then
        continue
    fi
    
    echo "Processing hypothesis with key: $key..."
    
    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"

    # Step 1: Generate experiment plan from hypothesis
    echo "Generating experiment plan..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_experiment_plan \
    "$hypothesis" \
    "$INDEX_MAPPING" \
    --context "$context" \
    --equipment_tsv "$equipment_file" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --output_folder "$OUTPUT_DIR" \
    --prefix "$key"

    # Step 2: Generate protocol from experiment plan
    echo "Generating protocol..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_protocol \
    "$OUTPUT_DIR/${key}_experiment_plan.json" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --output_folder "$OUTPUT_DIR" \
    --prefix "$key"

    # Step 3: Evaluate the generated protocol
    echo "Evaluating protocol..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.evaluate_protocol \
    "$OUTPUT_DIR/${key}_protocol.json" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_json "$OUTPUT_DIR/${key}_evaluation.json"

    echo "Completed processing and evaluation for key: $key"
    echo "----------------------------------------"
done < "$HYPOTHESIS_TSV"

echo "All hypotheses processed, protocols generated, and evaluated successfully!"
````

Key changes made:

1. Added `HYPOTHESIS_TSV` variable pointing to the carl_hypotheses.tsv file
2. Replaced the for loop with a while loop that reads the TSV file line by line
3. Used IFS=$'\t' to properly split on tab characters
4. Extracted key, hypothesis, context, and equipment_file from each line
5. Used the key as the prefix for output files
6. Added the equipment_tsv parameter to the generate_experiment_plan command
7. Skipped the header row of the TSV file

The script will now:
1. Read each hypothesis from the TSV file
2. Use the key column as the prefix for output files
3. Pass the hypothesis text and context to generate_experiment_plan
4. Include the equipment file specified in the TSV
5. Generate the protocol and evaluation for each hypothesis
6. Save all outputs in the specified output directory with the key as prefix

This should process all hypotheses in the TSV file sequentially, maintaining the same workflow for each one but now with the equipment file integration.

---

_**User**_

Ok to clarify, the header in the tsv file looks similar but has cases and no underscores, is that ok?

---

_**Assistant**_

Looking at the TSV file header from the context:

```
Key	Hypothesis	Context	Equipment File
```

Yes, this is perfectly fine! The bash script's `while IFS=$'\t' read -r key hypothesis context equipment_file` will still work correctly with this header format. The variable names in the script are just for our internal reference and don't need to match the header names exactly. The important things are:

1. The order of columns matches (Key, Hypothesis, Context, Equipment File)
2. The fields are tab-separated
3. We're skipping the header row with the check `if [ "$key" = "Key" ]`

So there's no need to modify the script - it will work

---



---

