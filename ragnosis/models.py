###############################################################################
# gk@reder.io
###############################################################################
from typing import List, Optional
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

class ExperimentPlan(BaseModel):
    """A plan for an experiment that will test the given hypothesis. The following seven parts are necessary when you suggest experimental validation for the hypothesis. It is important that the level of detail is sufficient for a graduate student to understand how to go about designing the experiment. Be specific in your descriptions. Consider each part and whether anything is missing or could be unclear to a graduate student. """
    description: str = Field(description="A free-text description of the experiment and how it will test the hypothesis")
    hypothesis: str = Field(description="A restating of the hypothesis")
    assay_types : List[str] = Field(description="The assay(s) to use in the experiment")
    objective : str = Field(description="A definition of the purpose of the experiment, including the effect or relationship being tested")
    organisms : List[str] = Field(description="The model organisms to use in the experiment")
    experimental_variables : List[str] = Field(description="A description of the manipulated/perturbed/altered factor, including the target and the modulation type. Ensure that this variable contains enough detail to understand the EXACT component being altered/perturbed/manipulated. It should be very clear how to go about designing the experiment for a graduate student.")
    dependent_variables : List[str] = Field(description="An outline of the measurable outcome, specifying the target, expected change, and readout method.")
    expected_outcome: str = Field(description="A summary of the anticipated result if the hypothesis is correct. What do we expect of this experiment if the hypothesis is valid?")
    # background_knowledge: List[str] = Field(description="Known biological pathways and contextual information entities")
    # resources: List[str] = Field(description="Instruments, reagents, and other resource entities needed")
    # controls: List[str] = Field(description="Positive and negative control entities for the experiment")
    # statistical_approach: List[str] = Field(description="Sample size, replication, precision, and criteria entities")
    # potential_pitfalls: List[str] = Field(description="Potential challenge entities in experiment design")

class Protocol(BaseModel):
    """A detailed experimental protocol derived from an experiment plan. Each step should be clear and actionable. The protocol should have enough detail that a graduate student could easily execute it."""
    title: str = Field(description="Title of the protocol")
    hypothesis: str =  Field(description="The hypothesis the protocol is testing")
    description: str = Field(description="Brief description of the protocol's purpose and reasoning")
    materials_needed: List[str] = Field(description="List of required materials and reagents, including any ontology grounding IDs if provided")
    equipment_needed: List[str] = Field(description="List of required equipment, including any ontology grounding IDs if provided")
    steps: List[str] = Field(description="Detailed step-by-step instructions. Each step should be clear and actionable.")
    

