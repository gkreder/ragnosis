###############################################################################
# gk@reder.io
###############################################################################
import logging
import textwrap
from pathlib import Path
import argparse
import sys
import os
from tqdm.auto import tqdm
import markdown
import pdfkit
import json
from typing import Dict
import yaml

from langchain.output_parsers import PydanticOutputParser, RetryOutputParser
from langchain_core.output_parsers.string import StrOutputParser
from langchain.prompts.prompt import PromptTemplate
from langchain.schema import format_document
from langchain_core.runnables import RunnableLambda, RunnablePassthrough, RunnableParallel
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_core.vectorstores.base import VectorStoreRetriever

from ragnosis.models import GroundedEntity, HypothesisEntities, ExtractedHypothesis, SearchTerm, GroundedEntityWithSearchTerm, HypothesisEvaluation
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
    
    # Note we're creating a new LLM instance here for grounding, but we could use the same one as for extraction
    llm = get_llm(model, kwargs={'temperature' : temperature})


    grounding_template = textwrap.dedent("""\
    Given the following entity extracted from a scientific hypothesis \
    find the best-fit ontology term to ground this entity. Use your \
    best judgement to select the most apt term from the ontology. \
    Use the original hypothesis to provide context for the grounding and your scoring. \
    Make sure to read the entire original hypothesis to make an informed decision for the best retrieved ontology term. \
                                         
    Base your decision ONLY on the retrieved ontology context below (retrieved terms in the available ontologies). 
        
    retrieved context : ```{context}```
        
                                         
    {format_instructions}
                                              
                                         
    Entity: ```{entity}```
                                         
    Original hypothesis: ```{user_input}```
                                         
    Response:""")

    search_term_template = textwrap.dedent("""\
    Given the following entity extracted from a scientific hypothesis, \
    decide on a search term that will be used to retrieve the most appropriate ontology term \
    for the specific entity in the hypothesis from a database of ontology terms. \
    Read the original hypothesis to make an informed decision on a database search term. \
    Your decided search term may be the same as the entity, or it may be a more general/specific term. \

    {format_instructions}

    Original hypothesis: ```{user_input}```
                                           
    Entity: ```{entity}```
    
    Response:""")
    
    document_format_prompt = PromptTemplate.from_template(
        template="Concept label: {page_content} | URI: {uri} | \
            Type: {type} | Predicate: {predicate} | Ontology: {ontology}"
    )

    def _combine_documents(
        docs, document_prompt=document_format_prompt, document_separator="\n\n"
    ):
        doc_strings = [format_document(doc, document_prompt) for doc in docs]
        return document_separator.join(doc_strings)
    

    grounding_parser = PydanticOutputParser(pydantic_object=GroundedEntity)
    grounding_retry_parser = RetryOutputParser.from_llm(parser=grounding_parser, llm=llm)
    search_term_parser = PydanticOutputParser(pydantic_object=SearchTerm)
    search_term_retry_parser = RetryOutputParser.from_llm(parser=search_term_parser, llm=llm)
    
    grounded_entities = {}
    response_items = entity_extraction_response.dict().items()
    logging.info(f"Grounding extracted entities ({len(response_items)} entity lists)")
    for entity_list_name, entity_list in response_items:
        logging.info(f"Grounding {entity_list_name}")
        retriever = vector_store_map[entity_list_name].as_retriever(search_kwargs={"k": RETRIEVER_TOP_K})
        temp_grounding = {}
        for entity in entity_list:

            search_term_prompt = PromptTemplate(
                template=search_term_template,
                input_variables=["entity"],
                partial_variables={"format_instructions":search_term_parser.get_format_instructions(),
                                "entity" : entity,
                                "user_input" : input,
                                }
            )
            
            search_term_instance = search_term_prompt | llm | StrOutputParser()
            search_term_retry_instance = RunnableParallel(
                completion=search_term_instance, prompt_value=search_term_prompt
                ) | RunnableLambda(lambda x: search_term_retry_parser.parse_with_prompt(**x))
            search_term = search_term_retry_instance.invoke({"entity" : entity})

            grounding_prompt = PromptTemplate(
                template=grounding_template,
                input_variables=["entity"],
                partial_variables={"format_instructions":grounding_parser.get_format_instructions(),
                                "context" : _combine_documents(retriever.invoke(search_term.search_term)),
                                "user_input" : input,
                                }
            )
            grounding_chain_instance = grounding_prompt | llm | StrOutputParser()
            grounding_retry_instance = RunnableParallel(
                completion=grounding_chain_instance, prompt_value=grounding_prompt
                ) | RunnableLambda(lambda x: grounding_retry_parser.parse_with_prompt(**x))
            grounded_entity = grounding_retry_instance.invoke({"entity" : entity})
            grounded_entity_with_search_term = GroundedEntityWithSearchTerm(**grounded_entity.dict(), search_term=search_term.search_term)
            temp_grounding[entity] = grounded_entity_with_search_term
        grounded_entities[entity_list_name] = temp_grounding
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


def evaluate_hypothesis_flow(reference_hypothesis: str, test_hypothesis: str, 
                             model: str, temperature: float = 0.0,
                             out_md: Path = None) -> HypothesisEvaluation:
    llm = get_llm(model, kwargs={'temperature': temperature})
    
    evaluation_template = textwrap.dedent("""\
    Compare the following two scientific hypotheses and evaluate how well the test hypothesis fits the reference hypothesis.
    
    Reference Hypothesis: ```{reference_hypothesis}```
                                          
    Test Hypothesis: ```{test_hypothesis}```
    
    Provide a score from 1 to 3, where:
    1 = Poor fit (significant differences or missing key elements)
    2 = Moderate fit (some similarities but notable differences)
    3 = Excellent fit (very similar or equivalent hypotheses)
    
    {format_instructions}
    
    Evaluation:
    """)

    evaluation_parser = PydanticOutputParser(pydantic_object=HypothesisEvaluation)
    evaluation_prompt = PromptTemplate(
        template=evaluation_template,
        input_variables=["reference_hypothesis", "test_hypothesis"],
        partial_variables={'format_instructions': evaluation_parser.get_format_instructions()}
    )

    retry_parser = RetryOutputParser.from_llm(parser=evaluation_parser, llm=llm)
    chain = evaluation_prompt | llm | StrOutputParser()
    retry_chain = RunnableParallel(
        completion=chain, prompt_value=evaluation_prompt
    ) | RunnableLambda(lambda x: retry_parser.parse_with_prompt(**x))

    evaluation = retry_chain.invoke({
        "reference_hypothesis": reference_hypothesis,
        "test_hypothesis": test_hypothesis
    })

    print(f"Score: {evaluation.score}")
    print(f"Explanation: {evaluation.explanation}")
    
    if out_md:
        out_md = Path(out_md)
        out_dir = out_md.parent
        if not out_dir.exists():
            out_dir.mkdir(parents=True)
        
        out_string = f"""# Hypothesis Evaluation

## Reference Hypothesis

{reference_hypothesis}

## Test Hypothesis

{test_hypothesis}

## Evaluation

- Score: {evaluation.score}
- Explanation: {evaluation.explanation}
"""
        
        with open(out_md, "w") as f:
            f.write(out_string)
        
        logging.info(f"Output saved to {out_md}")

    return evaluation

###############################################################################
# Main function for command line running
###############################################################################
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

if __name__ == "__main__":
    main()

