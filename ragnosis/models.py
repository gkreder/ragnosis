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
    """A detailed plan for an experiment that will test the given hypothesis. Adapt the plan based on the experiment’s key priorities and constraints, including any supplied inventory list (non-exhaustive list of available equipment and material/reagents). The level of detail should be sufficient for a lab technician to understand how to design and execute the experiment. Focus on defining the research goal, key variables, and general methodological approach. Do not provide step-by-step execution details at this stage. Be specific in your descriptions. Consider each part carefully and ensure no crucial details are omitted."""
    
    description: str = Field(description="A free-text description of the experiment and how it will test the hypothesis. Structure the response by outlining background information, explaining the experimental logic, and describing how it directly tests the hypothesis.")
    hypothesis: str = Field(description="A restatement of the hypothesis with clarification of assumptions and any potential sources of uncertainty.")
    context: str = Field(description="Any additional hypothesis context provided by the user or input")
    assay_types : List[GroundedItem] = Field(description="A list of the assay or assays to use in the experiment. Provide reasoning for selecting these assays based on their suitability for testing the hypothesis, considering the primary research question and potential alternatives. Adapt for any supplied inventory list (non-exhaustive list of available equipment and material/reagents). Follow relevant international guidelines and best practices.")
    objective : str = Field(description="The purpose of the experiment, specifying the effect or relationship being tested")
    organisms : List[GroundedItem] = Field(description="The model organisms to use in the experiment")
    # experimental_variables : List[GroundedItem] = Field(description="A description of the manipulated variable, including the target and modulation type. Ensure the variable is quantifiable and provide enough detail for a lab technician to understand how to manipulate it.")
    # dependent_variables : List[GroundedItem] = Field(description="An outline of the measurable outcome, specifying the target, expected change, and the readout method. Include information on how to statistically analyze the results (e.g., t-test, ANOVA). For each dependent variable, estimate the required sample size to achieve statistical significance (e.g., using power analysis tools such as GPower). Justify chosen statistical tests (e.g., t-test, ANOVA, linear regression) based on the expected data distribution and experimental setup. Provide a step-by-step outline of the statistical analysis pipeline.")
    experimental_variables : List[str] = Field(description="A list of the manipulated variables, including the target and modulation type. Ensure the variable is quantifiable and provide enough detail for a lab technician to understand how to manipulate it.")
    dependent_variables : List[str] = Field(description="A list of the measurable outcomes, specifying the target, expected change, and the readout method. Include information on how to statistically analyze the results (e.g., t-test, ANOVA). For each dependent variable, estimate the required sample size to achieve statistical significance (e.g., using power analysis tools such as GPower). Justify chosen statistical tests (e.g., t-test, ANOVA, linear regression) based on the expected data distribution and experimental setup. Provide a step-by-step outline of the statistical analysis pipeline.")
    expected_outcome: str = Field(description="A summary of the anticipated result if the hypothesis is correct. Predict the expected experimental results if the hypothesis holds true.")

class Protocol(BaseModel):
    """A highly detailed, step-by-step experimental protocol guided by the experiment plan that includes precise execution instructions, instrument settings, reagent concentrations, incubation times, and data analysis workflows. Ensure the protocol is comprehensive enough for direct execution by a lab technician. Prioritize protocol selection according to any supplied inventory list (non-exhaustive list of available equipment and material/reagents), experimental success rates, best-practice methodologies from peer-reviewed literature, and relevant international standards (e.g., MIQE for RT-qPCR, MIAME for microarray, MINSEQE for NGS). Adapt the protocol based on key priorities and constraints specified in the main hypothesis (e.g., material/reagents costs, throughput and assay sensitivity). Summarize key experimental details from at least three recent research papers (post-2015) (e.g. from PubMed, arXiv, or open-access databases), and rank methodologies based on citation count, reproducibility, study design robustness, and independent replication status. Justify the selected method by comparing advantages (e.g., sensitivity, specificity, cost) and resolving any conflicting methodologies by highlighting trade-offs and suggesting alternatives based on empirical evidence."""

    title: str = Field(description="Title of the protocol")
    hypothesis: str =  Field(description="The hypothesis the protocol is testing.")
    context: str = Field(description="Any additional hypothesis context provided by the user or input")
    description: str = Field(description="A brief description of the protocol's purpose and rationale. Justify the selection based on Sensitivity/Specificity, Feasibility (executability given common lab resources or the non-exhaustive list of material/reagents and equipment), Cost, Scale/Throughput, Reproducibility.")
    # materials_needed: List[GroundedItem] = Field(description="A list of required material/reagents, including any ontology grounding IDs such as OBI (if available). Specify brands, concentrations, sources, potential substitutes, storage conditions. Identify any safety precautions (e.g., “Wear gloves and work in a fume hood when handling chloroform”).")
    # equipment_needed: List[GroundedItem] = Field(description="A list of required equipment, including relevant ontology grounding IDs if available. Specify settings, parameters and calibration requirements for equipment (e.g. centrifugation speed and duration, excitation/emission wavelengths). Provide alternative equipment options where possible, including adjustments needed for compatibility (e.g., using alternative plate readers with modified settings for fluorescence assays). Include software tools (e.g., image analysis software, bioinformatics pipelines).")
    materials_needed: List[str] = Field(description="A list of required material/reagents, including any ontology grounding IDs such as OBI (if available). Specify brands, concentrations, sources, potential substitutes, storage conditions. Identify any safety precautions (e.g., “Wear gloves and work in a fume hood when handling chloroform”).")
    equipment_needed: List[str] = Field(description="A list of required equipment, including relevant ontology grounding IDs if available. Specify settings, parameters and calibration requirements for equipment (e.g. centrifugation speed and duration, excitation/emission wavelengths). Provide alternative equipment options where possible, including adjustments needed for compatibility (e.g., using alternative plate readers with modified settings for fluorescence assays). Include software tools (e.g., image analysis software, bioinformatics pipelines).")
    steps: List[str] = Field(description="A fully detailed, numbered step-by-step protocol with specific execution instructions. Include reagent preparation (concentrations, volumes), instrument settings (e.g., centrifuge speeds, fluorescence excitation/emission wavelengths, microscope objectives), sample handling steps, incubation conditions (times, temperatures), and data collection parameters. Assume the lab technician is executing this protocol directly. Include any required quality controls, validation steps, and recommended practices to ensure reproducibility. Before finalizing the protocol, check for logical consistency between experimental steps (e.g., ensuring reagents are prepared before use, incubation times are adequate, and steps follow an appropriate sequence). Explicitly flag and correct any inconsistencies. Assume no prior knowledge beyond standard lab experience of a technician.")
    # controls: List[GroundedItem] = Field(description="Positive, negative, and technical controls for the experiment.")
    controls: List[str] = Field(description="Positive, negative, and technical controls for the experiment.")
    explicit_error_handling: List[str] = Field(description="Identify common failure points, troubleshooting solutions, and optimizations for reproducibility and accuracy. Address sample variability, equipment inconsistencies, and reagent lot differences. Suggest alternative approaches if specific reagents or equipment are unavailable. Provide strategies for minimizing errors and improving data quality.")
    appendix: List[str] = Field(description="Summarize relevant literature supporting the protocol selection, prioritizing studies with high reproducibility, peer-reviewed validation, and independent replication. Highlight any known limitations or biases in existing methods. Specify web links to external resources where further specific information can be obtained (e.g. reagent product manuals, machine operating manuals).")
    
    

