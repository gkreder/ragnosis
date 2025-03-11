###############################################################################
# gk@reder.io
###############################################################################
import logging
import textwrap
from pathlib import Path
import argparse
import sys
import markdown
import pdfkit
from typing import Dict, Tuple
import yaml
import json
import pdb

# Workaround for the OpenMP forking error - needs more permanent fix
# See https://stackoverflow.com/questions/53014306/error-15-initializing-libiomp5-dylib-but-found-libiomp5-dylib-already-initial
import os
os.environ['KMP_DUPLICATE_LIB_OK']='True'

from langchain.output_parsers import PydanticOutputParser, RetryOutputParser
from langchain_core.output_parsers.string import StrOutputParser
from langchain.prompts import PromptTemplate
from langchain.schema import format_document
from langchain_core.runnables import RunnableLambda, RunnableParallel
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain.chat_models.base import BaseChatModel
from pydantic import BaseModel


from ragnosis.models import GroundedEntity, HypothesisEntities, ExtractedHypothesis, SearchTerm, GroundedEntityWithSearchTerm, HypothesisEvaluation, ExperimentPlan, Protocol, GroundedItem
from ragnosis.aux import get_llm, load_vector_stores_yaml, create_vector_store


###############################################################################
# Constants
###############################################################################
RETRIEVER_TOP_K = 5

###############################################################################

###############################################################################
def extract_hypothesis_flow(pdf_path : Path, model : str,
                            temperature : float = 0.0,
                            out_file : Path = None) -> str:
    llm = get_llm(model, kwargs={'temperature' : temperature})
    pdf_path = Path(pdf_path)
    logging.info("Loading PDF")
    loader = PyMuPDFLoader(pdf_path)
    docs = loader.load()
    hypothesis_parser = PydanticOutputParser(pydantic_object=ExtractedHypothesis)
    document_format_prompt = PromptTemplate.from_template(
        template="Page Number: {page} | Total Pages: {total_pages} | Page Content: ```{page_content}```",
    )
    def _combine_documents(
            docs, document_prompt=document_format_prompt, document_separator="\n\n"
    ):
        doc_strings = [format_document(doc, document_prompt) for doc in docs]
        return document_separator.join(doc_strings)
    hypothesis_template = textwrap.dedent("""\
    Given the following content from a single scientific paper, \
    extract the main hypothesis tested by the paper. \
                                        
    {format_instructions}
                                        
    Paper content: ```{paper_content}```
                                        
    Hypothesis:
    """)

    retry_parser = RetryOutputParser.from_llm(parser=hypothesis_parser, llm=llm)
    hypothesis_prompt = PromptTemplate(
        template=hypothesis_template,
        partial_variables={'format_instructions':hypothesis_parser.get_format_instructions(),
                        'paper_content' : _combine_documents(docs)}
    )
    logging.info("Extracting hypothesis")
    chain = hypothesis_prompt | llm | StrOutputParser()
    retry_chain = RunnableParallel(
        completion=chain, prompt_value=hypothesis_prompt
        ) | RunnableLambda(lambda x : retry_parser.parse_with_prompt(**x))
    extracted_hypothesis = retry_chain.invoke({})
    if out_file is not None:
        logging.info(f"Saving output to {out_file}")
        out_file = Path(out_file)
        out_dir = out_file.parent
        if not out_dir.exists():
            out_dir.mkdir(parents=True)
        with open(out_file, "w") as f:
            print(extracted_hypothesis.hypothesis, file = f)
    print(extracted_hypothesis.hypothesis)
    return extracted_hypothesis.hypothesis

def extract_entities(input : str, model : str, temperature : float = 0.0,) -> HypothesisEntities:
    llm = get_llm(model, kwargs={'temperature' : temperature})
    extract_entities_template = textwrap.dedent("""\
    Given the following scientific hypothesis, \
    extract all the entities of interest.

    {format_instructions}

    Hypothesis: ```{hypothesis}```
    """)

    entity_parser = PydanticOutputParser(pydantic_object=HypothesisEntities)
    entity_prompt = PromptTemplate(
        template=extract_entities_template,
        input_variables=["hypothesis"],
        partial_variables={"format_instructions":entity_parser.get_format_instructions()}
    )

    entity_chain = entity_prompt | llm | entity_parser
    entity_extraction_response = entity_chain.invoke({"hypothesis" : input})
    return entity_extraction_response

def ground_entities(input : str, entity_extraction_response : HypothesisEntities, 
                    vector_store_map : Dict[str, VectorStoreRetriever],
                    model : str, temperature : float = 0.0,):
    
    logging.info("Starting entity grounding workflow")
    
    # Note we're creating a new LLM instance here for grounding, but we could use the same one as for extraction
    try:
        llm = get_llm(model, kwargs={'temperature' : temperature})
        logging.debug(f"Initialized LLM model: {model} (temperature={temperature})")
    except Exception as e:
        logging.error(f"Failed to initialize LLM for grounding: {e}")
        raise

    # Setup parsers and templates
    logging.debug("Setting up parsers and templates for grounding")
    grounding_parser = PydanticOutputParser(pydantic_object=GroundedEntity)
    grounding_retry_parser = RetryOutputParser.from_llm(parser=grounding_parser, llm=llm)
    search_term_parser = PydanticOutputParser(pydantic_object=SearchTerm)
    search_term_retry_parser = RetryOutputParser.from_llm(parser=search_term_parser, llm=llm)
    
    grounded_entities = {}
    response_items = entity_extraction_response.dict().items()
    logging.info(f"Processing {len(response_items)} entity categories for grounding")
    
    for entity_list_name, entity_list in response_items:
        logging.info(f"Processing category: {entity_list_name} ({len(entity_list)} entities)")
        
        try:
            retriever = vector_store_map[entity_list_name].as_retriever(search_kwargs={"k": RETRIEVER_TOP_K})
            logging.debug(f"Initialized retriever for {entity_list_name}")
        except KeyError:
            logging.error(f"No vector store found for category: {entity_list_name}")
            raise
        
        temp_grounding = {}
        for entity in entity_list:
            logging.info(f"Grounding entity: {entity}")
            
            # Get search term
            try:
                search_term_prompt = PromptTemplate(
                    template=search_term_template,
                    input_variables=["entity"],
                    partial_variables={
                        "format_instructions": search_term_parser.get_format_instructions(),
                        "entity": entity,
                        "user_input": input,
                    }
                )
                
                search_term_instance = search_term_prompt | llm | StrOutputParser()
                search_term_retry_instance = RunnableParallel(
                    completion=search_term_instance, 
                    prompt_value=search_term_prompt
                ) | RunnableLambda(lambda x: search_term_retry_parser.parse_with_prompt(**x))
                
                search_term = search_term_retry_instance.invoke({"entity": entity})
                logging.debug(f"Generated search term: '{search_term.search_term}' for entity: '{entity}'")
            except Exception as e:
                logging.error(f"Failed to generate search term for entity '{entity}': {e}")
                raise

            # Ground entity using search term
            try:
                retrieved_docs = retriever.invoke(search_term.search_term)
                logging.debug(f"Retrieved {len(retrieved_docs)} documents for search term: '{search_term.search_term}'")
                
                context = _combine_documents(retrieved_docs)
                grounding_prompt = PromptTemplate(
                    template=grounding_template,
                    input_variables=["entity"],
                    partial_variables={
                        "format_instructions": grounding_parser.get_format_instructions(),
                        "context": context,
                        "user_input": input,
                    }
                )
                
                grounding_chain_instance = grounding_prompt | llm | StrOutputParser()
                grounding_retry_instance = RunnableParallel(
                    completion=grounding_chain_instance,
                    prompt_value=grounding_prompt
                ) | RunnableLambda(lambda x: grounding_retry_parser.parse_with_prompt(**x))
                
                grounded_entity = grounding_retry_instance.invoke({"entity": entity})
                grounded_entity_with_search_term = GroundedEntityWithSearchTerm(
                    **grounded_entity.dict(), 
                    search_term=search_term.search_term
                )
                
                logging.debug(f"Successfully grounded entity '{entity}':")
                for key, value in grounded_entity_with_search_term.dict().items():
                    logging.debug(f"  {key}: {value}")
                
                temp_grounding[entity] = grounded_entity_with_search_term
            except Exception as e:
                logging.error(f"Failed to ground entity '{entity}': {e}")
                raise

        grounded_entities[entity_list_name] = temp_grounding
        logging.info(f"Completed grounding for category: {entity_list_name}")
    
    logging.info("Entity grounding workflow completed successfully")
    return grounded_entities

def ground_hypothesis_flow(input : str, yaml_map_path : Path,
                           model : str, temperature : float = 0.0,
                           out_md : Path = None,) -> str:
    
    # Checking key compatibility between yaml and HypothesisEntities fields
    yaml_map_path = Path(yaml_map_path)
    with open(yaml_map_path, "r") as f:
        yaml_map = yaml.safe_load(f)
    hypothesis_model_keys = set(HypothesisEntities.__fields__.keys())
    yaml_keys = set(yaml_map.keys())
    if not hypothesis_model_keys.issubset(yaml_keys):
        raise ValueError(f"YAML map does not contain all the required keys for HypothesisEntities model. Missing fields: {hypothesis_model_keys - yaml_keys}")
    if yaml_keys != hypothesis_model_keys:
        logging.warning(f"YAML map contains extra keys not present in HypothesisEntities model. These vector stores will not be used. Extra fields: {yaml_keys - hypothesis_model_keys}")
    entity_extraction_response = extract_entities(input=input, model=model, temperature=temperature)
    vector_store_map = load_vector_stores_yaml(yaml_map_path)
    grounded_entities = ground_entities(input=input, entity_extraction_response=entity_extraction_response, 
                                        vector_store_map=vector_store_map,
                                        model=model, temperature=temperature)
    out_string = textwrap.dedent(f"""\
    # Input Text

    {input}\n

    # Extracted Entities\n""")
    response_items = entity_extraction_response.dict().items()
    for entity_list_name, entity_list in response_items:
        out_string += f"""## {entity_list_name}\n"""
        out_string += f"""{entity_list}\n\n"""
    out_string += "# Entity Grounding\n"
    for entity_list_name, entity_list in grounded_entities.items():
        out_string += f"""## {entity_list_name}\n"""
        for entity, grounded_entity in entity_list.items():
            out_string += f"""{entity}\n\n"""
            for k,v in grounded_entity.__dict__.items(): 
                out_string += f"""- {k}: {v}\n\n"""
            out_string += "\n"
    out_md = Path(out_md)
    out_dir = out_md.parent
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
    html_content = markdown.markdown(out_string)
    out_pdf = out_dir / (out_md.stem + ".pdf")
    pdfkit.from_string(html_content, out_pdf)
    with open(out_md, "w") as f:
        print(out_string, file = f)
    logging.info(f"Output saved to {out_md} & {out_pdf}")
    return out_string

def ground_experiment_plan(
    experiment_plan: ExperimentPlan, 
    yaml_map_path: Path,
    model: str, 
    temperature: float = 0.0
) -> ExperimentPlan:
    """Ground each field in the ExperimentPlan to ontology terms based on the yaml mapping.
    Only fields that appear in the yaml mapping will be grounded.
    Returns an updated ExperimentPlan with grounded entities.
    """
    
    # Load vector stores from yaml
    yaml_map_path = Path(yaml_map_path)
    vector_store_map = load_vector_stores_yaml(yaml_map_path)
    
    # Get the fields that should be grounded (those in the yaml mapping)
    yaml_keys = set(vector_store_map.keys())
    
    llm = get_llm(model, kwargs={'temperature': temperature})
    plan_dict = experiment_plan.dict()
    grounded_plan_dict = {}
    
    # Process each field in the experiment plan
    for field_name, value in plan_dict.items():
        if not value:  # Skip empty fields
            grounded_plan_dict[field_name] = value
            continue
            
        # Only ground fields that appear in the yaml mapping
        if field_name in yaml_keys:
            retriever = vector_store_map[field_name].as_retriever(search_kwargs={"k": RETRIEVER_TOP_K})
            
            if isinstance(value, list):
                grounded_items = []
                for item in value:
                    try:
                        # Convert any string or dict item to string for grounding
                        item_value = item['value'] if isinstance(item, dict) else str(item)
                        
                        # Get search term
                        search_term = get_search_term(entity=item_value, llm=llm)
                        
                        # Ground entity using search term
                        grounded_entity = ground_single_entity(
                            entity=item_value,
                            search_term=search_term,
                            retriever=retriever,
                            llm=llm
                        )
                        
                        grounded_items.append(GroundedItem(
                            value=item_value,
                            grounding=grounded_entity
                        ))
                    except Exception as e:
                        logging.warning(f"Failed to ground item '{item}' in field '{field_name}': {e}")
                        # If grounding fails, still include the item but without grounding
                        grounded_items.append(GroundedItem(
                            value=str(item),
                            grounding=None
                        ))
                grounded_plan_dict[field_name] = grounded_items
            else:
                grounded_plan_dict[field_name] = value
        else:
            # For fields not in yaml mapping, keep the original value
            grounded_plan_dict[field_name] = value
            
    return ExperimentPlan(**grounded_plan_dict)

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

def format_model_to_markdown(obj: BaseModel, level: int = 1) -> list[str]:
    """Convert a Pydantic model to markdown format recursively.
    
    Args:
        obj: A Pydantic model instance
        level: The current header level (1 = #, 2 = ##, etc.)
    
    Returns:
        List of markdown formatted strings
    """
    output = []
    
    # Handle different types
    if isinstance(obj, BaseModel):
        # Get all fields from the model
        for field_name, field_value in obj.dict().items():
            # Add field header
            header = "#" * level
            output.append(f"{header} {field_name.replace('_', ' ').title()}")
            output.append("")
            
            # Format the field value
            if isinstance(field_value, str):
                output.append(field_value)
            elif isinstance(field_value, list):
                if not field_value:
                    output.append("None specified")
                else:
                    for item in field_value:
                        if isinstance(item, dict) and 'value' in item:  # GroundedItem
                            output.append(f"### {item['value']}")
                            if item.get('grounding'):
                                output.append("Grounding Information:")
                                for k, v in item['grounding'].items():
                                    output.append(f"- {k.replace('_', ' ').title()}: {v}")
                        elif isinstance(item, BaseModel):
                            output.extend(format_model_to_markdown(item, level + 1))
                        else:
                            output.append(f"- {item}")
                        output.append("")
            elif isinstance(field_value, dict):
                for k, v in field_value.items():
                    output.append(f"### {k}")
                    output.append(str(v))
                    output.append("")
            elif isinstance(field_value, BaseModel):
                output.extend(format_model_to_markdown(field_value, level + 1))
            else:
                output.append(str(field_value))
            output.append("")
    
    return output

def save_markdown_and_pdf(output_parts: list[str], out_md: Path, out_pdf: Path):
    """Save markdown content to both .md and .pdf files with proper formatting."""
    # Join all parts with newlines for markdown
    out_string = "\n".join(output_parts)
    
    # Save markdown
    with open(out_md, "w") as f:
        print(out_string, file=f)
    
    # Convert to HTML with proper line breaks
    html_parts = []
    for line in output_parts:
        if line.startswith('#'):
            # Headers
            level = len(line.split()[0])
            text = ' '.join(line.split()[1:])
            html_parts.append(f"<h{level}>{text}</h{level}>")
        elif line.startswith('-'):
            # List items
            html_parts.append(f"<p>{line}</p>")
        elif line.strip() == "":
            # Empty lines
            html_parts.append("<br/>")
        else:
            # Regular text
            html_parts.append(f"<p>{line}</p>")
    
    html_content = "\n".join(html_parts)
    
    # Save PDF with proper formatting
    pdfkit.from_string(html_content, out_pdf, options={
        'margin-top': '20mm',
        'margin-right': '20mm',
        'margin-bottom': '20mm',
        'margin-left': '20mm'
    })

def parse_equipment_tsv(tsv_path: Path) -> str:
    """Parse a TSV file containing equipment/reagent information into formatted sections.
    
    Expected TSV format:
    Category    Item Name    Model/Manufacturer
    
    Returns:
        Formatted string with sections for each category
    """
    # Clean the path string of any whitespace or carriage returns
    tsv_path = Path(str(tsv_path).strip())
    tsv_path = Path(tsv_path).resolve()  # Resolve to absolute path
    
    if not tsv_path.exists():
        print(f"DEBUG: TSV path that doesn't exist: {tsv_path}")
        print(f"DEBUG: Current working directory: {Path.cwd()}")
        raise ValueError(f"TSV file not found: {tsv_path}")
        
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
            f"# Available {category} List",
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
    equipment_tsv = Path(equipment_tsv)
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
    
    # Generate the experiment plan using the hypothesis and context
    plan_template = """\
Given the Hypothesis/Research Question/Research Objective, generate a detailed structured experiment plan optimized for testing this hypothesis. Use structured reasoning to ensure feasibility, accuracy, and reproducibility. Adapt the plan based on the experiment's key priorities and constraints, including any supplied inventory list (non-exhaustive list of available equipment and material/reagents).

{format_instructions}

Input: ```{input_text}```

Response:"""

    llm = get_llm(model, kwargs={'temperature': temperature})
    
    plan_parser = PydanticOutputParser(pydantic_object=ExperimentPlan)
    plan_retry_parser = RetryOutputParser.from_llm(parser=plan_parser, llm=llm)
    
    plan_prompt = PromptTemplate(
        template=plan_template,
        input_variables=["input_text"],
        partial_variables={"format_instructions": plan_parser.get_format_instructions()}
    )
    
    plan_chain = plan_prompt | llm | StrOutputParser()
    plan_retry_chain = RunnableParallel(
        completion=plan_chain,
        prompt_value=plan_prompt
    ) | RunnableLambda(lambda x: plan_retry_parser.parse_with_prompt(**x))
    
    experiment_plan = plan_retry_chain.invoke({"input_text": input_text})
    
    # Ground the entities in the plan
    grounded_plan = ground_experiment_plan(
        experiment_plan=experiment_plan,
        yaml_map_path=yaml_map_path,
        model=model,
        temperature=temperature
    )
    
    # Generate markdown using the model-driven formatter
    output_parts = [
        # "# Input",
        # "",
        # "```",
        # input_text,
        # "```",
        # "",
        "# Generated Experiment Plan",
        ""
    ]
    
    output_parts.extend(format_model_to_markdown(grounded_plan, level=2))

    with open(output_folder / f"{prefix}_input.txt", "w") as f:
        print(input_text, file=f)
    
    # Save outputs with proper formatting
    save_markdown_and_pdf(output_parts, out_md, out_pdf)
    
    # Save JSON
    with open(out_json, "w") as f:
        json.dump(grounded_plan.dict(), f, indent=2)
    
    logging.info(f"Saved outputs to {output_folder}:")
    logging.info(f"  - Markdown: {out_md}")
    logging.info(f"  - PDF: {out_pdf}")
    logging.info(f"  - JSON: {out_json}")
    
    return "\n".join(output_parts), grounded_plan

def generate_protocol_flow(
    input_json: Path,
    model: str,
    output_folder: Path,
    prefix: str,
    equipment_tsv: Path = None,
    temperature: float = 0.0,
) -> Tuple[str, Protocol]:
    """Generate a detailed experimental protocol from a serialized experiment plan
    
    Args:
        input_json: Path to the serialized experiment plan JSON
        model: LLM model to use
        output_folder: Folder to save outputs
        prefix: Prefix for output files
        equipment_tsv: Optional path to TSV file with equipment/reagent information
        temperature: Temperature for LLM model
        
    Returns:
        Tuple of (markdown output string, protocol object)
    """
    
    # Create output directory if it doesn't exist
    output_folder = Path(output_folder)
    if equipment_tsv:
        equipment_tsv = Path(str(equipment_tsv).strip())
    if not output_folder.exists():
        output_folder.mkdir(parents=True)
    
    # Define output paths
    out_md = output_folder / f"{prefix}_protocol.md"
    out_pdf = output_folder / f"{prefix}_protocol.pdf"
    out_json = output_folder / f"{prefix}_protocol.json"
    log_file = output_folder / f"{prefix}_protocol.log"
    
    # Set up logging for this run
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    logging.info(f"Starting protocol generation workflow. Logging to {log_file}")
    
    try:
        # Read and parse the experiment plan JSON
        with open(input_json, "r") as f:
            experiment_plan_dict = json.load(f)
            experiment_plan = ExperimentPlan(**experiment_plan_dict)
        
        logging.info("Successfully loaded experiment plan from JSON")
        
        # Log information about equipment TSV if provided
        if equipment_tsv:
            if equipment_tsv.exists():
                logging.info(f"Using equipment information from: {equipment_tsv}")
            else:
                logging.warning(f"Equipment TSV file not found: {equipment_tsv}")

        # Create LLM instance
        logging.info(f"Initializing LLM model: {model} (temperature={temperature})")
        try:
            llm = get_llm(model, kwargs={'temperature': temperature})
            logging.debug("LLM initialization successful")
        except Exception as e:
            logging.error(f"Failed to initialize LLM: {e}")
            raise

        logging.info("Setting up protocol generation chain")
        try:
            # Set up the parser and prompt template
            protocol_parser = PydanticOutputParser(pydantic_object=Protocol)
            protocol_retry_parser = RetryOutputParser.from_llm(parser=protocol_parser, llm=llm)
            
            # Convert experiment plan to a format that includes grounding information in a readable way
            plan_dict = experiment_plan.dict()
            formatted_plan = {}
            for field_name, value in plan_dict.items():
                if isinstance(value, list) and value and isinstance(value[0], dict) and 'value' in value[0]:
                    # This is a list of GroundedItems
                    formatted_items = []
                    for item in value:
                        item_str = item['value']
                        if item.get('grounding'):
                            grounding = item['grounding']
                            item_str += f" [Ontology: {grounding['ontology_term']} ({grounding['ontology_id']})]"
                        formatted_items.append(item_str)
                    formatted_plan[field_name] = formatted_items
                else:
                    formatted_plan[field_name] = value
            
            # Get equipment information if provided
            equipment_info = ""
            if equipment_tsv and equipment_tsv.exists():
                equipment_info = parse_equipment_tsv(equipment_tsv)

            protocol_template = textwrap.dedent("""\
            Given the Hypothesis and Experimental Plan, generate a detailed experimental protocol optimized for a lab technician.
            The protocol should be clear, actionable, and complete.
            When materials, equipment, or controls are mentioned in the protocol, try to use the same terms that were grounded in the experiment plan.
            
            {format_instructions}

            Experiment Plan:
            ```
            {experiment_plan}
            ```
            """)
            
            # Add equipment information to the template if available
            if equipment_info:
                protocol_template += textwrap.dedent(f"""\
                Available Equipment and Materials:
                ```
                {equipment_info}
                ```
                """)
                logging.info("Added equipment and materials information to the protocol template")
            
            protocol_template += "Response:"
            
            protocol_prompt = PromptTemplate(
                template=protocol_template,
                input_variables=["experiment_plan"],
                partial_variables={"format_instructions": protocol_parser.get_format_instructions()}
            )
            
            # Create the chain
            protocol_chain = protocol_prompt | llm | StrOutputParser()
            protocol_retry_chain = RunnableParallel(
                completion=protocol_chain,
                prompt_value=protocol_prompt
            ) | RunnableLambda(lambda x: protocol_retry_parser.parse_with_prompt(**x))
            logging.debug("Protocol generation chain setup complete")
        except Exception as e:
            logging.error(f"Failed to setup protocol generation chain: {e}")
            raise

        # Generate protocol
        logging.info("Generating protocol from experiment plan")
        try:
            protocol = protocol_retry_chain.invoke({"experiment_plan": json.dumps(formatted_plan, indent=2)})
            logging.info("Protocol generation successful")
            logging.debug(f"Generated protocol with {len(protocol.steps)} steps")
        except Exception as e:
            logging.error(f"Failed to generate protocol: {e}")
            raise

        # Generate markdown output using the model-driven formatter
        logging.info("Formatting protocol output")
        try:
            output_parts = format_model_to_markdown(protocol, level=2)
            save_markdown_and_pdf(output_parts, out_md, out_pdf)
            
            # Save JSON
            with open(out_json, "w") as f:
                json.dump(protocol.dict(), f, indent=2)
            
            out_string = "\n".join(output_parts)
            logging.debug(f"Generated markdown output with {len(output_parts)} lines")
        except Exception as e:
            logging.error(f"Failed to format protocol output: {e}")
            raise

        logging.info(f"Successfully saved all outputs:")
        logging.info(f"  - Markdown: {out_md}")
        logging.info(f"  - PDF: {out_pdf}")
        logging.info(f"  - JSON: {out_json}")
        
        return out_string, protocol
        
    finally:
        # Clean up the file handler
        logging.getLogger().removeHandler(file_handler)
        file_handler.close()

###############################################################################
# Main function for command line running
###############################################################################
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

    # Subcommand for experiment plan generation
    experiment_plan_parser = subparsers.add_parser("generate_experiment_plan", help="Generate and ground an experiment plan from a hypothesis")
    experiment_plan_parser.add_argument("hypothesis", type=str, help="Input hypothesis text")
    experiment_plan_parser.add_argument("yaml_map_path", type=Path, help="Path to the YAML map of vector stores")
    experiment_plan_parser.add_argument("--context", type=str, help="Optional additional context for the hypothesis")
    experiment_plan_parser.add_argument("--model", type=str, default="openai/gpt-4o", help="LLM model to use")
    experiment_plan_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
    experiment_plan_parser.add_argument("--output_folder", type=Path, required=True, help="Folder to save outputs")
    experiment_plan_parser.add_argument("--prefix", type=str, default="experiment_plan", help="Prefix for output files")
    experiment_plan_parser.add_argument("--equipment_tsv", type=Path, help="Optional TSV file containing equipment and reagent information")

    # Subcommand for generating a detailed experimental protocol
    protocol_parser = subparsers.add_parser("generate_protocol", help="Generate a detailed experimental protocol from an experiment plan JSON")
    protocol_parser.add_argument("input_json", type=Path, help="Path to the serialized experiment plan JSON")
    protocol_parser.add_argument("--model", type=str, default="openai/gpt-4o", help="LLM model to use")
    protocol_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
    protocol_parser.add_argument("--output_folder", type=Path, required=True, help="Folder to save outputs")
    protocol_parser.add_argument("--prefix", type=str, default="protocol", help="Prefix for output files")
    protocol_parser.add_argument("--equipment_tsv", type=Path, help="Optional TSV file containing equipment and reagent information")

    return parser

def main():
    # Set up logging configuration for console output
    logging.basicConfig(
        level=logging.INFO,  # Change to logging.DEBUG for more detailed output
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    parser = get_parser()
    args = parser.parse_args()
    command_map = {
        "create_index": create_vector_store,
        "ground_hypothesis" : ground_hypothesis_flow,
        "extract_hypothesis" : extract_hypothesis_flow,
        "generate_experiment_plan" : generate_experiment_plan_flow,
        "generate_protocol" : generate_protocol_flow,
    }
    if args.command in command_map:
        command_args = {k : v for k, v in vars(args).items() if k != "command"}
        logging.info(f"Running command {args.command}")
        command_map[args.command](**command_args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

    

