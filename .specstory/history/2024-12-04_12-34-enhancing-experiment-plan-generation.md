## SpecStory

## Enhancing Experiment Plan Generation (12/4/2024, 12:34:53 PM)

_**User**_

I'm working on the `generate_experiment_plan_flow` and it's looking pretty good so far. I want to modify though in the following manner. See how the flow relies on the `ExperimentPlan` class? I'd like to include the plain-text description field (that's currently commented out). I need this to show up in the generated pdf/md output in the correct format, along with the current output that is correctly formatted already

---

_**Assistant**_

I'll help you modify the `generate_experiment_plan_flow` to include the plain-text description field. First, let's uncomment and update the description field in the `ExperimentPlan` class in models.py:

```python:ragnosis/models.py
class ExperimentPlan(BaseModel):
    """A plan for an experiment that will test the given hypothesis"""
    description: str = Field(description="A free-text description of the experiment and how it will test the hypothesis")
    background_knowledge: List[str] = Field(description="Known biological pathways and contextual information entities")
    resources: List[str] = Field(description="Instruments, reagents, and other resource entities needed")
    controls: List[str] = Field(description="Positive and negative control entities for the experiment")
    statistical_approach: List[str] = Field(description="Sample size, replication, precision, and criteria entities")
    potential_pitfalls: List[str] = Field(description="Potential challenge entities in experiment design")
```

Then, we need to modify the output string generation in `generate_experiment_plan_flow` to include the description field before the other fields. Here's how we should modify the output string generation part:

```python:ragnosis/grounding.py
out_string = textwrap.dedent(f"""\
# Input Hypothesis

{input}\n

# Generated Experiment Plan

## Description

{experiment_plan.description}\n

## Detailed Components\n""")

for field_name, entities in experiment_plan.dict().items():
    if field_name == "description":  # Skip description as it's already handled
        continue
        
    out_string += f"### {field_name}\n"
    if not entities:
        out_string += "No entities extracted\n\n"
        continue
        
    for entity in entities:
        out_string += f"#### {entity}\n"
        if entity in grounded_plan.get(field_name, {}):
            grounded_entity = grounded_plan[field_name][entity]
            for k, v in grounded_entity.__dict__.items():
                out_string += f"- {k}: {v}\n"
        out_string += "\n"
```

This modification will:
1. Uncomment and enable the description field in the `ExperimentPlan` model
2. Add a dedicated "Description" section at the start of the experiment plan output
3. Keep all the existing entity grounding output under a "Detailed Components" section
4. Skip the description field when iterating through the grounded entities

The output will now be formatted as:
```markdown
# Input Hypothesis
[hypothesis text]

# Generated Experiment Plan

## Description
[plain text description of the experiment plan]

## Detailed Components

### background_knowledge
[grounded entities...]

### resources
[grounded entities...]
...
```

The relevant code blocks I referenced are:

```50:57:ragnosis/models.py
class ExperimentPlan(BaseModel):
    """A plan for an experiment that will test the given hypothesis"""
    # description : str = Field(description="A free-text description of the experiment and how it will test the hypothesis")
    background_knowledge: List[str] = Field(description="Known biological pathways and contextual information entities")
    resources: List[str] = Field(description="Instruments, reagents, and other resource entities needed")
    controls: List[str] = Field(description="Positive and negative control entities for the experiment")
    statistical_approach: List[str] = Field(description="Sample size, replication, precision, and criteria entities")
    potential_pitfalls: List[str] = Field(description="Potential challenge entities in experiment design")
```


```447:468:ragnosis/grounding.py
    # Generate output
    out_string = textwrap.dedent(f"""\
    # Input Hypothesis
    
    {input}\n
    
    # Generated Experiment Plan\n""")
    
    for field_name, entities in experiment_plan.dict().items():
        out_string += f"## {field_name}\n"
        if not entities:
            out_string += "No entities extracted\n\n"
            continue
            
        for entity in entities:
            out_string += f"### {entity}\n"
            if entity in grounded_plan.get(field_name, {}):
                grounded_entity = grounded_plan[field_name][entity]
                for k, v in grounded_entity.__dict__.items():
                    out_string += f"- {k}: {v}\n"
            out_string += "\n"
    
```


---



---

