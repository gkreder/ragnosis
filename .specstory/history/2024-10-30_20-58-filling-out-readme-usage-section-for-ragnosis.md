## SpecStory

## Filling Out README Usage Section for Ragnosis (10/30/2024, 8:58:55 PM)

_**User**_

Can you fill out the rest of the `#Usage` section in the README file based on the code?

---

_**Assistant**_

I'll help fill out the Usage section based on the code. Looking at the grounding.py file, particularly the command line parser section:

```335:368:ragnosis/grounding.py
def get_parser():
    parser = argparse.ArgumentParser(description="Ragnosis scientific knowledge grounding")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Subcommand for creating a vector store index from owl files
    create_index_parser = subparsers.add_parser("create_index", help="Create a new vector store index")
    create_index_parser.add_argument("index_dir", type=Path, help="Path to save the vector store index")
    create_index_parser.add_argument("owl_files", type=Path, nargs="+", help="Path to owl files to create the index from")
    create_index_parser.add_argument("--force_create", action="store_true", help="Force create the index even if it already exists")
    create_index_parser.add_argument("--index_name", type=str, default="merged_index", help="Name of the output merged index")
    # Subcommand for running the hypothesis grounding flow
    ground_hypothesis_parser = subparsers.add_parser("ground_hypothesis", help="Translates a hypothesis into a prolog program")
    ground_hypothesis_parser.add_argument("input", type=str, help="User input")
    ground_hypothesis_parser.add_argument("yaml_map_path", type=Path, help="Path to the YAML map of vector stores")
    ground_hypothesis_parser.add_argument("--model", type=str, default="openai/gpt-4o", help="LLM model to use for the experiment plan")
    ground_hypothesis_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
    ground_hypothesis_parser.add_argument("--out_md", type=Path, default=None, help="Output file to save the results (.md)")

    # Subcommand for running the hypothesis extraction flow
    hypothesis_extraction_parser = subparsers.add_parser("extract_hypothesis", help="Extracts a hypothesis from a paper PDF")
    hypothesis_extraction_parser.add_argument("pdf_path", type=Path, help="Path to the PDF file")
    hypothesis_extraction_parser.add_argument("--model", type=str, default="openai/gpt-4o", help="LLM model to use for the experiment plan")
    hypothesis_extraction_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
    hypothesis_extraction_parser.add_argument("--out_file", type=Path, default=None, help="Optional file to save the extracted hypothesis (.txt)")

    # Add new subcommand for evaluating hypotheses
    evaluate_hypothesis_parser = subparsers.add_parser("evaluate_hypothesis", help="Evaluates a test hypothesis against a reference hypothesis")
    evaluate_hypothesis_parser.add_argument("reference_hypothesis", type=str, help="Reference hypothesis")
    evaluate_hypothesis_parser.add_argument("test_hypothesis", type=str, help="Test hypothesis")
    evaluate_hypothesis_parser.add_argument("--model", type=str, default="openai/gpt-4o", help="LLM model to use for the evaluation")
    evaluate_hypothesis_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
    evaluate_hypothesis_parser.add_argument("--out_md", type=Path, default=None, help="Optional file to save the evaluation results (.md)")
```


Here's the expanded Usage section for the README:

```markdown:README.md
# Usage

## Hypothesis extraction

Hypotheses can be extracted from PDF files by running:

```bash
ragnosis extract_hypothesis path/to/paper.pdf [--model MODEL] [--temperature TEMP] [--out_file OUTPUT.txt]
```

## Creating ontology indices

Before grounding entities, you need to create vector store indices from your ontology files:

```bash
ragnosis create_index index_directory path/to/ontology1.owl path/to/ontology2.owl [--force_create] [--index_name NAME]
```

## Hypothesis grounding 

To ground entities in a hypothesis to ontology terms:

```bash
ragnosis ground_hypothesis "your hypothesis text" path/to/vector_stores.yaml [--model MODEL] [--temperature TEMP] [--out_md OUTPUT.md]
```

The YAML file should map entity types to vector store indices, for example:

```yaml
bio_components: path/to/go_index
genes_proteins: path/to/protein_index
taxa: path/to/taxonomy_index
small_molecules: path/to/chebi_index
```

## Hypothesis evaluation

To evaluate how well a test hypothesis matches a reference hypothesis:

```bash
ragnosis evaluate_hypothesis "reference hypothesis" "test hypothesis" [--model MODEL] [--temperature TEMP] [--out_md OUTPUT.md]
```

### Model Selection

For all commands that accept a `--model` parameter, you can specify:
- OpenAI models with prefix `openai/` (e.g., `openai/gpt-4`)
- Ollama models with prefix `ollama/` (e.g., `ollama/llama2`)

The default model is `openai/gpt-4`. When using OpenAI models, make sure to set your `OPENAI_API_KEY` environment variable.

### Output Formats

Most commands support saving output in markdown format using the `--out_md` parameter. For hypothesis extraction, use `--out_file` to save the extracted hypothesis as plain text.

---



---

