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
from typing import Dict
import yaml

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


from ragnosis.models import GroundedEntity, HypothesisEntities, ExtractedHypothesis, SearchTerm, GroundedEntityWithSearchTerm, HypothesisEvaluation, ExperimentPlan, Protocol
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
    if not yaml_keys.issubset(experiment_plan_keys):
        raise ValueError(f"YAML contains unrecognized experiment plan object keys: {yaml_keys - experiment_plan_keys}")
    # if not experiment_plan_keys.issubset(yaml_keys):
    #     raise ValueError(f"YAML map missing required keys: {experiment_plan_keys - yaml_keys}")
    
    llm = get_llm(model, kwargs={'temperature': temperature})
    grounded_fields = {}
    
    # Ground each field's entities using the corresponding vector store
    for field_name, entities in experiment_plan.dict().items():
        if not entities:  # Skip empty fields
            continue
        if field_name not in yaml_keys: # Skip fields that shouldn't be grounded
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
    
    # First generate the restated hypothesis
    llm = get_llm(model, kwargs={'temperature': temperature})
    
    restate_template = """\
Clearly state the hypothesis, independent and dependent variables, any expected correlations,
interactions, or causal relationships

- Enhance Context-Gathering: Summarize known biological mechanisms, previous related
studies, and whether prior experiments have yielded conflicting or inconclusive results.
Highlight key knowledge gaps this research aims to address.

- Clarify Sensitivity Requirements: Define acceptable detection limits, dynamic range, or
measurement scales (e.g., molecular, subcellular, cellular, population level) necessary to
validate the hypothesis.

- Identify Potential Challenges: List anticipated technical or methodological challenges based
on prior research in this domain (e.g., detection limitations, sample constraints, equipment
availability).

Original hypothesis: ```{hypothesis}```

Restated hypothesis:"""
    
    restate_prompt = PromptTemplate(
        template=restate_template,
        input_variables=["hypothesis"]
    )
    
    restate_chain = restate_prompt | llm | StrOutputParser()
    restated_hypothesis = restate_chain.invoke({"hypothesis": input})
    
    # Then generate the experiment plan using the restated hypothesis
    plan_template = """\
Given the following scientific hypothesis, generate a detailed experiment plan to test the hypothesis. \
For each field, extract key entities (techniques, reagents, controls, etc.) as a list.

{format_instructions}

Hypothesis: ```{restated_hypothesis}```

Response:"""
    
    plan_parser = PydanticOutputParser(pydantic_object=ExperimentPlan)
    plan_retry_parser = RetryOutputParser.from_llm(parser=plan_parser, llm=llm)
    
    plan_prompt = PromptTemplate(
        template=plan_template,
        input_variables=["restated_hypothesis"],
        partial_variables={"format_instructions": plan_parser.get_format_instructions()}
    )
    
    plan_chain = plan_prompt | llm | StrOutputParser()
    plan_retry_chain = RunnableParallel(
        completion=plan_chain,
        prompt_value=plan_prompt
    ) | RunnableLambda(lambda x: plan_retry_parser.parse_with_prompt(**x))
    
    experiment_plan = plan_retry_chain.invoke({"restated_hypothesis": restated_hypothesis})
    
    # Ground the entities in the plan
    grounded_plan = ground_experiment_plan(
        experiment_plan=experiment_plan,
        yaml_map_path=yaml_map_path,
        model=model,
        temperature=temperature
    )
    
    # Generate output - using list of strings to ensure proper formatting
    output_parts = [
        "# Input Hypothesis",
        "",
        input,
        "",
        "# Restated Hypothesis",
        "",
        restated_hypothesis,
        "",
        "# Generated Experiment Plan",
        ""
    ]
    
    # Handle all fields from the experiment plan
    for field_name, value in experiment_plan.dict().items():
        output_parts.append(f"## {field_name.replace('_', ' ').title()}")
        output_parts.append("")
        
        if isinstance(value, str):
            # Handle string fields
            output_parts.append(value)
            output_parts.append("")
        elif isinstance(value, list):
            # Handle list fields
            if not value:
                output_parts.append("No entities extracted")
                output_parts.append("")
                continue
                
            for entity in value:
                output_parts.append(f"### {entity}")
                if field_name in grounded_plan and entity in grounded_plan[field_name]:
                    grounded_entity = grounded_plan[field_name][entity]
                    for k, v in grounded_entity.__dict__.items():
                        output_parts.append(f"- {k}: {v}")
                output_parts.append("")
    
    # Join all parts with newlines
    out_string = "\n".join(output_parts)
    
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

def generate_protocol_flow(
    input_md: Path,
    model: str,
    temperature: float = 0.0,
    out_md: Path = None,
) -> str:
    """Generate a detailed experimental protocol from an experiment plan markdown file"""
    
    # Set up logging for this run
    if out_md:
        out_dir = Path(out_md).parent
        if not out_dir.exists():
            out_dir.mkdir(parents=True)
        log_file = out_dir / "ragnosis_protocol.log"
    else:
        log_file = Path("ragnosis_protocol.log")
    
    # Add file handler to root logger
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s'))
    logging.getLogger().addHandler(file_handler)
    
    logging.info(f"Starting protocol generation workflow. Logging to {log_file}")
    
    try:
        # Read and parse the experiment plan markdown
        with open(input_md, "r") as f:
            experiment_plan_text = f.read()
        
        # Extract Assay Types and Organisms sections from input markdown
        assay_types_section = ""
        organisms_section = ""
        current_section = None
        
        for line in experiment_plan_text.split('\n'):
            if line.startswith('## Assay Types'):
                current_section = 'assay_types'
                continue
            elif line.startswith('## Organisms'):
                current_section = 'organisms'
                continue
            elif line.startswith('## '):
                current_section = None
                continue
            elif current_section == 'assay_types':
                assay_types_section += line + '\n'
            elif current_section == 'organisms':
                organisms_section += line + '\n'
        
        logging.debug(f"Extracted assay types section: {len(assay_types_section)} characters")
        logging.debug(f"Extracted organisms section: {len(organisms_section)} characters")

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
            
            protocol_template = textwrap.dedent("""\
            Given the following experiment plan, generate a detailed laboratory protocol that would allow a technician to execute the experiment.
            The protocol should be clear, actionable, and complete.

            {format_instructions}

            Experiment Plan:
            ```
            {experiment_plan}
            ```

            Response:""")
            
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
            protocol = protocol_retry_chain.invoke({"experiment_plan": experiment_plan_text})
            logging.info("Protocol generation successful")
            logging.debug(f"Generated protocol with {len(protocol.steps)} steps")
        except Exception as e:
            logging.error(f"Failed to generate protocol: {e}")
            raise

        # Generate markdown output
        logging.info("Formatting protocol output")
        try:
            sections = []
            
            # Add protocol sections
            for field_name, field_value in protocol.dict().items():
                section_title = field_name.replace('_', ' ').title()
                logging.debug(f"Processing section: {section_title}")
                
                if isinstance(field_value, str):
                    sections.append(f"## {section_title}\n{field_value}\n")
                elif isinstance(field_value, list):
                    items = '\n'.join([f"- {item}" for item in field_value])
                    sections.append(f"## {section_title}\n{items}\n")
            
            # Add Assay Types and Organisms sections from input if they exist
            if assay_types_section.strip():
                sections.append(f"## Assay Types\n{assay_types_section}\n")
            if organisms_section.strip():
                sections.append(f"## Organisms\n{organisms_section}\n")
            
            out_string = '\n'.join(sections)
            logging.debug(f"Generated markdown output with {len(sections)} sections")
        except Exception as e:
            logging.error(f"Failed to format protocol output: {e}")
            raise

        # Save output files if requested
        if out_md:
            logging.info(f"Saving output to {out_md}")
            try:
                out_md = Path(out_md)
                out_dir = out_md.parent
                if not out_dir.exists():
                    logging.debug(f"Creating output directory: {out_dir}")
                    out_dir.mkdir(parents=True)
                
                # Save markdown
                with open(out_md, "w") as f:
                    print(out_string, file=f)
                logging.debug(f"Saved markdown output to {out_md}")
                
                # Generate and save PDF
                logging.info("Converting to PDF")
                html_content = markdown.markdown(out_string)
                out_pdf = out_dir / (out_md.stem + ".pdf")
                pdfkit.from_string(html_content, out_pdf)
                logging.debug(f"Saved PDF output to {out_pdf}")
                
                logging.info(f"Output saved to {out_md} & {out_pdf}")
            except Exception as e:
                logging.error(f"Failed to save output files: {e}")
                raise
        
        logging.info("Protocol generation workflow completed successfully")
        return out_string
        
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
    experiment_plan_parser.add_argument("input", type=str, help="Input hypothesis text")
    experiment_plan_parser.add_argument("yaml_map_path", type=Path, help="Path to the YAML map of vector stores")
    experiment_plan_parser.add_argument("--model", type=str, default="openai/gpt-4", help="LLM model to use")
    experiment_plan_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
    experiment_plan_parser.add_argument("--out_md", type=Path, default=None, help="Output file to save the results (.md)")

    # Subcommand for generating a detailed experimental protocol
    protocol_parser = subparsers.add_parser("generate_protocol", help="Generate a detailed experimental protocol from an experiment plan markdown file")
    protocol_parser.add_argument("input_md", type=Path, help="Path to the experiment plan markdown file")
    protocol_parser.add_argument("--model", type=str, default="openai/gpt-4", help="LLM model to use")
    protocol_parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the LLM model")
    protocol_parser.add_argument("--out_md", type=Path, default=None, help="Output file to save the results (.md)")

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

    

