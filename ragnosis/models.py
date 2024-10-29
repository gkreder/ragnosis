###############################################################################
# gk@reder.io
###############################################################################
from typing import List
from pydantic import BaseModel, Field

###############################################################################

###############################################################################
class ExperimentEntites(BaseModel):
    techniques : List[str] = Field(description="The extracted experimental " \
            "techniques/laboratory methods from the text")


class HypothesisEntities(BaseModel):
        """The entities extracted from a scientific hypothesis. The entities are divided into different categories, these field lists MUST be mutually exclusive. An entity cannot be in more than one list."""
        bio_components : List[str] = Field(description="Any generic molecular biological parts, concepts, locations, or processes (e.g. 'DNA', 'transcription', 'nucleus', 'cell cycle')")
        genes_proteins : List[str] = Field(description="Any specific genes or proteins mentioned in the hypothesis")
        taxa : List[str] = Field(description="Any species or taxonomical entities mentioned in the hypothesis")
        small_molecules : List[str] = Field(description="Any small molecules, chemical compounds, or lipids mentioned in the hypothesis (do not include proteins)")

class SearchTerm(BaseModel):
    """The search term chosen to use for finding the best-fit ontology term in a database of ontology terms"""
    search_term : str = Field(description="The search term to be used to find the best-fit ontology term")
    
class GroundedEntity(BaseModel):
    """An extracted entity from a scientific hypothesis that has been grounded to an ontology term with a score for the grounding.
    The grounding score is a measure of how well the ontology term fits the entity given the context of the scientific hypothesis. 
    The score is an integer from 1 to 5, where 1 is the worst fit and 5 is the best fit."""
    ontology_term : str = Field(description="The best-fit ontology term label")
    ontology_id : str = Field(description="The best-fit ontology term URI")
    score : int = Field(description="""The goodness of fit score from 1 to 3. Must be an integer. 
                        A score of 1 indicates an ontology term that has nothing to do with the entity.
                        A score of 2 indicates an ontology term that is somewhat related to the entity but may not fit the entity context well.
                        A score of 3 indicates an ontology term that is a perfect fit for the entity given the context of the hypothesis.""")

class GroundedEntityWithSearchTerm(GroundedEntity):
    search_term : str = Field(description="The search term used to find the best-fit ontology term")


class ExtractedHypothesis(BaseModel):
    """A hypothesis extracted from a scientific paper"""
    hypothesis : str = Field(description="The extracted hypothesis. Should be phrased as single sentence (it can be a long one if necessary)")


class HypothesisEvaluation(BaseModel):
    score: int = Field(..., ge=1, le=3)
    explanation: str
