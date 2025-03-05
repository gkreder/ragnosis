## SpecStory

## Modifying Experiment Plan Output Function (12/10/2024, 9:12:03 PM)

_**User**_

I've modified the `ExperimentPlan` model in models.py such that there are now a couple of new `str` fields. Can we modify the `generate_experiment_plan_flow` function to fix the md/pdf output accordingly? Any str field in the model should appear in the final output as a normal string (like `description` was appearing before). The list[str] fields can continue to be handled in the same way as before

---

_**Assistant**_

I'll help modify the `generate_experiment_plan_flow` function to handle any string fields in the `ExperimentPlan` model consistently. Looking at the code blocks:

1. First, I see the `ExperimentPlan` model in models.py:

```50:64:ragnosis/models.py
class ExperimentPlan(BaseModel):
    """A plan for an experiment that will test the given hypothesis"""
    description: str = Field(description="A free-text description of the experiment and how it will test the hypothesis")
    hypothesis: str = Field(description="A restating of the hypothesis")
    assay_types : List[str] = Field(description="The assay(s) to use in the experiment")
    objective : str = Field(description="The purpose of the experiment, including the effect or relationship being tested")
    organisms : List[str] = Field(description="The model organisms to use in the experiment")
    experimental_variables : List[str] = Field(description="The manipulated factor(s), including the target and modulation type")
    dependent_variables : List[str] = Field(description="The measurable outcome(s), specifying the target, expected change, and readout method")
    expected_outcome: str = Field(description="A summary of the anticipated result if the hypothesis is correct")
    # background_knowledge: List[str] = Field(description="Known biological pathways and contextual information entities")
    # resources: List[str] = Field(description="Instruments, reagents, and other resource entities needed")
    # controls: List[str] = Field(description="Positive and negative control entities for the experiment")
    # statistical_approach: List[str] = Field(description="Sample size, replication, precision, and criteria entities")
    # potential_pitfalls: List[str] = Field(description="Potential challenge entities in experiment design")
```


2. And the current `generate_experiment_plan_flow` function:

```400:490:ragnosis/grounding.py
def generate_experiment_plan_flow(
    input: str,
    yaml_map_path: Path,
    model: str,
    temperature: float = 0.0,
    out_md: Path = None,
) -> str:
    """Main flow to generate and ground an experiment plan"""
    
    # First generate the experiment plan with entities
    llm = get_llm(model, kwargs={'temperature': temperature})
    
    plan_template = textwrap.dedent("""\
    Given the following scientific hypothesis, generate a detailed experiment plan to test the hypothesis. \
    For each field, extract key entities (techniques, reagents, controls, etc.) as a list.

    {format_instructions}
    
    Hypothesis: ```{hypothesis}```
    
    Response:""")
    
    plan_parser = PydanticOutputParser(pydantic_object=ExperimentPlan)
    plan_retry_parser = RetryOutputParser.from_llm(parser=plan_parser, llm=llm)
    
    plan_prompt = PromptTemplate(
        template=plan_template,
        input_variables=["hypothesis"],
        partial_variables={"format_instructions": plan_parser.get_format_instructions()}
    )
    
    plan_chain = plan_prompt | llm | StrOutputParser()
    plan_retry_chain = RunnableParallel(
        completion=plan_chain,
        prompt_value=plan_prompt
    ) | RunnableLambda(lambda x: plan_retry_parser.parse_with_prompt(**x))
    experiment_plan = plan_retry_chain.invoke({"hypothesis": input})
    
    # Ground the entities in the plan
    grounded_plan = ground_experiment_plan(
        experiment_plan=experiment_plan,
        yaml_map_path=yaml_map_path,
        model=model,
        temperature=temperature
    )
    
    # Generate output
    out_string = textwrap.dedent(f"""\
    # Input Hypothesis
    
    {input}\n
    
    # Generated Experiment Plan
    
    ## Description
    
    {experiment_plan.description}\n
    
    ## Detailed Components\n""")
    
    for field_name, entities in experiment_plan.dict().items():
        if field_name == "description":  # Skip description as it's already handled
            continue
            
        out_string += f"### {field_name}\n"
        if not entities:
            out_string += "No entities extracted\n\n"
            continue
            
        for entity in entities:
            out_string += f"#### {entity}\n"
            if entity in grounded_plan.get(field_name, {}):
                grounded_entity = grounded_plan[field_name][entity]
                for k, v in grounded_entity.__dict__.items():
                    out_string += f"- {k}: {v}\n"
            out_string += "\n"
    
    if out_md:
        out_md = Path(out_md)
        out_dir = out_md.parent
        if not out_dir.exists():
            out_dir.mkdir(parents=True)
        with open(out_md, "w") as f:
            print(out_string, file=f)
        html_content = markdown.markdown(out_string)
        out_pdf = out_dir / (out_md.stem + ".pdf")
        pdfkit.from_string(html_content, out_pdf)
        logging.info(f"Output saved to {out_md} & {out_pdf}")
    return out_string
```


Here's the modified version of the `generate_experiment_plan_flow` function that will handle both string and List[str] fields appropriately:

```python:ragnosis/grounding.py
def generate_experiment_plan_flow(
    input: str,
    yaml_map_path: Path,
    model: str,
    temperature: float = 0.0,
    out_md: Path = None,
) -> str:
    """Main flow to generate and ground an experiment plan"""
    
    # First generate the experiment plan with entities
    llm = get_llm(model, kwargs={'temperature': temperature})
    
    plan_template = textwrap.dedent("""\
    Given the following scientific hypothesis, generate a detailed experiment plan to test the hypothesis. \
    For each field, extract key entities (techniques, reagents, controls, etc.) as a list.

    {format_instructions}
    
    Hypothesis: ```{hypothesis}```
    
    Response:""")
    
    plan_parser = PydanticOutputParser(pydantic_object=ExperimentPlan)
    plan_retry_parser = RetryOutputParser.from_llm(parser=plan_parser, llm=llm)
    
    plan_prompt = PromptTemplate(
        template=plan_template,
        input_variables=["hypothesis"],
        partial_variables={"format_instructions": plan_parser.get_format_instructions()}
    )
    
    plan_chain = plan_prompt | llm | StrOutputParser()
    plan_retry_chain = RunnableParallel(
        completion=plan_chain,
        prompt_value=plan_prompt
    ) | RunnableLambda(lambda x: plan_retry_parser.parse_with_prompt(**x))
    
    experiment_plan = plan_retry_chain.invoke({"hypothesis": input})
    
    # Ground the entities in the plan
    grounded_plan = ground_experiment_plan(
        experiment_plan=experiment_plan,
        yaml_map_path=yaml_map_path,
        model=model,
        temperature=temperature
    )
    
    # Generate output
    out_string = textwrap.dedent(f"""\
    # Input Hypothesis
    
    {input}\n
    
    # Generated Experiment Plan\n""")
    
    # Handle all fields from the experiment plan
    for field_name, value in experiment_plan.dict().items():
        out_string += f"## {field_name.replace('_', ' ').title()}\n\n"
        
        if isinstance(value, str):
            # Handle string fields
            out_string += f"{value}\n\n"
        elif isinstance(value, list):
            # Handle list fields
            if not value:
                out_string += "No entities extracted\n\n"
                continue
                
            for entity in value:
                out_string += f"### {entity}\n"
                if field_name in grounded_plan and entity in grounded_plan[field_name]:
                    grounded_entity = grounded_plan[field_name][entity]
                    for k, v in grounded_entity.__dict__.items():
                        out_string += f"- {k}: {v}\n"
                out_string += "\n"
    
    if out_md:
        out_md = Path(out_md)
        out_dir = out_md.parent
        if not out_dir.exists():
            out_dir.mkdir(parents=True)
        with open(out_md, "w") as f:
            print(out_string, file=f)
        html_content = markdown.markdown(out_string)
        out_pdf = out_dir / (out_md.stem + ".pdf")
        pdfkit.from_string(html_content, out_pdf)
        logging.info(f"Output saved to {out_md} & {out_pdf}")
    
    return out_string
```

The key changes made are:

1. Removed the special handling of the "description" field
2. Added a generic field handling loop that:
   - Formats the field name nicely (replacing underscores with spaces and capitalizing)
   - Checks if the field is a string or list type
   - For strings: outputs the value directly
   - For lists: maintains the existing entity grounding output format

This will now handle any string fields in the ExperimentPlan model consistently, while maintaining the existing behavior for list fields that need grounding.

---

_**User**_

Create a new script based on this one that will run on the hypotheses files 1.txt - 5.txt (this one only runs on 1.txt)

---

_**Assistant**_

I'll help create a script that processes multiple hypothesis files. Here's the modified version of the original script:

```bash:process_hypotheses.sh
cd /Users/gkreder/ragnosis
export PYTHONPATH=$PYTHONPATH:/Users/gkreder/ragnosis

# Process hypotheses 1 through 5
for i in {1..5}; do
    echo "Processing hypothesis $i..."
    
    # Define input and output paths
    hypothesis_file="/Users/gkreder/org/data/B2/46CD05-23D2-4C80-AD16-F7F01FEBF601/individual_extracted_hypotheses/$i.txt"
    output_file="/Users/gkreder/Downloads/2024-12-11_medium-boat-output/$i.md"
    
    # Check if input file exists
    if [ ! -f "$hypothesis_file" ]; then
        echo "Warning: Input file $hypothesis_file does not exist. Skipping..."
        continue
    fi
    
    # Read the content of the file into a variable
    hypothesis=$(cat "$hypothesis_file")
    
    # Run the Python script with the extracted content
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_experiment_plan \
    "$hypothesis" \
    "/Users/gkreder/scripts/medium-boat/2024-12-02_abbi-test/index_mapping.yaml" \
    --model "openai/gpt-4o" \
    --temperature 0.0 \
    --out_md "$output_file"
    
    echo "Completed processing hypothesis $i"
    echo "----------------------------------------"
done

echo "All hypotheses processed successfully!"
```

This script:

1. Sets up the same environment as the original script
2. Uses a for loop to iterate through hypotheses 1-5
3. Constructs the input and output paths dynamically based on the iteration number
4. Includes error checking for missing input files
5. Processes each hypothesis file using the same parameters as the original script
6. Adds progress messages to track the processing status

You can run this script the same way as the original:
```bash
bash process_hypotheses.sh
```

The script will create corresponding output files (1.md through 5.md) in the specified output directory, along with their PDF versions.

---



---

