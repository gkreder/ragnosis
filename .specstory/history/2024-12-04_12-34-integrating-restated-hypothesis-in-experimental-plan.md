## SpecStory

## Integrating Restated Hypothesis in Experimental Plan (12/4/2024, 12:34:53 PM)

_**User**_

I've added a data model `RestatedHypothesis` in models.py. In the generate experimental plan flow here, I know want to include this as part of the flow. So see how right now it takes an input and directly generates the plan from there? I want it to restate the hypothesis first then generate the plan from there. Please help me do this 

---

_**Assistant**_

I'll help you modify the `generate_experiment_plan_flow` to include hypothesis restatement before generating the plan. First, let me check the `RestatedHypothesis` model.

---

_****_

<details>
            <summary>Searched codebase "RestatedHypothesis class definition or model" • **25** results</summary>
        
| File | Lines |
|------|-------|
| `.specstory/history/adding-protocol-generation-to-codebase.md` | L190-194 |
| `.specstory/history/adding-protocol-generation-to-codebase.md` | L195-215 |
| `ragnosis/models.py` | L50-56 |
| `.specstory/history/modifying-experiment-plan-output-function.md` | L16-33 |
| `ragnosis/models.py` | L37-48 |
| `ragnosis/models.py` | L1-20 |
| `.specstory/history/adding-protocol-generation-to-codebase.md` | L166-189 |
| `ragnosis/models.py` | L70-73 |
| `.specstory/history/enhancing-experiment-plan-generation.md` | L72-97 |
| `ragnosis/models.py` | L22-35 |
| `.specstory/history/active-status-and-python-file-discussion.md` | L205-235 |
| `ragnosis/grounding.py` | L38-67 |
| `.specstory/history/integrating-ai-evaluation-into-protocol-generation.md` | L172-192 |
| `.specstory/history/enhancing-experiment-plan-generation.md` | L14-36 |
| `.specstory/history/modifying-workflow-for-experimental-plans-and-protocols.md` | L107-156 |
| `.specstory/history/modifying-workflow-for-experimental-plans-and-protocols.md` | L191-240 |
| `.specstory/history/modifying-workflow-for-experimental-plans-and-protocols.md` | L18-69 |
| `.specstory/history/adding-protocol-generation-to-codebase.md` | L152-165 |
| `.specstory/history/modifying-experiment-plan-output-function.md` | L285-306 |
| `.specstory/history/adding-experiment-plan-flow-to-grounding-py.md` | L16-41 |
| `.specstory/history/modifying-experiment-plan-output-function.md` | L251-284 |
| `.specstory/history/adding-experiment-plan-flow-to-grounding-py.md` | L1-15 |
| `.specstory/history/adding-experiment-plan-flow-to-grounding-py.md` | L138-145 |
| `.specstory/history/modifying-experiment-plan-output-function.md` | L54-128 |
| `ragnosis/grounding.py` | L92-112 |

</details>

---

_****_



I see that the `RestatedHypothesis` model has been added to `models.py`. Let me modify the `generate_experiment_plan_flow` to first restate the hypothesis before generating the plan. Here's how I'll do it:

---

_****_

```diff
  
  
- from ragnosis.models import GroundedEntity, HypothesisEntities, ExtractedHypothesis, SearchTerm, GroundedEntityWithSearchTerm, HypothesisEvaluation, ExperimentPlan, Protocol
+ from ragnosis.models import GroundedEntity, HypothesisEntities, ExtractedHypothesis, SearchTerm, GroundedEntityWithSearchTerm, HypothesisEvaluation, ExperimentPlan, Protocol, RestatedHypothesis
  from ragnosis.aux import get_llm, load_vector_stores_yaml, create_vector_store
  
      """Main flow to generate and ground an experiment plan"""
      
-     # First generate the experiment plan with entities
+     # First generate the restated hypothesis
      llm = get_llm(model, kwargs={'temperature': temperature})
      
+     restate_template = textwrap.dedent("""\
+     Given the following scientific hypothesis, restate it in a clearer and more detailed way.
+     Consider the following aspects:
+     - Enhance context-gathering: Summarize known biological mechanisms, previous related studies, and whether prior experiments have yielded conflicting or inconclusive results. Highlight key knowledge gaps this research aims to address.
+     - Clarify Sensitivity Requirements: Define acceptable detection limits, dynamic range, or measurement scales (e.g. molecular, subcellular, cellular, population level) necessary to validate the hypothesis.
+     - Identify Potential Challenges: List anticipated technical or methodological challenges based on prior research in this domain.
+ 
+     {format_instructions}
+     
+     Hypothesis: ```{hypothesis}```
+     
+     Response:""")
+     
+     restate_parser = PydanticOutputParser(pydantic_object=RestatedHypothesis)
+     restate_retry_parser = RetryOutputParser.from_llm(parser=restate_parser, llm=llm)
+     
+     restate_prompt = PromptTemplate(
+         template=restate_template,
+         input_variables=["hypothesis"],
+         partial_variables={"format_instructions": restate_parser.get_format_instructions()}
+     )
+     
+     restate_chain = restate_prompt | llm | StrOutputParser()
+     restate_retry_chain = RunnableParallel(
+         completion=restate_chain,
+         prompt_value=restate_prompt
+     ) | RunnableLambda(lambda x: restate_retry_parser.parse_with_prompt(**x))
+     
+     restated_hypothesis = restate_retry_chain.invoke({"hypothesis": input})
+     
+     # Then generate the experiment plan using the restated hypothesis
      plan_template = textwrap.dedent("""\
      Given the following scientific hypothesis, generate a detailed experiment plan to test the hypothesis. \
      {format_instructions}
      
-     Hypothesis: ```{hypothesis}```
+     Hypothesis: ```{restated_hypothesis}```
      
      Response:""")
      plan_prompt = PromptTemplate(
          template=plan_template,
-         input_variables=["hypothesis"],
+         input_variables=["restated_hypothesis"],
          partial_variables={"format_instructions": plan_parser.get_format_instructions()}
      )
      ) | RunnableLambda(lambda x: plan_retry_parser.parse_with_prompt(**x))
      
-     experiment_plan = plan_retry_chain.invoke({"hypothesis": input})
+     experiment_plan = plan_retry_chain.invoke({"restated_hypothesis": restated_hypothesis.hypothesis})
      
      # Ground the entities in the plan
      out_string = textwrap.dedent(f"""\
      # Input Hypothesis
-     
+ 
      {input}\n
+     
+     # Restated Hypothesis
+ 
+     {restated_hypothesis.hypothesis}\n
      
      # Generated Experiment Plan\n""")
```

---

_****_



I've modified the `generate_experiment_plan_flow` function to:

1. First import the `RestatedHypothesis` model from `models.py`
2. Add a new step at the beginning that restates the hypothesis using the `RestatedHypothesis` model
3. Use the restated hypothesis as input for generating the experiment plan
4. Include the restated hypothesis in the output markdown

The flow now works like this:
1. Takes the input hypothesis
2. Uses LLM to restate it in a clearer and more detailed way using the `RestatedHypothesis` model
3. Uses the restated hypothesis to generate the experiment plan
4. Grounds the entities in the plan
5. Outputs everything in a markdown format that includes:
   - Original input hypothesis
   - Restated hypothesis
   - Generated experiment plan with grounded entities

The output markdown will now show both the original and restated hypotheses before showing the experiment plan, making it easier to track how the hypothesis was refined before being used to generate the plan.

Would you like me to make any adjustments to this implementation?

---

_**User**_

Very nice, now that I look at your edits it has me thinking. Let's not even do a data model for the restated hypothesis. Let's just do it directly via text prompting. So the text prompt for the restated hypothesis can be:

```Clearly state the hypothesis, independent and dependent variables, any expected correlations,
interactions, or causal relationships

- Enhance Context-Gathering: Summarize known biological mechanisms, previous related
studies, and whether prior experiments have yielded conflicting or inconclusive results.
Highlight key knowledge gaps this research aims to address.

- Clarify Sensitivity Requirements: Define acceptable detection limits, dynamic range, or
measurement scales (e.g., molecular, subcellular, cellular, population level) necessary to
validate the hypothesis.

- Identify Potential Challenges: List anticipated technical or methodological challenges based
on prior research in this domain (e.g., detection limitations, sample constraints, equipment
availability).```

Can you modify it again so we're not using the pydantic model validation approach for this step? I think it makes more sense because the pydantic model has a simple string output anyways



---

_**Assistant**_

I'll help modify the code to use direct text prompting for the hypothesis restatement instead of using a Pydantic model.

---

_****_

```diff
      
      restate_template = textwrap.dedent("""\
-     Given the following scientific hypothesis, restate it in a clearer and more detailed way.
-     Consider the following aspects:
-     - Enhance context-gathering: Summarize known biological mechanisms, previous related studies, and whether prior experiments have yielded conflicting or inconclusive results. Highlight key knowledge gaps this research aims to address.
-     - Clarify Sensitivity Requirements: Define acceptable detection limits, dynamic range, or measurement scales (e.g. molecular, subcellular, cellular, population level) necessary to validate the hypothesis.
-     - Identify Potential Challenges: List anticipated technical or methodological challenges based on prior research in this domain.
- 
-     {format_instructions}
-     
-     Hypothesis: ```{hypothesis}```
+     Clearly state the hypothesis, independent and dependent variables, any expected correlations,
+     interactions, or causal relationships
+ 
+     - Enhance Context-Gathering: Summarize known biological mechanisms, previous related
+     studies, and whether prior experiments have yielded conflicting or inconclusive results.
+     Highlight key knowledge gaps this research aims to address.
+ 
+     - Clarify Sensitivity Requirements: Define acceptable detection limits, dynamic range, or
+     measurement scales (e.g., molecular, subcellular, cellular, population level) necessary to
+     validate the hypothesis.
+ 
+     - Identify Potential Challenges: List anticipated technical or methodological challenges based
+     on prior research in this domain (e.g., detection limitations, sample constraints, equipment
+     availability).
+ 
+     Original hypothesis: ```{hypothesis}```
  
-     Response:""")
-     
-     restate_parser = PydanticOutputParser(pydantic_object=RestatedHypothesis)
-     restate_retry_parser = RetryOutputParser.from_llm(parser=restate_parser, llm=llm)
+     Restated hypothesis:""")
      
      restate_prompt = PromptTemplate(
          template=restate_template,
-         input_variables=["hypothesis"],
-         partial_variables={"format_instructions": restate_parser.get_format_instructions()}
+         input_variables=["hypothesis"]
      )
      
      restate_chain = restate_prompt | llm | StrOutputParser()
-     restate_retry_chain = RunnableParallel(
-         completion=restate_chain,
-         prompt_value=restate_prompt
-     ) | RunnableLambda(lambda x: restate_retry_parser.parse_with_prompt(**x))
-     
-     restated_hypothesis = restate_retry_chain.invoke({"hypothesis": input})
+     restated_hypothesis = restate_chain.invoke({"hypothesis": input})
      
      # Then generate the experiment plan using the restated hypothesis
      ) | RunnableLambda(lambda x: plan_retry_parser.parse_with_prompt(**x))
      
-     experiment_plan = plan_retry_chain.invoke({"restated_hypothesis": restated_hypothesis.hypothesis})
+     experiment_plan = plan_retry_chain.invoke({"restated_hypothesis": restated_hypothesis})
      
      # Ground the entities in the plan
      # Restated Hypothesis
  
-     {restated_hypothesis.hypothesis}\n
+     {restated_hypothesis}\n
      
      # Generated Experiment Plan\n""")
```

---

_****_



I've modified the code to:

1. Remove the Pydantic model validation for the hypothesis restatement
2. Update the restatement prompt to use your provided template
3. Simplify the restatement chain to just use the LLM and string output parser
4. Update the output handling to use the raw restated hypothesis text

The changes make the code simpler and more straightforward since we're just doing text-to-text transformation for the hypothesis restatement. The Pydantic model wasn't adding much value since it was just wrapping a single string.

The flow now works like this:
1. Takes the input hypothesis
2. Uses LLM to restate it using the provided template, returning plain text
3. Uses the restated hypothesis text to generate the experiment plan (which still uses Pydantic validation since it has a more complex structure)
4. Grounds the entities in the plan
5. Outputs everything in markdown format

Would you like me to make any other adjustments to this implementation?

---

_**User**_

Ok, there's a problem now where some section headers are indented in the output MD file (both at the # and ## levels) I don't think this should be happening. can you figure out what's going on and why?

---

_**Assistant**_

The issue is likely coming from the `textwrap.dedent()` function and how we're handling the multiline strings. Let me check the output format and fix the indentation issues.

The problem is in how we're constructing the output string. When using `textwrap.dedent()`, it removes common leading whitespace from every line in the text block, but if we have inconsistent indentation in our template strings, it can lead to unexpected results.

Let me modify the code to ensure consistent indentation:

---

_****_

```diff
      llm = get_llm(model, kwargs={'temperature': temperature})
      
-     restate_template = textwrap.dedent("""\
+     restate_template = """\
  Clearly state the hypothesis, independent and dependent variables, any expected correlations,
  interactions, or causal relationships
  Original hypothesis: ```{hypothesis}```
  
-     Restated hypothesis:""")
+ Restated hypothesis:"""
      
      restate_prompt = PromptTemplate(
      
      # Then generate the experiment plan using the restated hypothesis
-     plan_template = textwrap.dedent("""\
+     plan_template = """\
  Given the following scientific hypothesis, generate a detailed experiment plan to test the hypothesis. \
  For each field, extract key entities (techniques, reagents, controls, etc.) as a list.
  Hypothesis: ```{restated_hypothesis}```
  
-     Response:""")
+ Response:"""
      
      plan_parser = PydanticOutputParser(pydantic_object=ExperimentPlan)
      )
      
-     # Generate output
-     out_string = textwrap.dedent(f"""\
-     # Input Hypothesis
- 
-     {input}\n
-     
-     # Restated Hypothesis
- 
-     {restated_hypothesis}\n
-     
-     # Generated Experiment Plan\n""")
+     # Generate output - using list of strings to ensure proper formatting
+     output_parts = [
+         "# Input Hypothesis",
+         "",
+         input,
+         "",
+         "# Restated Hypothesis",
+         "",
+         restated_hypothesis,
+         "",
+         "# Generated Experiment Plan",
+         ""
+     ]
      
      # Handle all fields from the experiment plan
      for field_name, value in experiment_plan.dict().items():
-         out_string += f"## {field_name.replace('_', ' ').title()}\n\n"
+         output_parts.append(f"## {field_name.replace('_', ' ').title()}")
+         output_parts.append("")
          
          if isinstance(value, str):
              # Handle string fields
-             out_string += f"{value}\n\n"
+             output_parts.append(value)
+             output_parts.append("")
          elif isinstance(value, list):
              # Handle list fields
              if not value:
-                 out_string += "No entities extracted\n\n"
+                 output_parts.append("No entities extracted")
+                 output_parts.append("")
                  continue
                  
              for entity in value:
-                 out_string += f"### {entity}\n"
+                 output_parts.append(f"### {entity}")
                  if field_name in grounded_plan and entity in grounded_plan[field_name]:
                      grounded_entity = grounded_plan[field_name][entity]
                      for k, v in grounded_entity.__dict__.items():
-                         out_string += f"- {k}: {v}\n"
-                 out_string += "\n"
+                         output_parts.append(f"- {k}: {v}")
+                 output_parts.append("")
+     
+     # Join all parts with newlines
+     out_string = "\n".join(output_parts)
      
      if out_md:
```

---

_****_



I've made several changes to fix the indentation issues:

1. Removed `textwrap.dedent()` from the template strings since we don't need it for the prompts
2. Changed the output generation strategy from using a single multiline string to using a list of strings that we join with newlines
3. Each markdown section header, content, and blank line is now added as a separate string to the list
4. Used `"\n".join(output_parts)` to create the final output string, which ensures consistent newlines and no unwanted indentation

This approach should ensure that:
1. All markdown headers start at column 0 (no indentation)
2. There are proper blank lines between sections
3. The content is properly formatted with consistent spacing

The indentation issues were happening because `textwrap.dedent()` was trying to handle the common leading whitespace in the multiline f-string, but

---



---

