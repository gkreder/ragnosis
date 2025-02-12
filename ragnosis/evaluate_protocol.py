from typing import Dict, List
from pathlib import Path
from pydantic import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser, RetryOutputParser
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel
import json

from ragnosis.aux import get_llm
from ragnosis.models import Protocol

class ProtocolEvaluation(BaseModel):
    """Evaluation results for a laboratory protocol"""
    clarity_score: int = Field(
        description="Score from 1-5 indicating how clear and unambiguous the protocol steps are",
        ge=1, le=5
    )
    completeness_score: int = Field(
        description="Score from 1-5 indicating how complete the protocol is in terms of materials, equipment, and steps",
        ge=1, le=5
    )
    sensibility_score: int = Field(
        description="Score from 1-5 indicating how much the protocol makes sense. Does one step follow logically from the previous step? Does the protocol represent a complete set of steps that will succesfully test the hypothesis?",
        ge=1, le=5
    )
    executability_score: int = Field(
        description="Score from 1-5 evaluating if the protocol can be executed in the average yeast biology lab given the equipment needed. A score of 5 indicates that the protocol can easily be executed in an average yeast biology lab given its equipment. A score of 1 indicates that it would be impossible to execute in an average yeast biology lab.",
        ge=1, le=5
    )
    executability_reasoning: str = Field(
        description="Your reasoning behind the executability score."
    )
    feedback: str = Field(
        description="Detailed feedback on the protocol's strengths and weaknesses"
    )
    improvement_suggestions: List[str] = Field(
        description="Specific suggestions for improving the protocol"
    )

def evaluate_protocol(protocol_json_path: Path, model: str = "openai/gpt-4", temperature: float = 0.0) -> Dict:
    """
    Evaluates a protocol JSON file for executability and clarity.
    
    Args:
        protocol_json_path: Path to the protocol JSON file (output from generate_protocol_flow)
        model: The LLM model to use for evaluation
        temperature: Temperature parameter for the LLM
        
    Returns:
        Dictionary containing evaluation metrics and feedback
    """
    # Create LLM instance
    llm = get_llm(model, kwargs={'temperature': temperature})
    
    # Read and parse the protocol JSON
    with open(protocol_json_path, 'r') as f:
        protocol_dict = json.load(f)
        protocol = Protocol(**protocol_dict)
    
    # Convert protocol to a formatted string for evaluation
    protocol_content = []
    for field_name, field_value in protocol.dict().items():
        section_title = field_name.replace('_', ' ').title()
        protocol_content.append(f"## {section_title}")
        
        if isinstance(field_value, str):
            protocol_content.append(field_value)
        elif isinstance(field_value, list):
            for item in field_value:
                protocol_content.append(f"- {item}")
        protocol_content.append("")
    
    protocol_text = "\n".join(protocol_content)
    
    # Construct the evaluation prompt
    evaluation_template = """Please evaluate the following laboratory protocol for executability and clarity.
    Focus on these aspects:
    1. Are all steps clearly defined and unambiguous?
    2. Are all required materials and equipment listed?
    3. Are quantities and measurements specific and precise?
    4. Are there any safety considerations that need to be addressed?
    5. Are there any potential points of failure or ambiguity?

    {format_instructions}

    Protocol:
    ```
    {protocol_content}
    ```

    Evaluation:"""
    
    # Set up the parser
    evaluation_parser = PydanticOutputParser(pydantic_object=ProtocolEvaluation)
    evaluation_retry_parser = RetryOutputParser.from_llm(parser=evaluation_parser, llm=llm)
    
    # Create the prompt
    evaluation_prompt = PromptTemplate(
        template=evaluation_template,
        input_variables=["protocol_content"],
        partial_variables={"format_instructions": evaluation_parser.get_format_instructions()}
    )
    
    # Create the chain
    evaluation_chain = evaluation_prompt | llm | StrOutputParser()
    evaluation_retry_chain = RunnableParallel(
        completion=evaluation_chain,
        prompt_value=evaluation_prompt
    ) | RunnableLambda(lambda x: evaluation_retry_parser.parse_with_prompt(**x))
    
    # Run the evaluation
    evaluation_results = evaluation_retry_chain.invoke({"protocol_content": protocol_text})
    
    return evaluation_results.dict()

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Evaluate a protocol for executability")
    parser.add_argument("protocol_json_path", type=Path, help="Path to the protocol JSON file")
    parser.add_argument("--model", default="openai/gpt-4", help="Model to use for evaluation")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the model")
    parser.add_argument("--out_json", type=Path, help="Optional path to save evaluation results as JSON")
    
    args = parser.parse_args()
    
    results = evaluate_protocol(args.protocol_json_path, args.model, args.temperature)
    
    if args.out_json:
        with open(args.out_json, 'w') as f:
            json.dump(results, f, indent=2)
    else:
        print(json.dumps(results, indent=2))

