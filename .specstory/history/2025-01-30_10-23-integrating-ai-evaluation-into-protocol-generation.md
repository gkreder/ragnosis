## SpecStory

## Integrating AI Evaluation into Protocol Generation (1/30/2025, 10:23:57 AM)

_**User**_

Take a look at this file. Here I'm running experiment plan generation on 5 input files to produce protocol outputs. I want to have a similar workflow but I want to additionally have an AI agent evaluate the resulting protocols in terms of executability. Can we add this in? I may need to create additional Python files etc

---

_**Assistant**_

I'll help you modify the script to include protocol evaluation. We'll need to create a new Python module for the evaluation functionality and then update the shell script to include this step.

First, let's create a new Python module for protocol evaluation. I suggest creating this file:

```python:/Users/gkreder/ragnosis/ragnosis/grounding/evaluate_protocol.py
from typing import Dict
from pathlib import Path

def evaluate_protocol(protocol_path: str, model: str = "openai/gpt-4", temperature: float = 0.0) -> Dict:
    """
    Evaluates a protocol markdown file for executability and clarity.
    
    Args:
        protocol_path: Path to the protocol markdown file
        model: The LLM model to use for evaluation
        temperature: Temperature parameter for the LLM
        
    Returns:
        Dictionary containing evaluation metrics and feedback
    """
    # Read the protocol
    with open(protocol_path, 'r') as f:
        protocol_content = f.read()
    
    # Construct the evaluation prompt
    evaluation_prompt = f"""Please evaluate the following laboratory protocol for executability and clarity.
    Focus on these aspects:
    1. Are all steps clearly defined and unambiguous?
    2. Are all required materials and equipment listed?
    3. Are quantities and measurements specific and precise?
    4. Are there any safety considerations that need to be addressed?
    5. Are there any potential points of failure or ambiguity?

    Protocol:
    {protocol_content}

    Provide your evaluation in a structured format.
    """
    
    # TODO: Implement your LLM call here using your existing infrastructure
    # This should match how you're making LLM calls in generate_protocol
    
    # For now, returning a mock response
    return {
        "executability_score": 0.0,
        "clarity_score": 0.0,
        "feedback": "",
        "improvement_suggestions": []
    }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate a protocol for executability")
    parser.add_argument("protocol_path", help="Path to the protocol markdown file")
    parser.add_argument("--model", default="openai/gpt-4", help="Model to use for evaluation")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the model")
    parser.add_argument("--out_json", help="Optional path to save evaluation results as JSON")
    
    args = parser.parse_args()
    
    results = evaluate_protocol(args.protocol_path, args.model, args.temperature)
    
    if args.out_json:
        import json
        with open(args.out_json, 'w') as f:
            json.dump(results, f, indent=2)
    else:
        print(json.dumps(results, indent=2))
```

Now, let's modify your shell script to include the evaluation step:

```shell:/Users/gkreder/scripts/medium-boat/2025-01-23_abbi-test/1-5.sh
cd /Users/gkreder/ragnosis
export PYTHONPATH=$PYTHONPATH:/Users/gkreder/ragnosis

# Process protocols for hypotheses 1 through 5
for i in {1..5}; do
    echo "Processing protocol for hypothesis $i..."
    
    # Define input and output paths
    input_md="/Users/gkreder/scripts/medium-boat/2024-12-17_abbi-test/output/$i.md"
    output_md="/Users/gkreder/scripts/medium-boat/2025-01-23_abbi-test/output/${i}_protocol.md"
    eval_json="/Users/gkreder/scripts/medium-boat/2025-01-23_abbi-test/output/${i}_evaluation.json"
    
    # Create output directory if it doesn't exist
    output_dir=$(dirname "$output_md")
    mkdir -p "$output_dir"
    
    # Check if input file exists
    if [ ! -f "$input_md" ]; then
        echo "Warning: Input file $input_md does not exist. Skipping..."
        continue
    fi
    
    # Generate protocol from experiment plan
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding generate_protocol \
    "$input_md" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_md "$output_md"
    
    # Evaluate the generated protocol
    echo "Evaluating protocol for hypothesis $i..."
    /Users/gkreder/medium-boat/.pixi/envs/langchain/bin/python -m ragnosis.grounding.evaluate_protocol \
    "$output_md" \
    --model "openai/gpt-4" \
    --temperature 0.0 \
    --out_json "$eval_json"
    
    echo "Completed processing and evaluation for hypothesis $i"
    echo "----------------------------------------"
done

echo "All protocols generated and evaluated successfully!"
```

The main changes I've made are:

1. Created a new Python module `evaluate_protocol.py` that will handle the evaluation of protocols. You'll need to implement the actual LLM call using your existing infrastructure, but I've provided the basic structure.

2. Modified the shell script to:
   - Add a new output path for evaluation results (`eval_json`)
   - Add a new step that calls the evaluation module after generating each protocol
   - Update the output messages to reflect the additional evaluation step

To use this:

1. Save the new Python module in your ragnosis package directory
2. Update the evaluate_protocol.py implementation to use your actual LLM calling infrastructure
3. Run the modified shell script

The evaluation results will be saved as JSON files alongside your protocol markdown files, making it easy to review the AI's assessment of each protocol's executability and clarity.

Would you like me to explain any part of this in more detail or help with implementing the LLM call in the evaluation module?

---

_**User**_

Great, I've added these to files. Take a look at this workflow file and the @ragnosis code base with the updated file in it to make sure both the new `evalulate_protocol.py` file looks ok and so does this workflow

---

_**Assistant**_

Looking at the codebase, I can help improve the `evaluate_protocol.py` implementation to better integrate with your existing infrastructure. Here's how I would modify it:

````python:ragnosis/evaluate_protocol.py
from typing import Dict
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser, RetryOutputParser
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers.string import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel

from ragnosis.aux import get_llm

class ProtocolEvaluation(BaseModel):
    """Evaluation results for a laboratory protocol"""
    clarity_score: int = Field(
        description="Score from 1-3 indicating how clear and unambiguous the protocol steps are",
        ge=1, le=3
    )
    completeness_score: int = Field(
        description="Score from 1-3 indicating how complete the protocol is in terms of materials, equipment, and steps",
        ge=1, le=3
    )
    safety_score: int = Field(
        description="Score from 1-3 indicating how well safety considerations are addressed",
        ge=1, le=3
    )
    feedback: str = Field(
        description="Detailed feedback on the protocol's strengths and weaknesses"
    )
    improvement_suggestions: List[str] = Field(
        description="Specific suggestions for improving the protocol"
    )

def evaluate_protocol(protocol_path: str, model: str = "openai/gpt-4", temperature: float = 0.0) -> Dict:
    """
    Evaluates a protocol markdown file for executability and clarity.
    
    Args:
        protocol_path: Path to the protocol markdown file
        model: The LLM model to use for evaluation
        temperature: Temperature parameter for the LLM
        
    Returns:
        Dictionary containing evaluation metrics and feedback
    """
    # Create LLM instance
    llm = get_llm(model, kwargs={'temperature': temperature})
    
    # Read the protocol
    with open(protocol_path, 'r') as f:
        protocol_content = f.read()
    
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
    evaluation_results = evaluation_retry_chain.invoke({"protocol_content": protocol_content})
    
    return evaluation_results.dict()

if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Evaluate a protocol for executability")
    parser.add_argument("protocol_path", help="Path to the protocol markdown file")
    parser.add_argument("--model", default="openai/gpt-4", help="Model to use for evaluation")
    parser.add_argument("--temperature", type=float, default=0.0, help="Temperature for the model")
    parser.add_argument("--out_json", help="Optional path to save evaluation results as JSON")
    
    args = parser.parse_args()
    
    results = evaluate_protocol(args.protocol_path, args.model, args.temperature)
    
    if args.out_json:
        with open(args.out_json, 'w') as f:
            json.dump(results, f, indent=2)
    else:
        print(json.dumps(results, indent=2))
````

The key improvements I've made are:

1. Added a proper `ProtocolEvaluation` Pydantic model to match your existing code style and provide structured output
2. Integrated with your existing `get_llm` infrastructure from `aux.py`
3. Used the LangChain patterns you're using elsewhere in the codebase (PromptTemplate, PydanticOutputParser, etc.)
4. Added more specific scoring categories (clarity, completeness, safety)
5. Structured the evaluation chain similar to your other flows

The workflow script looks good as is - it's correctly calling the new evaluation module. The evaluation will now provide more structured feedback with numerical scores and specific improvement suggestions.

Would you like me to explain any part of the implementation in more detail or make any adjustments to better match your needs?

---

_**User**_

Very nice, now given the output in the folder @2025-01-30_tests I want to have an additional script that will plot the score results per protocol. Also ideally in the plot I should be able to click a hyperlink in the plot to the protocol itself and the protocol's evaluation. Can you do this for me?

---

_****_

Very nice, now given the output in the folder @2025-01-30_tests I want to have an additional script that will plot the score results per protocol. Also ideally in the plot I should be able to click a hyperlink in the plot to the protocol itself and the protocol's evaluation. Can you do this for me?

---



---

