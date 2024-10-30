# LLM-retrieval based knowledge grounding
`ragnosis` contains tools for extracting hypotheses from scientific paper PDFs, extracting entities according to a user model, and grounding entities to ontology terms.


# Installation

This project relies on [langchain-rdf](https://github.com/vemonet/langchain-rdf) which should be installed separately.

To install langchain-rdf run:

```bash
pip install git+https://github.com/vemonet/langchain-rdf.git
```

`ragnosis` can be installed using pip:

```bash
pip install ragnosis
```

# Usage

## Hypothesis extraction

Hypotheses can be extracted from PDF files by running:

```bash
ragnosis extract_hypothesis path/to/paper.pdf [--model MODEL] [--temperature TEMP] [--out_file OUTPUT.txt]
```

## Creating ontology indices

Before grounding entities, vector store indices must be created from your ontology files. One or more OWL files can be provided to create a single index. `force_create` will overwrite an existing index. The index will be saved in the index_directory with the name `merged_index` unless `index_name` is specified:

```bash
ragnosis create_index index_directory path/to/ontology1.owl path/to/ontology2.owl [--force_create] [--index_name NAME]
```

## Hypothesis grounding

To ground entities in an input text to ontology terms:

```bash
ragnosis ground_hypothesis "your hypothesis text" path/to/yaml_map.yaml [--model MODEL] [--temperature TEMP] [--out_md OUTPUT.md]
```

The YAML file should map entity extraction categories to pre-built vector store indices, for example:

```yaml
bio_components: path/to/go_index
genes_proteins: path/to/protein_index
taxa: path/to/taxonomy_index
small_molecules: path/to/chebi_index
```

where the `path/to/go_index` refers to pre-built vector store files `path/to/go_index.faiss` and `path/to/go_index.pkl`. A sample YAML file can be found in the `ragnosis` repository.


## LLM Model Selection

For all commands that accept a `--model` parameter, you can specify:
- OpenAI models with prefix `openai/` (e.g., `openai/gpt-4o`)
- Ollama models with prefix `ollama/` (e.g., `ollama/llama3`)

The default model is `openai/gpt-4o`. When using OpenAI models, make sure to set your `OPENAI_API_KEY` environment variable before running the commands. For Ollama, make sure to have ollama installed and running.

## Output Files

Most commands support saving output in markdown format using the `--out_md` parameter. For hypothesis extraction, use `--out_file` to save the extracted hypothesis as plain text. If the out file parameter is not provided, no output file will be saved. The output will be printed to the console in all cases.

