###############################################################################
# gk@reder.io
###############################################################################
from operator import itemgetter
from typing import Dict, List
from pathlib import Path
import logging
import sys
import os
from tqdm.auto import tqdm
import yaml

from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.vectorstores.base import VectorStoreRetriever
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_rdf import OntologyLoader

###############################################################################
# Constants
###############################################################################
EMBEDDINGS_MODEL = "BAAI/bge-small-en-v1.5"
MAX_LENGTH = 512

###############################################################################

###############################################################################
def get_llm(model_name : str, kwargs : Dict) -> BaseChatModel:
    """Returns a Chat Model instance"""
    if model_name.startswith("ollama"):
        model_name_ollama = model_name.replace("ollama/", "")
        return ChatOllama(model=model_name_ollama, **kwargs)
    elif model_name.startswith("openai"):
        try:
            openai_api_key = os.environ["OPENAI_API_KEY"]
        except KeyError:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        model_name_openai = model_name.replace("openai/", "")
        return ChatOpenAI(model=model_name_openai, **kwargs)
    
def get_embeddings(model_name : str = EMBEDDINGS_MODEL, max_length : int = MAX_LENGTH) -> FastEmbedEmbeddings:
    embeddings = FastEmbedEmbeddings(model_name=model_name, max_length=max_length)
    
    # Workaround to get the model instantiated. 
    # See https://github.com/langchain-ai/langchain/issues/26759
    embeddings._model = embeddings.model_dump().get("_model")
    return embeddings

def load_vector_store(index_path : Path) -> VectorStoreRetriever:
    index_path = Path(index_path)
    embeddings = get_embeddings(model_name=EMBEDDINGS_MODEL, max_length=MAX_LENGTH)
    for ext in [".faiss", ".pkl"]:
        if not index_path.with_suffix(ext).exists():
            raise ValueError(f"Could not find {index_path.with_suffix(ext)}")
    vector_store = FAISS.load_local(str(index_path.parent), 
                                    index_name=index_path.stem,
                                    embeddings=embeddings, 
                                    allow_dangerous_deserialization=True)
    return vector_store
    
def load_vector_stores_yaml(yaml_map_path : Path) -> Dict[str, VectorStoreRetriever]:
    yaml_map_path = Path(yaml_map_path)
    with open(yaml_map_path, "r") as f:
        yaml_map = yaml.safe_load(f)
    embeddings = get_embeddings(model_name=EMBEDDINGS_MODEL, max_length=MAX_LENGTH)
    vector_stores = {}
    for field_name, index_name in yaml_map.items():
        index_name = Path(index_name)
        logging.info(f"Loading vector store for field {field_name} from {index_name.stem}")
        for ext in [".faiss", ".pkl"]:
            if not index_name.with_suffix(ext).exists():
                raise ValueError(f"Could not find {index_name.with_stem(ext)}")
        vector_store = FAISS.load_local(str(index_name.parent), index_name=index_name.stem, 
                                        embeddings=embeddings,
                                        allow_dangerous_deserialization=True)
        vector_stores[field_name] = vector_store
    return vector_stores

def create_vector_store(index_path : Path, owl_files : List[Path],
                        force_create : bool = False,) -> VectorStoreRetriever:
    index_path = Path(index_path)
    owl_files = [Path(owl_file) for owl_file in owl_files]
    if len(owl_files) == 0:
        raise ValueError("Must provide at least one own file to create vector store")
    embeddings = get_embeddings(model_name=EMBEDDINGS_MODEL, max_length=MAX_LENGTH)
    for ext in [".faiss", ".pkl"]:
        if index_path.with_suffix(ext).exists():
            logging.info(f"Found previously created vector store ({index_path.with_suffix(ext)})")
            if not force_create:
                raise ValueError(f"Found previously created vector store ({index_path.with_suffix(ext)}) - either create new index or set `force_create` to True to overwrite")
            else:
                logging.info(f"Overwriting existing index at {index_path}")
    
    logging.info(f"Creating new vector store from {owl_files} for index {index_path}")
    merged_vector_store = None
    for owl_file in tqdm(owl_files):
        logging.info(f"Loading ontology from {owl_file}")
        if not owl_file.exists():
            raise ValueError(f"Could not find file {owl_file}")
        loader = OntologyLoader(owl_file)
        docs = loader.load()
        vector_store_faiss = FAISS.from_documents(documents=docs, embedding=embeddings)
        ontology_store_dir = index_path.parent / f"{index_path.stem}_vector_stores"
        if not ontology_store_dir.exists():
            ontology_store_dir.mkdir(parents=True)
        logging.info(f"Saving {owl_file} vector store to {ontology_store_dir}")
        vector_store_faiss.save_local(ontology_store_dir, owl_file.stem)
        if merged_vector_store is None:
            merged_vector_store = vector_store_faiss
        else:
            logging.info("Merging with currently built vector store")
            merged_vector_store.merge_from(vector_store_faiss)
    logging.info("Saving merged vector store")
    merged_vector_store.save_local(index_path.parent, index_path.stem)
                

def main():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    ############################################################################
    # Testing creation and loading the vector store from multiple owl files
    ############################################################################
    index_dir = "/Users/gkreder/Downloads/2024-10-02_onto_rag_index"
    owl_files = [
        Path('/Users/gkreder/gdrive/medium-boat/ontologies/obi.owl'),
        Path('/Users/gkreder/gdrive/medium-boat/ontologies/so.owl')
                 ]
    
    vector_store = create_vector_store(Path(index_dir), owl_files)
    logging.info("Vector store loaded")

    ############################################################################
    # Testing queries to ensure multiple ontologies present
    ############################################################################
    obi_results = vector_store.similarity_search("RNA_Seq")
    print(f"\nOBI results (RNA_Seq):\n")
    for result in obi_results:
        print(result.metadata['uri'], result.metadata['label'])
    so_results = vector_store.similarity_search("deficient_intrachromosomal_transposition")
    print(f"\nSO results (deficient_intrachromosomal_transposition):\n")
    for result in so_results:
        print(result.metadata['uri'], result.metadata['label'])
    print('')
    

if __name__ == "__main__":
    main()
    
