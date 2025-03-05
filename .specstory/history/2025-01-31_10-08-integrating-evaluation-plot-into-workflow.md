## SpecStory

## Integrating Evaluation Plot into Workflow (1/31/2025, 10:08:45 AM)

_**User**_

See this evaluation plot file? I want to incorporate this into the workflow so I can call on the output of a workflow like I do the other parts dynamically on a new run

---

_**Assistant**_

I'll help you modify the code to make it work as part of a workflow. The main changes needed are to make the plotting function more flexible and integrate it with workflow outputs. Here's how we can modify the code:

```python:ragnosis/evaluation_plot.py
// ... existing code ...

def plot_protocol_evaluations(eval_dir: str | Path, output_html: str | Path = "protocol_evaluations.html", open_browser: bool = True):
    """
    Create an interactive plot of protocol evaluation scores.
    
    Args:
        eval_dir: Directory containing the evaluation JSON files and protocol markdown files
        output_html: Path to save the interactive HTML plot
        open_browser: Whether to automatically open the plot in a browser
    """
    eval_dir = Path(eval_dir)
    output_html = Path(output_html)
    scores = []
    protocols = []
    eval_files = []
    
    # Collect all evaluation files
    for eval_file in sorted(eval_dir.glob("*_evaluation.json")):
        protocol_file = eval_dir / f"{eval_file.stem.split('_')[0]}_protocol.md"
        
        if not protocol_file.exists():
            print(f"Warning: Protocol file not found for {eval_file}")
            continue
            
        with open(eval_file) as f:
            data = json.load(f)
            
        scores.append({
            'clarity': data['clarity_score'],
            'completeness': data['completeness_score'],
            'sensibility': data['sensibility_score'],
            'hypothesis': eval_file.stem.split('_')[0]
        })
        protocols.append(str(protocol_file))
        eval_files.append(str(eval_file))

    if not scores:
        print("No evaluation files found to plot")
        return None

    // ... existing code ...

    # Write the HTML file
    output_html.parent.mkdir(parents=True, exist_ok=True)
    with open(output_html, 'w') as f:
        f.write(html_content)
    
    print(f"Plot saved to {output_html}")
    if open_browser:
        webbrowser.open(str(output_html))
    
    return output_html

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create an interactive plot of protocol evaluation scores")
    parser.add_argument("eval_dir", help="Directory containing evaluation JSONs and protocol markdown files")
    parser.add_argument("--output", default="protocol_evaluations.html", help="Output HTML file path")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    
    args = parser.parse_args()
    plot_protocol_evaluations(args.eval_dir, args.output, not args.no_browser)
```

Key changes made:
1. Added type hints to support both string and Path objects for input parameters
2. Added `open_browser` parameter to control whether the browser opens automatically
3. Added error handling for when no evaluation files are found
4. Added warning message when protocol files are missing
5. Ensure output directory exists before writing file
6. Return the output path for workflow integration
7. Added `--no-browser` CLI option
8. Made Path handling more robust

Now you can use this in a workflow by importing and calling the function with appropriate parameters. The function will return the path to the generated HTML file, which can be used in subsequent workflow steps.

To use this in a workflow, you would typically do something like:

```python
from ragnosis.evaluation_plot import plot_protocol_evaluations

def your_workflow():
    # ... other workflow steps ...
    
    # Generate the plot
    plot_path = plot_protocol_evaluations(
        eval_dir="path/to/evaluations",
        output_html="output/plots/protocol_evaluations.html",
        open_browser=False  # Typically False in workflow context
    )
    
    # Use plot_path in subsequent steps if needed
    if plot_path:
        # do something with the plot
        pass
```

---

_**User**_

Ok great, now add a plot evaluation step to the workflow in @1-15.sh 

---

_**Assistant**_

I'll add the plotting step to the workflow. Since we want to generate the plot after all evaluations are complete, we'll add it after the loop:

```shell:/Users/gkreder/scripts/medium-boat/2025-01-31_tests/1-15.sh
// ... existing code ...

done

# Step 4: Generate evaluation plot
echo "Generating evaluation plot..."
/Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.evaluation_plot \
"$OUTPUT_DIR" \
--output "$OUTPUT_DIR/protocol_evaluations.html" \
--no-browser

echo "All hypotheses processed, protocols generated, evaluated, and plotted successfully!"
```

Key changes:
1. Added a new step after the loop to generate the evaluation plot
2. Uses the same `OUTPUT_DIR` where all the evaluation JSONs and protocol files are stored
3. Saves the plot in the same output directory
4. Added `--no-browser` flag since this is running in a script
5. Updated the final success message to include the plotting step

The plot will be generated using all the evaluation files present in the output directory, making it easy to visualize the results across all hypotheses that were processed.

---



---

