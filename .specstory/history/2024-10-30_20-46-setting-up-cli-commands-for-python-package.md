## SpecStory

## Setting Up CLI Commands for Python Package (10/30/2024, 8:46:31 PM)

_**User**_

When I upload this to pypi using build, I want certain commands to be installed. So for example `ragnosis create_index` should run the `create_index` command, `ragnosis ground_hypothesis` to run the `ground_hypothesis` command and so forth. Can you help me?

---

_**Assistant**_

I'll help you set up command-line entry points for your package. You'll need to modify your `pyproject.toml` file to include console scripts. These scripts will map commands to the functions in your code.

Looking at your code, you have several main commands defined in your command map:

```382:387:ragnosis/grounding.py
    command_map = {
        "create_index": create_vector_store,
        "ground_hypothesis" : ground_hypothesis_flow,
        "extract_hypothesis" : extract_hypothesis_flow,
        "evaluate_hypothesis": evaluate_hypothesis_flow,
    }
```


To make these commands available as CLI commands, you need to add a `[project.scripts]` section to your `pyproject.toml`. Here's how to modify it:

```toml:pyproject.toml
[project.scripts]
ragnosis = "ragnosis.grounding:main"
```

This will make the `ragnosis` command available, which will then use your existing argument parser to handle the subcommands.

Your current main function already handles the subcommands correctly:

```372:393:ragnosis/grounding.py
def main():
    # Set up logging configuration for console output
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    
    parser = get_parser()
    args = parser.parse_args()
    command_map = {
        "create_index": create_vector_store,
        "ground_hypothesis" : ground_hypothesis_flow,
        "extract_hypothesis" : extract_hypothesis_flow,
        "evaluate_hypothesis": evaluate_hypothesis_flow,
    }
    if args.command in command_map:
        command_args = {k : v for k, v in vars(args).items() if k != "command"}
        logging.info(f"Running command {args.command}")
        command_map[args.command](**command_args)
    else:
        parser.print_help()
```


With this setup, users will be able to run:
- `ragnosis create_index ...`
- `ragnosis ground_hypothesis ...`
- `ragnosis extract_hypothesis ...`
- `ragnosis evaluate_hypothesis ...`

After making these changes:

1. Update your package:
```bash
python -m build
```

2. Install your package:
```bash
pip install dist/ragnosis-0.1.2-py3-none-any.whl
```

The commands will then be available in your system PATH.

If you want to test this locally before publishing to PyPI, you can install your package in editable mode:
```bash
pip install -e .
```

This setup takes advantage of your existing argument parser and command structure while making it accessible as CLI commands. The commands will work exactly as defined in your `get_parser()` function:

```335:370:ragnosis/grounding.py
def get_parser():
    parser = argparse.ArgumentParser(description="Hypothesis compilation tool")
    
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

    return parser
```


---



---

