## SpecStory

## Markdown Syntax for Quoting Input Text (2/28/2025, 3:05:18 PM)

_**User**_

Do you see the section in the context? Is there some markdown syntax I can use to make sure input_text is quoted in the output markdown? Like the content of the string input_text might itself be markdown but I want this to show as a quoted block or a code block in the final output markdown

---

_**Assistant**_

Yes, I see the section. You can wrap the `input_text` in triple backticks or use markdown blockquote syntax (lines starting with >) to ensure it's displayed as a distinct block in the final markdown. Here's how you could modify that section:

````python:ragnosis/grounding.py
// ... existing code ...
output_parts = [
    "# Input",
    "",
    "```",
    input_text,
    "```",
    "",
    "# Generated Experiment Plan",
    ""
]
// ... existing code ...
````

Or alternatively, using blockquote syntax:

````python:ragnosis/grounding.py
// ... existing code ...
output_parts = [
    "# Input",
    "",
    "> " + input_text.replace("\n", "\n> "),  # Prefix each line with "> "
    "",
    "# Generated Experiment Plan",
    ""
]
// ... existing code ...
````

The first approach using triple backticks will display the content in a code block, while the second approach using blockquotes will show it as an indented quote block. The triple backticks approach might be preferable since it will preserve any markdown formatting in the input text without interpreting it.

---



---

