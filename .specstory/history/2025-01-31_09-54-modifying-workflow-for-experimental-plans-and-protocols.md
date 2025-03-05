## SpecStory

## Modifying Workflow for Experimental Plans and Protocols (1/31/2025, 9:54:09 AM)

_**User**_

Take a look at this file and the workflow in @1-5.sh The older workflow takes in hypotheses in .txt format and generates experimental plans. The newer workflow takes the output of this and produces experimental protocols. I'd like to modify this newer flow file to do everything from the start. Generate experimental plans then turn into protocols. Can we modify accordingly?

---

_**Assistant**_

I'll help modify the newer workflow to incorporate both steps: generating experimental plans from hypotheses and then creating protocols from those plans. Here's the modified version:

```shell:/Users/gkreder/scripts/medium-boat/2025-01-31_tests/1-5.sh
cd /Users/gkreder/ragnosis
export PYTHONPATH=$PYTHONPATH:/Users/gkreder/ragnosis

# Process hypotheses 1 through 15
for i in {1..15}; do
    echo "Processing hypothesis $i..."
    
    # Define input and output paths
    hypothesis_file="/Users/gkreder/org/data/B2/46CD05-23D2-4C80-AD16-F7F01FEBF601/individual_extracted_hypotheses/$i.txt"
    experiment_plan="/Users/gkreder/scripts/medium-boat/2025-01-30_tests/output/${i}_experiment_plan.md"
    protocol_md="/Users/gkreder/scripts/medium-boat/2025-01-30_tests/output/${i}_protocol.md"
    eval_json="/Users/gkreder/scripts/medium-boat/2025-01-30_tests/output/${i}_evaluation.json"
    
    # Create output directory if it doesn't exist
    output_dir=$(dirname "$experiment_plan")
    mkdir -p "$output_dir"
    
    # Check if input file exists
    if [ ! -f "$hypothesis_file" ]; then
        echo "Warning: Input file $hypothesis_file does not exist. Skipping..."
        continue
    fi
    
    # Read the content of the file into a variable
    hypothesis=$(cat "$hypothesis_file")
    
    # Step 1: Generate experiment plan from hypothesis
    echo "Generating experiment plan for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_experiment_plan \
    "$hypothesis" \
    "/Users/gkreder/scripts/medium-boat/2024-12-11_abbi-test/index_mapping.yaml" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_md "$experiment_plan"
    
    # Step 2: Generate protocol from experiment plan
    echo "Generating protocol for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_protocol \
    "$experiment_plan" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_md "$protocol_md"
    
    # Step 3: Evaluate the generated protocol
    echo "Evaluating protocol for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.evaluate_protocol \
    "$protocol_md" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_json "$eval_json"
    
    echo "Completed processing and evaluation for hypothesis $i"
    echo "----------------------------------------"
done

echo "All hypotheses processed, protocols generated, and evaluated successfully!"
```

Key changes made:
1. Combined both workflows into a single script
2. Added the experiment plan generation step before protocol generation
3. Updated the file paths to maintain a clear progression: hypothesis → experiment plan → protocol → evaluation
4. Fixed the model name from "gpt-4o" to "gpt-4"
5. Updated the echo messages to reflect the multi-step process
6. Maintained the same output directory structure from your newer workflow

The script now:
1. Reads the hypothesis from a text file
2. Generates an experiment plan
3. Creates a protocol from that plan
4. Evaluates the protocol
5. Saves all outputs in the specified directory structure

---

_**User**_

Excellent, now a minor modification. Can we have the output directory be a variable since I don't have to manually change it so many times in the script text?

---

_**Assistant**_

Here's the modified version with the output directory as a variable:

```shell:/Users/gkreder/scripts/medium-boat/2025-01-31_tests/1-5.sh
cd /Users/gkreder/ragnosis
export PYTHONPATH=$PYTHONPATH:/Users/gkreder/ragnosis

# Define output directory
OUTPUT_DIR="/Users/gkreder/scripts/medium-boat/2025-01-30_tests/output"

# Process hypotheses 1 through 15
for i in {1..15}; do
    echo "Processing hypothesis $i..."
    
    # Define input and output paths
    hypothesis_file="/Users/gkreder/org/data/B2/46CD05-23D2-4C80-AD16-F7F01FEBF601/individual_extracted_hypotheses/$i.txt"
    experiment_plan="$OUTPUT_DIR/${i}_experiment_plan.md"
    protocol_md="$OUTPUT_DIR/${i}_protocol.md"
    eval_json="$OUTPUT_DIR/${i}_evaluation.json"
    
    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"
    
    # ... existing code ...
    if [ ! -f "$hypothesis_file" ]; then
        echo "Warning: Input file $hypothesis_file does not exist. Skipping..."
        continue
    fi
    
    hypothesis=$(cat "$hypothesis_file")
    
    # Step 1: Generate experiment plan from hypothesis
    echo "Generating experiment plan for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_experiment_plan \
    "$hypothesis" \
    "/Users/gkreder/scripts/medium-boat/2024-12-11_abbi-test/index_mapping.yaml" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_md "$experiment_plan"
    
    # Step 2: Generate protocol from experiment plan
    echo "Generating protocol for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_protocol \
    "$experiment_plan" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_md "$protocol_md"
    
    # Step 3: Evaluate the generated protocol
    echo "Evaluating protocol for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.evaluate_protocol \
    "$protocol_md" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_json "$eval_json"
    
    echo "Completed processing and evaluation for hypothesis $i"
    echo "----------------------------------------"
done

echo "All hypotheses processed, protocols generated, and evaluated successfully!"
```

Changes made:
1. Added `OUTPUT_DIR` variable at the top of the script
2. Replaced all instances of the hardcoded output directory with `$OUTPUT_DIR`
3. Simplified the `mkdir -p` command since we now have the directory in a variable
4. Removed the now-redundant `output_dir=$(dirname "$experiment_plan")` line

This makes it much easier to change the output location - you only need to modify the `OUTPUT_DIR` variable at the top of the script.

---

_**User**_

Nice I really like that. Let's do the same for the hypothesis input file directory and the location of hte index mapping file

---

_**Assistant**_



Here's the version with all common paths defined as variables at the top:

```shell:/Users/gkreder/scripts/medium-boat/2025-01-31_tests/1-5.sh
cd /Users/gkreder/ragnosis
export PYTHONPATH=$PYTHONPATH:/Users/gkreder/ragnosis

# Define directories and common paths
OUTPUT_DIR="/Users/gkreder/scripts/medium-boat/2025-01-30_tests/output"
HYPOTHESIS_DIR="/Users/gkreder/org/data/B2/46CD05-23D2-4C80-AD16-F7F01FEBF601/individual_extracted_hypotheses"
INDEX_MAPPING="/Users/gkreder/scripts/medium-boat/2024-12-11_abbi-test/index_mapping.yaml"

# Process hypotheses 1 through 15
for i in {1..15}; do
    echo "Processing hypothesis $i..."
    
    # Define input and output paths
    hypothesis_file="$HYPOTHESIS_DIR/$i.txt"
    experiment_plan="$OUTPUT_DIR/${i}_experiment_plan.md"
    protocol_md="$OUTPUT_DIR/${i}_protocol.md"
    eval_json="$OUTPUT_DIR/${i}_evaluation.json"
    
    # Create output directory if it doesn't exist
    mkdir -p "$OUTPUT_DIR"
    
    # Check if input file exists
    if [ ! -f "$hypothesis_file" ]; then
        echo "Warning: Input file $hypothesis_file does not exist. Skipping..."
        continue
    fi
    
    hypothesis=$(cat "$hypothesis_file")
    
    # Step 1: Generate experiment plan from hypothesis
    echo "Generating experiment plan for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_experiment_plan \
    "$hypothesis" \
    "$INDEX_MAPPING" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_md "$experiment_plan"
    
    # Step 2: Generate protocol from experiment plan
    echo "Generating protocol for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_protocol \
    "$experiment_plan" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_md "$protocol_md"
    
    # Step 3: Evaluate the generated protocol
    echo "Evaluating protocol for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.evaluate_protocol \
    "$protocol_md" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_json "$eval_json"
    
    echo "Completed processing and evaluation for hypothesis $i"
    echo "----------------------------------------"
done

echo "All hypotheses processed, protocols generated, and evaluated successfully!"
```

Changes made:
1. Added `HYPOTHESIS_DIR` variable for the input hypothesis files location
2. Added `INDEX_MAPPING` variable for the index mapping file location
3. Updated the path references in the script to use these variables
4. All common paths are now defined at the top of the script for easy modification

This makes the script much more maintainable - you can now easily change any of these paths by modifying just the variables at the top of the script.

---



---

