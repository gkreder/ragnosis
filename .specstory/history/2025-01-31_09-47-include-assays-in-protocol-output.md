## SpecStory

## Include Assays in Protocol Output (1/31/2025, 9:47:58 AM)

_**User**_

Right now, the workflow that generates a protocol takes an input md of a experimental plan and generates a protocol. One thing that's missing is the grounded assays from the experimental plan in the output protocol. I think this is because of the actual model (there's not a `assays` section in the output model of this flow right? I'd like to be sure to include the assays in the protocol output. This shouldn't involve any extra generation, it's more copying over that information into the output protocol and making sure its rendered (with its grounding terms and scores etc) in the output. Can we modify the protocol flow accordingly?

---

_**Assistant**_

I'll help modify the protocol flow to include the assays information from the input experiment plan. We'll need to make two main changes:

1. Add an `assays` field to the `Protocol` model (which isn't shown in the current file)
2. Parse the assays section from the input markdown and include it in the output

Here's how we can modify the code:

````python:ragnosis/grounding.py
// ... existing code ...

def generate_protocol_flow(
    input_md: Path,
    model: str,
    temperature: float = 0.0,
    out_md: Path = None,
) -> str:
    """Generate a detailed experimental protocol from an experiment plan markdown file"""
    
    // ... existing logging setup ...

    try:
        # Read and parse the experiment plan markdown
        with open(input_md, "r") as f:
            experiment_plan_text = f.read()
        
        # Extract assays section from input markdown
        assays_section = ""
        in_assays_section = False
        for line in experiment_plan_text.split('\n'):
            if line.startswith('## Assays'):
                in_assays_section = True
                continue
            elif line.startswith('## ') and in_assays_section:
                break
            elif in_assays_section:
                assays_section += line + '\n'
        
        logging.debug(f"Extracted assays section: {len(assays_section)} characters")

        // ... existing LLM setup and protocol generation ...

        # Generate markdown output
        logging.info("Formatting protocol output")
        try:
            sections = []
            
            # Add protocol sections
            for field_name, field_value in protocol.dict().items():
                if field_name == 'assays':  # Skip assays as we'll add it separately
                    continue
                    
                section_title = field_name.replace('_', ' ').title()
                logging.debug(f"Processing section: {section_title}")
                
                if isinstance(field_value, str):
                    sections.append(f"## {section_title}\n{field_value}\n")
                elif isinstance(field_value, list):
                    items = '\n'.join([f"- {item}" for item in field_value])
                    sections.append(f"## {section_title}\n{items}\n")
            
            # Add assays section from input if it exists
            if assays_section.strip():
                sections.append(f"## Assays\n{assays_section}\n")
            
            out_string = '\n'.join(sections)
            logging.debug(f"Generated markdown output with {len(sections)} sections")
        except Exception as e:
            logging.error(f"Failed to format protocol output: {e}")
            raise

        // ... existing file saving code ...

    finally:
        // ... existing cleanup code ...
````

You'll also need to make sure the `Protocol` model includes an `assays` field. This should be in your models.py file, but since it wasn't shown, here's what that change would look like:

````python:ragnosis/models.py
class Protocol(BaseModel):
    materials: List[str]
    equipment: List[str]
    safety_precautions: str
    steps: List[str]
    assays: Optional[str]  # Added field for assays
    notes: Optional[str]
````

This modification will:
1. Extract the assays section from the input markdown
2. Include it in the output protocol under an "Assays" section
3. Preserve all the grounding information since we're copying the section verbatim

The assays section will appear in the output after all the protocol-generated sections, maintaining all its original formatting including any grounding terms and scores.

---

_**User**_

Ok I don't think this worked. The final output experimental protocol file from a full run does not include assays. So let's modify this again. For now, I simply want the `Assay Types` and `Organisms` sections from the input experimental plan file copied over to the output of the experimental protocol as sections. Forget about modifying the `Protocol` model for now @grounding.py @models.py 

---

_**Assistant**_

I'll help modify the `generate_protocol_flow` function to copy over these sections directly. Here's the updated code:

````python:ragnosis/grounding.py
def generate_protocol_flow(
    input_md: Path,
    model: str,
    temperature: float = 0.0,
    out_md: Path = None,
) -> str:
    """Generate a detailed experimental protocol from an experiment plan markdown file"""
    
    // ... existing logging setup ...

    try:
        # Read and parse the experiment plan markdown
        with open(input_md, "r") as f:
            experiment_plan_text = f.read()
        
        # Extract Assay Types and Organisms sections from input markdown
        assay_types_section = ""
        organisms_section = ""
        current_section = None
        
        for line in experiment_plan_text.split('\n'):
            if line.startswith('## Assay Types'):
                current_section = 'assay_types'
                continue
            elif line.startswith('## Organisms'):
                current_section = 'organisms'
                continue
            elif line.startswith('## '):
                current_section = None
                continue
            elif current_section == 'assay_types':
                assay_types_section += line + '\n'
            elif current_section == 'organisms':
                organisms_section += line + '\n'
        
        logging.debug(f"Extracted assay types section: {len(assay_types_section)} characters")
        logging.debug(f"Extracted organisms section: {len(organisms_section)} characters")

        // ... existing LLM setup and protocol generation ...

        # Generate markdown output
        logging.info("Formatting protocol output")
        try:
            sections = []
            
            # Add protocol sections
            for field_name, field_value in protocol.dict().items():
                section_title = field_name.replace('_', ' ').title()
                logging.debug(f"Processing section: {section_title}")
                
                if isinstance(field_value, str):
                    sections.append(f"## {section_title}\n{field_value}\n")
                elif isinstance(field_value, list):
                    items = '\n'.join([f"- {item}" for item in field_value])
                    sections.append(f"## {section_title}\n{items}\n")
            
            # Add Assay Types and Organisms sections from input if they exist
            if assay_types_section.strip():
                sections.append(f"## Assay Types\n{assay_types_section}\n")
            if organisms_section.strip():
                sections.append(f"## Organisms\n{organisms_section}\n")
            
            out_string = '\n'.join(sections)
            logging.debug(f"Generated markdown output with {len(sections)} sections")
        except Exception as e:
            logging.error(f"Failed to format protocol output: {e}")
            raise

        // ... existing file saving code ...

    finally:
        // ... existing cleanup code ...
````

This modification will:
1. Extract both the "Assay Types" and "Organisms" sections from the input markdown
2. Copy these sections verbatim into the output protocol markdown
3. Preserve all the grounding information since we're copying the sections directly
4. Keep the sections in their original format

The sections will appear in the output after all the protocol-generated sections. No changes to the models are needed for this approach.

---



---

