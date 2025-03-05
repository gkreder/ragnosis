## SpecStory

## Modifying Experimental Plan and Protocol Workflow (2/12/2025, 3:37:17 PM)

_**User**_

Take a look at the grounding workflow, specifically for generating an experimental plan and for generating an experimental protocol. I want experimental plan to take an output folder and a prefix (e.g. /Users/gkreder/Downloads/output and "1_plan") and I want it to save (1) an output md (2) an output pdf and (3) a json serialized version of the output plan. The generate protocol flow should then take in the serialized json of the experimental plan as input and produce a generated protocol accordingly. It should also take in a output folder and prefix as well and produce a md output, a pdf output, and a serialized json (as well as whatever other outputs are currently being produced)

---

_**Assistant**_

I'll help modify the grounding workflow to accommodate these changes. Let me first explain what I'll do:

1. Modify `generate_experiment_plan_flow` to:
   - Take output folder and prefix parameters
   - Save MD, PDF, and JSON serialized plan
   - Return both the markdown string and the experiment plan object

2. Modify `generate_protocol_flow` to:
   - Take a serialized JSON plan as input instead of markdown
   - Take output folder and prefix parameters
   - Save MD, PDF, and JSON serialized protocol

Let me make these changes:

---

_****_

```diff
  import markdown
  import pdfkit
- from typing import Dict
+ from typing import Dict, Tuple
  import yaml
+ import json
  
  # Workaround for the OpenMP forking error - needs more permanent fix
      yaml_map_path: Path,
      model: str,
+     output_folder: Path,
+     prefix: str,
      temperature: float = 0.0,
-     out_md: Path = None,
- ) -> str:
-     """Main flow to generate and ground an experiment plan"""
-     
-     # First generate the restated hypothesis
-     llm = get_llm(model, kwargs={'temperature': temperature})
-     
- #     restate_template = """\
- # Clearly state the hypothesis, independent and dependent variables, any expected correlations,
- # interactions, or causal relationships
- 
- # - Enhance Context-Gathering: Summarize known biological mechanisms, previous related
- # studies, and whether prior experiments have yielded conflicting or inconclusive results.
- # Highlight key knowledge gaps this research aims to address.
- 
- # - Clarify Sensitivity Requirements: Define acceptable detection limits, dynamic range, or
- # measurement scales (e.g., molecular, subcellular, cellular, population level) necessary to
- # validate the hypothesis.
- 
- # - Identify Potential Challenges: List anticipated technical or methodological challenges based
- # on prior research in this domain (e.g., detection limitations, sample constraints, equipment
- # availability).
- 
- # Original hypothesis: ```{hypothesis}```
- 
- # Restated hypothesis:"""
-     
- #     restate_prompt = PromptTemplate(
- #         template=restate_template,
- #         input_variables=["hypothesis"]
- #     )
-     
- #     restate_chain = restate_prompt | llm | StrOutputParser()
- #     restated_hypothesis = restate_chain.invoke({"hypothesis": input})
+ ) -> Tuple[str, ExperimentPlan]:
+     """Main flow to generate and ground an experiment plan
+     
+     Args:
+         input: Input hypothesis text
+         yaml_map_path: Path to YAML map of vector stores
+         model: LLM model to use
+         output_folder: Folder to save outputs
+         prefix: Prefix for output files
+         temperature: Temperature for LLM model
+         
+     Returns:
+         Tuple of (markdown output string, experiment plan object)
+     """
+     
+     # Create output directory if it doesn't exist
+     output_folder = Path(output_folder)
+     if not output_folder.exists():
+         output_folder.mkdir(parents=True)
+     
+     # Define output paths
+     out_md = output_folder / f"{prefix}_experiment_plan.md"
+     out_pdf = output_folder / f"{prefix}_experiment_plan.pdf"
+     out_json = output_folder / f"{prefix}_experiment_plan.json"
      
-     # Then generate the experiment plan using the restated hypothesis
+     # Then generate the experiment plan using the hypothesis
      plan_template = """\
  Given the following scientific hypothesis, generate a detailed experiment plan to test the hypothesis. \
      out_string = "\n".join(output_parts)
      
-     if out_md:
-         out_md = Path(out_md)
-         out_dir = out_md.parent
-         if not out_dir.exists():
-             out_dir.mkdir(parents=True)
-         with open(out_md, "w") as f:
-             print(out_string, file=f)
-         html_content = markdown.markdown(out_string)
-         out_pdf = out_dir / (out_md.stem + ".pdf")
-         pdfkit.from_string(html_content, out_pdf)
-         logging.info(f"Output saved to {out_md} & {out_pdf}")
+     # Save outputs
+     # Save markdown
+     with open(out_md, "w") as f:
+         print(out_string, file=f)
+     
+     # Save PDF
+     html_content = markdown.markdown(out_string)
+     pdfkit.from_string(html_content, out_pdf)
+     
+     # Save JSON
+     with open(out_json, "w") as f:
+         json.dump(experiment_plan.dict(), f, indent=2)
+     
+     logging.info(f"Saved outputs to {output_folder}:")
+     logging.info(f"  - Markdown: {out_md}")
+     logging.info(f"  - PDF: {out_pdf}")
+     logging.info(f"  - JSON: {out_json}")
      
-     return out_string
+     return out_string, experiment_plan
  
  def generate_protocol_flow(
```

---

_****_



Now let me modify the protocol generation flow to work with the serialized JSON plan:

---

_****_

```diff
  
  def generate_protocol_flow(
-     input_md: Path,
+     input_json: Path,
      model: str,
+     output_folder: Path,
+     prefix: str,
      temperature: float = 0.0,
-     out_md: Path = None,
- ) -> str:
-     """Generate a detailed experimental protocol from an experiment plan markdown file"""
+ ) -> Tuple[str, Protocol]:
+     """Generate a detailed experimental protocol from a serialized experiment plan
+     
+     Args:
+         input_json: Path to the serialized experiment plan JSON
+         model: LLM model to use
+         output_folder: Folder to save outputs
+         prefix: Prefix for output files
+         temperature: Temperature for LLM model
+         
+     Returns:
+         Tuple of (markdown output string, protocol object)
+     """
+     
+     # Create output directory if it doesn't exist
+     output_folder = Path(output_folder)
+     if not output_folder.exists():
+         output_folder.mkdir(parents=True)
+     
+     # Define output paths
+     out_md = output_folder / f"{prefix}_protocol.md"
+     out_pdf = output_folder / f"{prefix}_protocol.pdf"
+     out_json = output_folder / f"{prefix}_protocol.json"
+     log_file = output_folder / f"{prefix}_protocol.log"
      
      # Set up logging for this run
-     if out_md:
-         out_dir = Path(out_md).parent
-         if not out_dir.exists():
-             out_dir.mkdir(parents=True)
-         log_file = out_dir / "ragnosis_protocol.log"
-     else:
-         log_file = Path("ragnosis_protocol.log")
-     
-     # Add file handler to root logger
      file_handler = logging.FileHandler(log_file)
      file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
      
      try:
-         # Read and parse the experiment plan markdown
-         with open(input_md, "r") as f:
-             experiment_plan_text = f.read()
-         
-         # Extract Assay Types and Organisms sections from input markdown
-         assay_types_section = ""
-         organisms_section = ""
-         current_section = None
-         
-         for line in experiment_plan_text.split('\n'):
-             if line.startswith('## Assay Types'):
-                 current_section = 'assay_types'
-                 continue
-             elif line.startswith('## Organisms'):
-                 current_section = 'organisms'
-                 continue
-             elif line.startswith('## '):
-                 current_section = None
-                 continue
-             elif current_section == 'assay_types':
-                 assay_types_section += line + '\n'
-             elif current_section == 'organisms':
-                 organisms_section += line + '\n'
-         
-         logging.debug(f"Extracted assay types section: {len(assay_types_section)} characters")
-         logging.debug(f"Extracted organisms section: {len(organisms_section)} characters")
+         # Read and parse the experiment plan JSON
+         with open(input_json, "r") as f:
+             experiment_plan_dict = json.load(f)
+             experiment_plan = ExperimentPlan(**experiment_plan_dict)
+         
+         logging.info("Successfully loaded experiment plan from JSON")
  
          # Create LLM instance
          logging.info("Generating protocol from experiment plan")
          try:
-             protocol = protocol_retry_chain.invoke({"experiment_plan": experiment_plan_text})
+             protocol = protocol_retry_chain.invoke({"experiment_plan": experiment_plan.json()})
              logging.info("Protocol generation successful")
              logging.debug(f"Generated protocol with {len(protocol.steps)} steps")
                      sections.append(f"## {section_title}\n{items}\n")
              
-             # Add Assay Types and Organisms sections from input if they exist
-             if assay_types_section.strip():
-                 sections.append(f"## Assay Types\n{assay_types_section}\n")
-             if organisms_section.strip():
-                 sections.append(f"## Organisms\n{organisms_section}\n")
-             
              out_string = '\n'.join(sections)
              logging.debug(f"Generated markdown output with {len(sections)} sections")
              raise
  
-         # Save output files if requested
-         if out_md:
-             logging.info(f"Saving output to {out_md}")
+         # Save outputs
+         logging.info(f"Saving outputs to {output_folder}")
          try:
-                 out_md = Path(out_md)
-                 out_dir = out_md.parent
-                 if not out_dir.exists():
-                     logging.debug(f"Creating output directory: {out_dir}")
-                     out_dir.mkdir(parents=True)
-                 
              # Save markdown
              with open(out_md, "w") as f:
              logging.info("Converting to PDF")
              html_content = markdown.markdown(out_string)
-                 out_pdf = out_dir / (out_md.stem + ".pdf")
              pdfkit.from_string(html_content, out_pdf)
              logging.debug(f"Saved PDF output to {out_pdf}")
              
-                 logging.info(f"Output saved to {out_md} & {out_pdf}")
+             # Save JSON
+             with open(out_json, "w") as f:
+                 json.dump(protocol.dict(), f, indent=2)
+             logging.debug(f"Saved JSON output to {out_json}")
+             
+             logging.info(f"Successfully saved all outputs:")
+             logging.info(f"  - Markdown: {out_md}")
+             logging.info(f"  - PDF: {out_pdf}")
+             logging.info(f"  - JSON: {out_json}")
          except Exception as e:
              logging.error(f"Failed to save output files: {e}")
              raise
          
          logging.info("Protocol generation workflow completed successfully")
-         return out_string
+         return out_string, protocol
          
      finally:
      # Subcommand for generating a detailed experimental protocol
      protocol_parser = subparsers.add_parser("generate_protocol", help="Generate a detailed experimental protocol from an experiment plan markdown file")
-     protocol_parser.add_argument("input_md", type=Path, help="Path to the experiment plan markdown file")
+     protocol_parser.add_argument("input_json", type=Path, help="Path to the serialized experiment plan JSON")
      protocol_parser.add_argument("--model", type=str, default="openai/gpt-4", help="LLM model to use")
      protocol_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
-     protocol_parser.add_argument("--out_md", type=Path, default=None, help="Output file to save the results (.md)")
+     protocol_parser.add_argument("--output_folder", type=Path, default=None, help="Folder to save outputs")
+     protocol_parser.add_argument("--prefix", type=str, default="protocol", help="Prefix for output files")
  
      return parser
```

---

_****_



Now I need to update the main function to handle the new parameters:

---

_****_

```diff
      experiment_plan_parser.add_argument("--model", type=str, default="openai/gpt-4", help="LLM model to use")
      experiment_plan_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
-     experiment_plan_parser.add_argument("--out_md", type=Path, default=None, help="Output file to save the results (.md)")
+     experiment_plan_parser.add_argument("--output_folder", type=Path, required=True, help="Folder to save outputs")
+     experiment_plan_parser.add_argument("--prefix", type=str, default="experiment_plan", help="Prefix for output files")
  
      # Subcommand for generating a detailed experimental protocol
-     protocol_parser = subparsers.add_parser("generate_protocol", help="Generate a detailed experimental protocol from an experiment plan markdown file")
+     protocol_parser = subparsers.add_parser("generate_protocol", help="Generate a detailed experimental protocol from an experiment plan JSON")
      protocol_parser.add_argument("input_json", type=Path, help="Path to the serialized experiment plan JSON")
      protocol_parser.add_argument("--model", type=str, default="openai/gpt-4", help="LLM model to use")
      protocol_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
-     protocol_parser.add_argument("--output_folder", type=Path, default=None, help="Folder to save outputs")
+     protocol_parser.add_argument("--output_folder", type=Path, required=True, help="Folder to save outputs")
      protocol_parser.add_argument("--prefix", type=str, default="protocol", help="Prefix for output files")
  
```

---

_****_



I've made all the necessary changes to implement the requested workflow. Here's a summary of what's changed:

1. `generate_experiment_plan_flow`:
   - Now takes `output_folder` and `prefix` parameters
   - Creates output directory if it doesn't exist
   - Saves three files:
     - `{prefix}_experiment_plan.md` (markdown output)
     - `{prefix}_experiment_plan.pdf` (PDF version)
     - `{prefix}_experiment_plan.json` (serialized experiment plan)
   - Returns both the markdown string and the experiment plan object

2. `generate_protocol_flow`:
   - Now takes a JSON file path as input instead of markdown
   - Takes `output_folder` and `prefix` parameters
   - Creates output directory if it doesn't exist
   - Saves four files:
     - `{prefix}_protocol.md` (markdown output)
     - `{prefix}_protocol.pdf` (PDF version)
     - `{prefix}_protocol.json` (serialized protocol)
     - `{prefix}_protocol.log` (detailed logging)
   - Returns both the markdown string and the protocol object

3. Command line interface:
   - Updated argument parsers for both commands
   - Made `output_folder` required for both commands
   - Added `prefix` parameter with defaults
   - Updated help text and descriptions

The workflow now works like this:

1. Generate experiment plan:
```bash
python -m ragnosis.grounding generate_experiment_plan \
  "hypothesis text" \
  path/to/yaml_map.yml \
  --output_folder /path/to/output \
  --prefix "1_plan"
```

2. Generate protocol from the experiment plan:
```bash
python -m ragnosis.grounding generate_protocol \
  /path/to/output/1_plan_experiment_plan.json \
  --output_folder /path/to/output \
  --prefix "1_protocol"
```

Each step will create its own set of output files with the specified prefix, and the protocol generation will use the serialized JSON from the experiment plan step as input.

---

_**User**_

Ok great. I want to further modify this so that the generate_experiment_plan_flow actually has to take two inputs from the user (1) is a hypothesis string input and (2) is an (optional) context string. These should still be passed through to the plan_template as a single concatenated string

---

_**Assistant**_

I'll help modify the code to accept both a hypothesis string and an optional context string, then combine them appropriately in the plan template. Here's how we'll do it:

1. Update the function signature and docstring
2. Modify the plan template to handle both inputs
3. Update the argument parser to accept the optional context

---

_****_

```diff
  
  def generate_experiment_plan_flow(
-     input: str,
+     hypothesis: str,
      yaml_map_path: Path,
      model: str,
      output_folder: Path,
      prefix: str,
+     context: str = None,
      temperature: float = 0.0,
  ) -> Tuple[str, ExperimentPlan]:
      """Main flow to generate and ground an experiment plan
      
      Args:
-         input: Input hypothesis text
+         hypothesis: Input hypothesis text
          yaml_map_path: Path to YAML map of vector stores
          model: LLM model to use
          output_folder: Folder to save outputs
          prefix: Prefix for output files
+         context: Optional additional context for the hypothesis
          temperature: Temperature for LLM model
          
      out_json = output_folder / f"{prefix}_experiment_plan.json"
      
-     # Then generate the experiment plan using the hypothesis
+     # Combine hypothesis and context if provided
+     input_text = hypothesis
+     if context:
+         input_text = f"Context:\n{context}\n\nHypothesis:\n{hypothesis}"
+     
+     # Generate the experiment plan using the hypothesis and context
      plan_template = """\
- Given the following scientific hypothesis, generate a detailed experiment plan to test the hypothesis. \
+ Given the following input, generate a detailed experiment plan to test the hypothesis. \
  For each field, extract key entities (techniques, reagents, controls, etc.) as a list.
  
  {format_instructions}
  
- Hypothesis: ```{restated_hypothesis}```
+ Input: ```{input_text}```
  
  Response:"""
      plan_prompt = PromptTemplate(
          template=plan_template,
-         input_variables=["restated_hypothesis"],
+         input_variables=["input_text"],
          partial_variables={"format_instructions": plan_parser.get_format_instructions()}
      )
      ) | RunnableLambda(lambda x: plan_retry_parser.parse_with_prompt(**x))
      
-     experiment_plan = plan_retry_chain.invoke({"restated_hypothesis": input})
+     experiment_plan = plan_retry_chain.invoke({"input_text": input_text})
      
      # Ground the entities in the plan
      # Generate output - using list of strings to ensure proper formatting
      output_parts = [
-         "# Input Hypothesis",
+         "# Input",
          "",
-         input,
+         input_text,
          "",
          "# Generated Experiment Plan",
```

---

_****_



Now let's update the argument parser to handle the new optional context parameter:

---

_****_

```diff
      # Subcommand for experiment plan generation
      experiment_plan_parser = subparsers.add_parser("generate_experiment_plan", help="Generate and ground an experiment plan from a hypothesis")
-     experiment_plan_parser.add_argument("input", type=str, help="Input hypothesis text")
+     experiment_plan_parser.add_argument("hypothesis", type=str, help="Input hypothesis text")
      experiment_plan_parser.add_argument("yaml_map_path", type=Path, help="Path to the YAML map of vector stores")
+     experiment_plan_parser.add_argument("--context", type=str, help="Optional additional context for the hypothesis")
      experiment_plan_parser.add_argument("--model", type=str, default="openai/gpt-4", help="LLM model to use")
      experiment_plan_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
```

---

_****_



I've made the following changes:

1. Modified `generate_experiment_plan_flow`:
   - Changed the function signature to take `hypothesis` and optional `context` parameters
   - Added logic to combine hypothesis and context when context is provided
   - Updated the prompt template to handle the combined input
   - Updated the output formatting to show both context and hypothesis when provided
   - Updated docstring with new parameter descriptions

2. Updated the argument parser:
   - Renamed the first positional argument from `input` to `hypothesis`
   - Added a new optional `--context` argument

Now the function can be called in two ways:

1. With just a hypothesis:
```bash
python -m ragnosis.grounding generate_experiment_plan \
  "My hypothesis text" \
  path/to/yaml_map.yml \
  --output_folder /path/to/output \
  --prefix "1_plan"
```

2. With both hypothesis and context:
```bash
python -m ragnosis.grounding generate_experiment_plan \
  "My hypothesis text" \
  path/to/yaml_map.yml \
  --context "Additional context about the hypothesis" \
  --output_folder /path/to/output \
  --prefix "1_plan"
```

When context is provided, it will be included in:
1. The prompt to the LLM (formatted as "Context: ... Hypothesis: ...")
2. The markdown output (under the "Input" section)
3. The generated plan will take both the hypothesis and context into account

The rest of the workflow (JSON serialization, protocol generation, etc.) remains unchanged since the experiment plan object structure stays the same.

---

_**User**_

Ok excellent, now let's fix `evaluate_protocol` in @evaluate_protocol.py to accept an input json instead of what is is now. It should expect the input json following the data model that is outputed by the generate protocol flow

---

_**Assistant**_

I'll modify the `evaluate_protocol.py` file to accept a protocol JSON file as input instead of a markdown file. The function should expect the JSON format that matches the `Protocol` model output from `generate_protocol_flow`.

---

_****_

```diff
  from langchain_core.output_parsers.string import StrOutputParser
  from langchain_core.runnables import RunnableLambda, RunnableParallel
+ import json
  
  from ragnosis.aux import get_llm
+ from ragnosis.models import Protocol
  
  class ProtocolEvaluation(BaseModel):
      )
  
- def evaluate_protocol(protocol_path: str, model: str = "openai/gpt-4", temperature: float = 0.0) -> Dict:
+ def evaluate_protocol(protocol_json_path: Path, model: str = "openai/gpt-4", temperature: float = 0.0) -> Dict:
      """
-     Evaluates a protocol markdown file for executability and clarity.
+     Evaluates a protocol JSON file for executability and clarity.
      
      Args:
-         protocol_path: Path to the protocol markdown file
+         protocol_json_path: Path to the protocol JSON file (output from generate_protocol_flow)
          model: The LLM model to use for evaluation
          temperature: Temperature parameter for the LLM
      llm = get_llm(model, kwargs={'temperature': temperature})
      
-     # Read the protocol
-     with open(protocol_path, 'r') as f:
-         protocol_content = f.read()
+     # Read and parse the protocol JSON
+     with open(protocol_json_path, 'r') as f:
+         protocol_dict = json.load(f)
+         protocol = Protocol(**protocol_dict)
+     
+     # Convert protocol to a formatted string for evaluation
+     protocol_content = []
+     for field_name, field_value in protocol.dict().items():
+         section_title = field_name.replace('_', ' ').title()
+         protocol_content.append(f"## {section_title}")
+         
+         if isinstance(field_value, str):
+             protocol_content.append(field_value)
+         elif isinstance(field_value, list):
+             for item in field_value:
+                 protocol_content.append(f"- {item}")
+         protocol_content.append("")
+     
+     protocol_text = "\n".join(protocol_content)
      
      # Construct the evaluation prompt
      
      # Run the evaluation
-     evaluation_results = evaluation_retry_chain.invoke({"protocol_content": protocol_content})
+     evaluation_results = evaluation_retry_chain.invoke({"protocol_content": protocol_text})
      
      return evaluation_results.dict()
      
      parser = argparse.ArgumentParser(description="Evaluate a protocol for executability")
-     parser.add_argument("protocol_path", help="Path to the protocol markdown file")
+     parser.add_argument("protocol_json_path", type=Path, help="Path to the protocol JSON file")
      parser.add_argument("--model", default="openai/gpt-4", help="Model to use for evaluation")
      parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the model")
-     parser.add_argument("--out_json", help="Optional path to save evaluation results as JSON")
+     parser.add_argument("--out_json", type=Path, help="Optional path to save evaluation results as JSON")
      
      args = parser.parse_args()
      
-     results = evaluate_protocol(args.protocol_path, args.model, args.temperature)
+     results = evaluate_protocol(args.protocol_json_path, args.model, args.temperature)
      
      if args.out_json:
```

---

_****_



I've made the following changes to `evaluate_protocol.py`:

1. Adde

---



---

