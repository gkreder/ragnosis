## SpecStory

## Adding Experiment Plan Flow to Grounding.py (12/2/2024, 9:32:13 AM)

_**User**_

I'd like to add a flow to `grounding.py` that will take an input hypothesis and will produce an `ExperimentPlan` object. The ExperimentPlan will include the following fields:

```
- Background knowledge / Biological context: known biological pathways and more contextual info?
- Resources: Do we need to define more on ‘Resources’…e.g. ‘Instrument(s)’ or ‘reagents’…need to be defined? Add its own heading or expand ‘Assay type’?
- Controls: Do we need to include positive and negative controls as a heading? Useful because experiments typically must include controls (top level info)
- Statistical approach: eg. Sample size, replication, precision, criteria for acceptance of hypothesis, etc?
- Potential pitfalls or challenges in experiment design: this might be worth starting to think about especially in situations where the results do not prove the hypothesis;
```

Importantly, the entities in some of the fields should be grounded to ontologies (indices) provided by the user at runtime. The fields to ground and the indices to ground will be provided by the user as a yaml as for the other flows.

---

_**Assistant**_

To add a new flow in `grounding.py` that generates an `ExperimentPlan` object, you'll need to follow these steps:

1. **Define the `ExperimentPlan` Model**: Add a new Pydantic model in `models.py` for the `ExperimentPlan`.

2. **Create the Flow Function**: Implement a function in `grounding.py` that takes an input hypothesis and generates an `ExperimentPlan`.

3. **Ground Entities**: Use the provided YAML file to ground specific fields to ontologies.

4. **Update Command Line Interface**: Add a new command to the CLI for this flow.

Here's how you can implement these steps:

### Step 1: Define the `ExperimentPlan` Model

Add the following class to `models.py`:

```python:ragnosis/models.py
from typing import List, Optional
from pydantic import BaseModel, Field

class ExperimentPlan(BaseModel):
    background_knowledge: Optional[str] = Field(description="Known biological pathways and contextual information")
    resources: Optional[str] = Field(description="Instruments, reagents, and other resources needed")
    controls: Optional[str] = Field(description="Positive and negative controls for the experiment")
    statistical_approach: Optional[str] = Field(description="Sample size, replication, precision, criteria for acceptance")
    potential_pitfalls: Optional[str] = Field(description="Potential challenges in experiment design")
```

### Step 2: Create the Flow Function

Add a new function in `grounding.py`:

```python:ragnosis/grounding.py
from ragnosis.models import ExperimentPlan

def generate_experiment_plan(input: str, yaml_map_path: Path, model: str, temperature: float = 0.0) -> ExperimentPlan:
    # Load the YAML map for grounding
    yaml_map_path = Path(yaml_map_path)
    with open(yaml_map_path, "r") as f:
        yaml_map = yaml.safe_load(f)

    # Extract entities from the hypothesis
    entity_extraction_response = extract_entities(input=input, model=model, temperature=temperature)

    # Ground entities using the provided YAML map
    vector_store_map = load_vector_stores_yaml(yaml_map_path)
    grounded_entities = ground_entities(input=input, entity_extraction_response=entity_extraction_response, 
                                        vector_store_map=vector_store_map, model=model, temperature=temperature)

    # Create the ExperimentPlan object
    experiment_plan = ExperimentPlan(
        background_knowledge="Extracted background knowledge",
        resources="Extracted resources",
        controls="Extracted controls",
        statistical_approach="Extracted statistical approach",
        potential_pitfalls="Extracted potential pitfalls"
    )

    return experiment_plan
```

### Step 3: Ground Entities

Ensure that the `ground_entities` function is capable of grounding the necessary fields for the `ExperimentPlan`. You may need to adjust the logic to handle new fields if they require specific grounding.

### Step 4: Update Command Line Interface

Add a new command to the CLI in `grounding.py`:

```python:ragnosis/grounding.py
def get_parser():
    parser = argparse.ArgumentParser(description="Ragnosis scientific knowledge grounding")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Existing subcommands...

    # Subcommand for generating an experiment plan
    experiment_plan_parser = subparsers.add_parser("generate_experiment_plan", help="Generate an experiment plan from a hypothesis")
    experiment_plan_parser.add_argument("input", type=str, help="User input hypothesis")
    experiment_plan_parser.add_argument("yaml_map_path", type=Path, help="Path to the YAML map of vector stores")
    experiment_plan_parser.add_argument("--model", type=str, default="openai/gpt-4o", help="LLM model to use for the experiment plan")
    experiment_plan_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")

    return parser

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
        "ground_hypothesis": ground_hypothesis_flow,
        "extract_hypothesis": extract_hypothesis_flow,
        "generate_experiment_plan": generate_experiment_plan,  # Add this line
    }
    if args.command in command_map:
        command_args = {k: v for k, v in vars(args).items() if k != "command"}
        logging.info(f"Running command {args.command}")
        command_map[args.command](**command_args)
    else:
        parser.print_help()
```

This setup will allow you to generate an `ExperimentPlan` from a hypothesis, grounding specific fields to ontologies as specified by the user. Adjust the logic in `generate_experiment_plan` to extract and ground the necessary information for each field.

---

_**User**_

Ok this is a good start. Especially with the new object class. One thing that might be wrong though is that the `ground_entities` function expects an input hypothesis and grounds its entities. In our new flow, we want to ground entities on a field-by-field basis in the new object class type. Each field of the class will be mapped to a specific index via yaml. So the grounding task is even a little easier this time. I'm not sure where to do entity extraction though. I think the best way is to modify the new object to be a list of strings so they are already "entities"

---

_**Assistant**_

I understand - we want to modify the approach to handle grounding entities that are already extracted and organized in the ExperimentPlan fields. Let's first modify the ExperimentPlan model to use Lists of strings instead of single strings:

```python:ragnosis/models.py
class ExperimentPlan(BaseModel):
    background_knowledge: List[str] = Field(description="Known biological pathways and contextual information entities")
    resources: List[str] = Field(description="Instruments, reagents, and other resource entities needed")
    controls: List[str] = Field(description="Positive and negative control entities for the experiment")
    statistical_approach: List[str] = Field(description="Sample size, replication, precision, and criteria entities")
    potential_pitfalls: List[str] = Field(description="Potential challenge entities in experiment design")
```

Then, we'll need a new grounding function specifically for the ExperimentPlan that takes a YAML mapping of fields to indices. Here's how we can modify the grounding function:

```python:ragnosis/grounding.py
def ground_experiment_plan(experiment_plan: ExperimentPlan, 
                         yaml_map_path: Path,
                         model: str, 
                         temperature: float = 0.0) -> Dict[str, Dict[str, GroundedEntityWithSearchTerm]]:
    """
    Ground each field in the ExperimentPlan to ontology terms based on the yaml mapping.
    Returns a dictionary mapping field names to their grounded entities.
    """
    # Load vector stores from yaml
    yaml_map_path = Path(yaml_map_path)
    vector_store_map = load_vector_stores_yaml(yaml_map_path)
    
    # Check yaml compatibility with ExperimentPlan fields
    experiment_plan_keys = set(ExperimentPlan.__fields__.keys())
    yaml_keys = set(vector_store_map.keys())
    if not experiment_plan_keys.issubset(yaml_keys):
        raise ValueError(f"YAML map missing required keys: {experiment_plan_keys - yaml_keys}")
    
    llm = get_llm(model, kwargs={'temperature': temperature})
    grounded_fields = {}
    
    # Ground each field's entities using the corresponding vector store
    for field_name, entities in experiment_plan.dict().items():
        if not entities:  # Skip empty fields
            continue
            
        retriever = vector_store_map[field_name].as_retriever(search_kwargs={"k": RETRIEVER_TOP_K})
        field_groundings = {}
        
        for entity in entities:
            # Get search term
            search_term = get_search_term(entity=entity, llm=llm)
            
            # Ground entity using search term
            grounded_entity = ground_single_entity(
                entity=entity,
                search_term=search_term,
                retriever=retriever,
                llm=llm
            )
            
            field_groundings[entity] = grounded_entity
            
        grounded_fields[field_name] = field_groundings
        
    return grounded_fields
```

This approach:

1. Takes an ExperimentPlan object with pre-extracted entities in each field
2. Uses the YAML mapping to match each field to its corresponding vector store
3. Grounds each entity in each field using the appropriate vector store
4. Returns a nested dictionary of grounded entities organized by field

We can reuse most of the helper functions from the original grounding flow (like the prompt templates and parsers), but they'll be applied on a field-by-field basis rather than trying to extract and categorize entities first.

The main difference from the original `ground_entities` function (lines 107-208 in grounding.py) is that we don't need to handle entity extraction or categorization - we just need to ground pre-organized entities to their corresponding indices based on which field they're in.

Would you like me to continue with implementing the helper functions and the main flow that would use this grounding approach?

---

_**User**_

Ok yes, this appears to be looking a bit better. I've added these changes in. Go ahead and continue to implement the helper functions and main flow that would use this approach

---

_**Assistant**_

I'll help implement the helper functions and main flow. We'll need:

1. A function to get search terms for entities
2. A function to ground single entities
3. A main flow function to generate and ground an experiment plan

Here's the implementation:

```python:ragnosis/grounding.py
def get_search_term(entity: str, llm: BaseChatModel) -> str:
    """Get a search term for an entity to use for ontology lookup"""
    search_term_template = textwrap.dedent("""\
    Given the following entity, decide on a search term that will be used to retrieve \
    the most appropriate ontology term from a database of ontology terms. \
    Your decided search term may be the same as the entity, or it may be a more general/specific term.

    {format_instructions}
                                       
    Entity: ```{entity}```
    
    Response:""")
    
    search_term_parser = PydanticOutputParser(pydantic_object=SearchTerm)
    search_term_retry_parser = RetryOutputParser.from_llm(parser=search_term_parser, llm=llm)
    
    search_term_prompt = PromptTemplate(
        template=search_term_template,
        input_variables=["entity"],
        partial_variables={"format_instructions": search_term_parser.get_format_instructions()}
    )
    
    search_term_instance = search_term_prompt | llm | StrOutputParser()
    search_term_retry_instance = RunnableParallel(
        completion=search_term_instance, 
        prompt_value=search_term_prompt
    ) | RunnableLambda(lambda x: search_term_retry_parser.parse_with_prompt(**x))
    
    search_term = search_term_retry_instance.invoke({"entity": entity})
    return search_term.search_term

def ground_single_entity(
    entity: str,
    search_term: str,
    retriever: VectorStoreRetriever,
    llm: BaseChatModel
) -> GroundedEntityWithSearchTerm:
    """Ground a single entity to an ontology term"""
    grounding_template = textwrap.dedent("""\
    Given the following entity, find the best-fit ontology term to ground this entity. \
    Use your best judgement to select the most apt term from the ontology. \
    Base your decision ONLY on the retrieved ontology context below.
        
    retrieved context: ```{context}```
    
    {format_instructions}
                                         
    Entity: ```{entity}```
                                         
    Response:""")

    document_format_prompt = PromptTemplate.from_template(
        template="Concept label: {page_content} | URI: {uri} | Type: {type} | Predicate: {predicate} | Ontology: {ontology}"
    )
    
    def _combine_documents(docs, document_prompt=document_format_prompt, document_separator="\n\n"):
        doc_strings = [format_document(doc, document_prompt) for doc in docs]
        return document_separator.join(doc_strings)

    grounding_parser = PydanticOutputParser(pydantic_object=GroundedEntity)
    grounding_retry_parser = RetryOutputParser.from_llm(parser=grounding_parser, llm=llm)
    
    retrieved_docs = retriever.invoke(search_term)
    context = _combine_documents(retrieved_docs)
    
    grounding_prompt = PromptTemplate(
        template=grounding_template,
        input_variables=["entity"],
        partial_variables={
            "format_instructions": grounding_parser.get_format_instructions(),
            "context": context
        }
    )
    
    grounding_chain_instance = grounding_prompt | llm | StrOutputParser()
    grounding_retry_instance = RunnableParallel(
        completion=grounding_chain_instance,
        prompt_value=grounding_prompt
    ) | RunnableLambda(lambda x: grounding_retry_parser.parse_with_prompt(**x))
    
    grounded_entity = grounding_retry_instance.invoke({"entity": entity})
    return GroundedEntityWithSearchTerm(**grounded_entity.dict(), search_term=search_term)

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
    Given the following scientific hypothesis, generate a detailed experiment plan. \
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
    
    for field_name, entities in experiment_plan.dict().items():
        out_string += f"## {field_name}\n"
        if not entities:
            out_string += "No entities extracted\n\n"
            continue
            
        for entity in entities:
            out_string += f"### {entity}\n"
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

Now we need to add this new command to the parser. We can reference the existing parser code:


```309:358:ragnosis/grounding.py
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

    return parser

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
    }
    if args.command in command_map:
        command_args = {k : v for k, v in vars(args).items() if k != "command"}
        logging.info(f"Running command {args.command}")
        command_map[args.command](**command_args)
    else:
        parser.print_help()
```


And add our new command:

```python:ragnosis/grounding.py
def get_parser():
    # ... existing parser code ...
    
    # Add new subcommand for experiment plan generation
    experiment_plan_parser = subparsers.add_parser(
        "generate_experiment_plan",
        help="Generate and ground an experiment plan from a hypothesis"
    )
    experiment_plan_parser.add_argument(
        "input",
        type=str,
        help="Input hypothesis text"
    )
    experiment_plan_parser.add_argument(
        "yaml_map_path",
        type=Path,
        help="Path to the YAML map of vector stores"
    )
    experiment_plan_parser.add_argument(
        "--model",
        type=str,
        default="openai/gpt-4",
        help="LLM model to use"
    )
    experiment_plan_parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Temperature for the LLM model"
    )
    experiment_plan_parser.add_argument(
        "--out_md",
        type=Path,
        default=None,
        help="Output file to save the results (.md)"
    )
    
    return parser

def main():
    # ... existing main code ...
    command_map = {
        "create_index": create_vector_store,
        "ground_hypothesis": ground_hypothesis_flow,
        "extract_hypothesis": extract_hypothesis_flow,
        "generate_experiment_plan": generate_experiment_plan_flow,  # Add new command
    }
    # ... rest of main code ...
```

This implementation:
1. Reuses the existing grounding and search term logic but simplifies it for single entities
2. Adds a new flow to generate an experiment plan with pre-extracted entities
3. Grounds each entity in the plan using the appropriate vector store
4. Generates a formatted output with the results
5. Adds CLI support for the new functionality

Would you like me to explain any part in more detail or make any adjustments?

---



---

