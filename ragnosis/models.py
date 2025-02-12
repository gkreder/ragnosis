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

class GroundedItem(BaseModel):
    """An item that may be grounded to an ontology term"""
    value: str = Field(description="The original value/text of the item")
    grounding: Optional[GroundedEntityWithSearchTerm] = Field(description="The grounding information if this item has been grounded to an ontology term", default=None)

class ExtractedHypothesis(BaseModel):
    """A hypothesis extracted from a scientific paper"""
    hypothesis : str = Field(description="The extracted hypothesis. Should be phrased as single sentence (it can be a long one if necessary)")


class HypothesisEvaluation(BaseModel):
    score: int = Field(..., ge=1, le=3)
    explanation: str

class ExperimentPlan(BaseModel):
    """A detailed plain for an experiment that will test the given hypothesis. The level of detail should be sufficient for a lab technician to understand how ot design and execute the experiment. be specific in your descriptions. Consider each part carefully and ensure no crucial details are omitted, making it easy to implement for students with relevant experience."""
    
    """A plan for an experiment that will test the given hypothesis. The following seven parts are necessary when you suggest experimental validation for the hypothesis. It is important that the level of detail is sufficient for a graduate student to understand how to go about designing the experiment. Be specific in your descriptions. Consider each part and whether anything is missing or could be unclear to a graduate student. """
    description: str = Field(description="A free-text description of the experiment and how it will test the hypothesis. Structure response using background, experimental logic and how it directly tests the Hypothesis.")
    hypothesis: str = Field(description="The entire hypothesis as it was provided by the user via the input. No parts should be omitted.")
    context: str = Field(description="Any additional hypothesis context provided by the user or input")
    assay_types : List[GroundedItem] = Field(description="The assay(s) to use in the experiment. Justify why these assays are ideal for testing the hypothesis and consider potential alternatives.")
    objective : str = Field(description="The purpose of the experiment, specifying the effect or relationship being tested")
    organisms : List[GroundedItem] = Field(description="The model organisms to use in the experiment")
    experimental_variables : List[GroundedItem] = Field(description="A description of the manipulated/perturbed/altered factor, including the target and the modulation type. Ensure that this variable is quantifiable and provide enough detail for a lab technician to understand how to manipulate it.")
    dependent_variables : List[GroundedItem] = Field(description="An outline of the measurable outcome, specifying the target, expected change, and readout method. Include information on how to statistically analyze the result s(e.g., t-test, ANOVA).")
    expected_outcome: str = Field(description="A summary of the anticipated result if the hypothesis is correct. Provide a prediction of what the experiment should demonstrate if the hypothesis is valid.")

class Protocol(BaseModel):
    """A detailed experimental protocol derived from the experiment plan. Ensure it follows published methodologies in yeast biology for similar research hypotheses or objectives. Integrate the most reliable methods in the published methodologies while adhering to best practices. If conflicting methodologies exist, choose according to highest citation count and experimental success rate. When two methods appear equally valid, prioritize reproducibility. Each step should be clear and actionable, and the protocol should contain enough detail for a laboratory technician to easily execute it."""
    title: str = Field(description="Title of the protocol")
    hypothesis: str =  Field(description="The original input hypothesis the protocol is testing. No content should be omitted.")
    context: str = Field(description="Any additional hypothesis context provided by the user or input")
    description: str = Field(description="A brief description of the protocol's purpose and rationale. Justify the selection based on Sensitivity/Specificity, Feasibility (executability given common lab resources), Cost, Reproducibility.")
    materials_needed: List[GroundedItem] = Field(description="List of required materials and reagents, including any ontology grounding IDs if provided. Specify concentrations, sources, potential substitutes.")
    equipment_needed: List[GroundedItem] = Field(description="List of required equipment, including any ontology grounding IDs if provided. Specify calibration/operational settings and any equipment alternatives.")
    steps: List[str] = Field(description="Detailed step-by-step instructions, each clear and actionable. Include incubation times/temperatures. Include expected outcomes for each step.")
    controls: List[GroundedItem] = Field(description="Positive, negative, and technical controls for the experiment.")
    explicit_error_handling: List[str] = Field(description="For any conflicting or missing information, suggest alternatives, and flag uncertainty.")
    appendix: List[str] = Field(description="A brief literature summary with references when suggesting protocols, rankings them by citation count and reproducibility metrics.")
    

