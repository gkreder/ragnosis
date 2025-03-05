## SpecStory

## TSV Parsing for Experiment Plan (2/12/2025, 9:50:52 AM)

_**User**_

Take a look at `generate_experiment_plan_flow`. I want to be able to pass in an input tsv file with three columns "Category", "Item Name", and "Model/Manufacturer". This should get parsed into the `input_text` as a separate sections for Equipment and Reagents that can be bullet point lists where each bullet point looks like "- Autoclave : Amsco 250LS (Steris)". Where autoclave here is the item name, and amsco 250LS (Steris) is the model/manufacturer and this would appear in the equipment list since it was tagged as "Equipment" in category. If other tags besides equipment and reagent show up in the category column, these sections should be included appropriately in the input text

---

_**Assistant**_

I'll help you modify the `generate_experiment_plan_flow` function to handle TSV input. Here's how we can update it:

````python:ragnosis/grounding.py
// ... existing code ...

def parse_equipment_tsv(tsv_path: Path) -> str:
    """Parse a TSV file containing equipment/reagent information into formatted sections.
    
    Expected TSV format:
    Category    Item Name    Model/Manufacturer
    
    Returns:
        Formatted string with sections for each category
    """
    if not tsv_path.exists():
        return ""
        
    # Read TSV and group by category
    categories = {}
    with open(tsv_path, 'r') as f:
        # Skip header
        next(f)
        for line in f:
            category, item, model = line.strip().split('\t')
            if category not in categories:
                categories[category] = []
            categories[category].append(f"- {item} : {model}")
    
    # Format into sections
    sections = []
    for category in sorted(categories.keys()):
        sections.extend([
            f"# {category}",
            "",
            "\n".join(categories[category]),
            ""
        ])
    
    return "\n".join(sections)

def generate_experiment_plan_flow(
    hypothesis: str,
    yaml_map_path: Path,
    model: str,
    output_folder: Path,
    prefix: str,
    context: str = None,
    equipment_tsv: Path = None,
    temperature: float = 0.0,
) -> Tuple[str, ExperimentPlan]:
    """Main flow to generate and ground an experiment plan
    
    Args:
        hypothesis: Input hypothesis text
        yaml_map_path: Path to YAML map of vector stores
        model: LLM model to use
        output_folder: Folder to save outputs
        prefix: Prefix for output files
        context: Optional additional context for the hypothesis
        equipment_tsv: Optional path to TSV file with equipment/reagent information
        temperature: Temperature for LLM model
        
    Returns:
        Tuple of (markdown output string, experiment plan object)
    """
    
    # Create output directory if it doesn't exist
    output_folder = Path(output_folder)
    if not output_folder.exists():
        output_folder.mkdir(parents=True)
    
    # Define output paths
    out_md = output_folder / f"{prefix}_experiment_plan.md"
    out_pdf = output_folder / f"{prefix}_experiment_plan.pdf"
    out_json = output_folder / f"{prefix}_experiment_plan.json"
    
    # Combine hypothesis, context, and equipment info if provided
    sections = ["# Hypothesis", "", hypothesis, ""]
    
    if context:
        sections.extend(["# Context", "", context, ""])
    
    if equipment_tsv:
        equipment_sections = parse_equipment_tsv(equipment_tsv)
        if equipment_sections:
            sections.append(equipment_sections)
    
    input_text = "\n".join(sections)
    
    # Rest of the function remains the same...
// ... existing code ...

def get_parser():
    parser = get_parser()
    # ... existing parser code ...
    
    # Update experiment plan parser to include equipment_tsv
    experiment_plan_parser.add_argument("--equipment_tsv", type=Path, help="Optional TSV file containing equipment and reagent information")
    
    # ... rest of parser code ...
````

This modification:

1. Adds a new `parse_equipment_tsv` helper function that reads a TSV file and formats its contents into sections based on the categories.

2. Updates `generate_experiment_plan_flow` to accept an optional `equipment_tsv` parameter and incorporate the parsed equipment information into the input text.

3. Updates the argument parser to accept the new `--equipment_tsv` parameter.

The TSV file should be formatted like this:
```tsv
Category	Item Name	Model/Manufacturer
Equipment	Autoclave	Amsco 250LS (Steris)
Reagents	PBS Buffer	Sigma-Aldrich P4417
Equipment	Centrifuge	Eppendorf 5424R
```

When processed, this would appear in the input text as:
```
# Hypothesis

your hypothesis here

# Equipment

- Autoclave : Amsco 250LS (Steris)
- Centrifuge : Eppendorf 5424R

# Reagents

- PBS Buffer : Sigma-Aldrich P4417
```

You can then use it from the command line like:
```bash
python -m ragnosis.grounding generate_experiment_plan \
    "Your hypothesis" \
    path/to/yaml_map.yaml \
    --equipment_tsv path/to/equipment.tsv \
    --output_folder output/ \
    --prefix test
```

---



---

