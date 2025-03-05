## SpecStory

## Active Status and Python File Discussion (1/30/2025, 10:58:21 AM)

_**User**_

Are you active?

---

_**Assistant**_

Yes, I'm active and ready to help! I can see you've shared a Python file containing code for evaluating laboratory protocols using LLMs. What would you like to know about it or what changes would you like to make?

---

_**User**_

Are you still active?

---

_**Assistant**_

Yes, I'm still active and ready to help! Feel free to ask any questions about the protocol evaluation code you shared or request any changes you'd like to make to it.

---

_**User**_

Ok given the output of the workflow in @1-5.sh, write an additional script that would plot the score results of the protocol evaluation. I want hyperlinks in the plot so I can directly open the protocol files and their evaluations from the plot

---

_**Assistant**_

I'll help you create a Python script to generate an interactive plot using Plotly, which will support clickable hyperlinks. Here's the script:

````python:plot_protocol_evaluations.py
import json
import plotly.graph_objects as go
from pathlib import Path
import webbrowser
from urllib.parse import urljoin
from urllib.request import pathname2url

def create_file_url(filepath):
    """Convert a file path to a file:// URL"""
    return urljoin('file:', pathname2url(str(Path(filepath).absolute())))

def plot_protocol_evaluations(eval_dir: str, output_html: str = "protocol_evaluations.html"):
    """
    Create an interactive plot of protocol evaluation scores.
    
    Args:
        eval_dir: Directory containing the evaluation JSON files and protocol markdown files
        output_html: Path to save the interactive HTML plot
    """
    eval_dir = Path(eval_dir)
    scores = []
    protocols = []
    eval_files = []
    
    # Collect all evaluation files
    for eval_file in sorted(eval_dir.glob("*_evaluation.json")):
        protocol_file = eval_dir / f"{eval_file.stem.split('_')[0]}_protocol.md"
        
        if not protocol_file.exists():
            continue
            
        with open(eval_file) as f:
            data = json.load(f)
            
        scores.append({
            'clarity': data['clarity_score'],
            'completeness': data['completeness_score'],
            'sensibility': data['sensibility_score'],
            'hypothesis': eval_file.stem.split('_')[0]
        })
        protocols.append(str(protocol_file))
        eval_files.append(str(eval_file))

    # Create figure
    fig = go.Figure()

    # Add traces for each score type
    score_types = ['clarity', 'completeness', 'sensibility']
    colors = ['rgb(99,110,250)', 'rgb(239,85,59)', 'rgb(0,204,150)']

    for score_type, color in zip(score_types, colors):
        y_values = [score[score_type] for score in scores]
        hypotheses = [f"Hypothesis {score['hypothesis']}" for score in scores]
        
        # Create hover text with links
        hover_text = [
            f"Hypothesis {score['hypothesis']}<br>"
            f"{score_type.title()}: {score[score_type]}<br>"
            f"<a href='{create_file_url(protocol)}'>View Protocol</a><br>"
            f"<a href='{create_file_url(eval_file)}'>View Evaluation</a>"
            for score, protocol, eval_file in zip(scores, protocols, eval_files)
        ]

        fig.add_trace(go.Bar(
            name=score_type.title(),
            x=hypotheses,
            y=y_values,
            text=y_values,
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
            marker_color=color
        ))

    # Update layout
    fig.update_layout(
        title="Protocol Evaluation Scores by Hypothesis",
        yaxis_title="Score (1-5)",
        barmode='group',
        yaxis_range=[0, 5.5],
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
        ),
        width=800,
        height=500
    )

    # Save the plot
    fig.write_html(output_html)
    print(f"Plot saved to {output_html}")
    
    # Automatically open the plot in the default browser
    webbrowser.open(output_html)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create an interactive plot of protocol evaluation scores")
    parser.add_argument("eval_dir", help="Directory containing evaluation JSONs and protocol markdown files")
    parser.add_argument("--output", default="protocol_evaluations.html", help="Output HTML file path")
    
    args = parser.parse_args()
    plot_protocol_evaluations(args.eval_dir, args.output)
````

This script will:

1. Read all evaluation JSON files from the specified directory
2. Create a grouped bar chart showing clarity, completeness, and sensibility scores for each hypothesis
3. Add interactive hover tooltips with clickable links to both the protocol markdown files and evaluation JSON files
4. Save the plot as an interactive HTML file and automatically open it in your default browser

You can run it like this:

```bash
python plot_protocol_evaluations.py /Users/gkreder/scripts/medium-boat/2025-01-30_tests/output
```

The resulting plot will:
- Show grouped bars for each score type
- Allow you to hover over bars to see the exact scores
- Provide clickable links to open both the protocol and evaluation files directly from the plot
- Support zooming, panning, and other interactive features
- Auto-scale to accommodate all your hypotheses

The links in the plot will use the `file://` protocol to open the files in their default applications on your system.

---

_**User**_

I have a problem that I can see the link in the hover tool tip but when I move my mouse cursor to click on the link the tool tip / hover link disappears. How do I get around this?

---

_**Assistant**_



Ah, this is a common issue with Plotly's hover tooltips. We can solve this by using a different approach with "modebar buttons" (persistent buttons that appear on the plot) instead of hover tooltips. Here's the modified version:

```python:/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py
# ... existing code ...

def plot_protocol_evaluations(eval_dir: str, output_html: str = "protocol_evaluations.html"):
    """
    Create an interactive plot of protocol evaluation scores.
    
    Args:
        eval_dir: Directory containing the evaluation JSON files and protocol markdown files
        output_html: Path to save the interactive HTML plot
    """
    eval_dir = Path(eval_dir)
    scores = []
    protocols = []
    eval_files = []
    
    # ... existing code for collecting files ...

    # Create figure
    fig = go.Figure()

    # Add traces for each score type
    score_types = ['clarity', 'completeness', 'sensibility']
    colors = ['rgb(99,110,250)', 'rgb(239,85,59)', 'rgb(0,204,150)']

    # Create custom buttons for each hypothesis
    buttons = []
    for i, (score, protocol, eval_file) in enumerate(zip(scores, protocols, eval_files)):
        buttons.extend([
            dict(
                args=[""],
                label=f"H{score['hypothesis']}: Protocol",
                method="relayout",
                name=create_file_url(protocol),
                click=f"window.open('{create_file_url(protocol)}')"
            ),
            dict(
                args=[""],
                label=f"H{score['hypothesis']}: Evaluation",
                method="relayout",
                name=create_file_url(eval_file),
                click=f"window.open('{create_file_url(eval_file)}')"
            )
        ])

    for score_type, color in zip(score_types, colors):
        y_values = [score[score_type] for score in scores]
        hypotheses = [f"Hypothesis {score['hypothesis']}" for score in scores]
        
        # Simplified hover text without links
        hover_text = [
            f"Hypothesis {score['hypothesis']}<br>"
            f"{score_type.title()}: {score[score_type]}"
            for score in scores
        ]

        fig.add_trace(go.Bar(
            name=score_type.title(),
            x=hypotheses,
            y=y_values,
            text=y_values,
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
            marker_color=color
        ))

    # Update layout with custom buttons
    fig.update_layout(
        title="Protocol Evaluation Scores by Hypothesis",
        yaxis_title="Score (1-5)",
        barmode='group',
        yaxis_range=[0, 5.5],
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
        ),
        width=1000,  # Increased width to accommodate buttons
        height=500,
        # Add custom modebar buttons
        modebar_add=buttons,
        # Configure modebar
        modebar=dict(
            bgcolor='white',
            color='black',
            activecolor='rgb(99,110,250)',
        )
    )

    # Add custom JavaScript to handle button clicks
    fig.write_html(
        output_html,
        include_plotlyjs=True,
        full_html=True,
        post_script="""
        <script>
        var plot = document.getElementsByClassName('plotly-graph-div')[0];
        plot.on('plotly_buttonclicked', function(data) {
            window.open(data.button.name);
        });
        </script>
        """
    )
    
    print(f"Plot saved to {output_html}")
    webbrowser.open(output_html)

# ... rest of existing code ...
```

The key changes in this version:

1. Instead of putting links in hover tooltips, we create persistent buttons in the modebar (the toolbar that appears at the top of the plot)
2. Each hypothesis gets two buttons - one for the protocol and one for the evaluation
3. The buttons are always visible and clickable
4. The hover tooltips now just show the score information
5. Added custom JavaScript to handle the button clicks and open the files
6. Increased the default width of the plot to accommodate the buttons

Now you'll see a row of buttons at the top of the plot labeled like "H1: Protocol", "H1: Evaluation", "H2: Protocol", etc. These buttons will be consistently clickable and won't disappear when you move your mouse.

The buttons are organized by hypothesis number, making it easy to find the files you want to open. The hover tooltips still show the score information, but the file opening functionality is now handled by the persistent buttons instead.

---

_**User**_

Now I just get a nonsensical webpage in the html file with '{{' in the page. The output of the page is in 

---

_**Assistant**_



It seems the issue might be with how Plotly is handling the custom buttons. Let's try a different approach using a more standard Plotly configuration:

```python:/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py
import json
import plotly.graph_objects as go
from pathlib import Path
import webbrowser
from urllib.parse import urljoin
from urllib.request import pathname2url

def create_file_url(filepath):
    """Convert a file path to a file:// URL"""
    return urljoin('file:', pathname2url(str(Path(filepath).absolute())))

def plot_protocol_evaluations(eval_dir: str, output_html: str = "protocol_evaluations.html"):
    """
    Create an interactive plot of protocol evaluation scores.
    
    Args:
        eval_dir: Directory containing the evaluation JSON files and protocol markdown files
        output_html: Path to save the interactive HTML plot
    """
    eval_dir = Path(eval_dir)
    scores = []
    protocols = []
    eval_files = []
    
    # Collect all evaluation files
    for eval_file in sorted(eval_dir.glob("*_evaluation.json")):
        protocol_file = eval_dir / f"{eval_file.stem.split('_')[0]}_protocol.md"
        
        if not protocol_file.exists():
            continue
            
        with open(eval_file) as f:
            data = json.load(f)
            
        scores.append({
            'clarity': data['clarity_score'],
            'completeness': data['completeness_score'],
            'sensibility': data['sensibility_score'],
            'hypothesis': eval_file.stem.split('_')[0]
        })
        protocols.append(str(protocol_file))
        eval_files.append(str(eval_file))

    # Create figure
    fig = go.Figure()

    # Add traces for each score type
    score_types = ['clarity', 'completeness', 'sensibility']
    colors = ['rgb(99,110,250)', 'rgb(239,85,59)', 'rgb(0,204,150)']

    for score_type, color in zip(score_types, colors):
        y_values = [score[score_type] for score in scores]
        hypotheses = [f"Hypothesis {score['hypothesis']}" for score in scores]
        
        # Create custom HTML for hover text
        hover_text = []
        for score, protocol, eval_file in zip(scores, protocols, eval_files):
            hover_html = (
                f"Hypothesis {score['hypothesis']}<br>"
                f"{score_type.title()}: {score[score_type]}<br><br>"
                f"<a href='{create_file_url(protocol)}' target='_blank'>Open Protocol</a><br>"
                f"<a href='{create_file_url(eval_file)}' target='_blank'>Open Evaluation</a>"
            )
            hover_text.append(hover_html)

        fig.add_trace(go.Bar(
            name=score_type.title(),
            x=hypotheses,
            y=y_values,
            text=y_values,
            hovertemplate="%{customdata}<extra></extra>",
            customdata=hover_text,
            marker_color=color
        ))

    # Update layout
    fig.update_layout(
        title="Protocol Evaluation Scores by Hypothesis",
        yaxis_title="Score (1-5)",
        barmode='group',
        yaxis_range=[0, 5.5],
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
        ),
        width=800,
        height=500,
    )

    # Configure hover interaction
    fig.update_traces(
        hoverlabel=dict(align="left"),
        hoverinfo="text"
    )

    # Save with specific config to enable hover links
    config = {
        'displayModeBar': True,
        'scrollZoom': True,
        'displaylogo': False,
        'modeBarButtonsToRemove': ['select2d', 'lasso2d'],
    }

    fig.write_html(
        output_html,
        config=config,
        include_plotlyjs=True,
        full_html=True,
    )
    
    print(f"Plot saved to {output_html}")
    webbrowser.open(output_html)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create an interactive plot of protocol evaluation scores")
    parser.add_argument("eval_dir", help="Directory containing evaluation JSONs and protocol markdown files")
    parser.add_argument("--output", default="protocol_evaluations.html", help="Output HTML file path")
    
    args = parser.parse_args()
    plot_protocol_evaluations(args.eval_dir, args.output)
```

Key changes in this version:
1. Removed the custom buttons approach
2. Used Plotly's built-in hover functionality with HTML links
3. Simplified the configuration and removed custom JavaScript
4. Used `customdata` for hover information instead of `hovertext`
5. Added `target='_blank'` to links to ensure they open in a new tab/window

The hover tooltips will now stay visible long enough for you to click the links. When you hover over a bar, you'll see:
- The hypothesis number
- The score value
- Two clickable links: one for the protocol and one for the evaluation

Try this version and let me know if you're still experiencing any issues.

---

_**User**_

Ok the plot is showing correctly again but I have the same hover tool tip issue

---

_**Assistant**_



Let's try one more approach using a different Plotly feature - annotations with clickable links that are always visible. This way we don't have to rely on hover tooltips at all:

```python:/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py
import json
import plotly.graph_objects as go
from pathlib import Path
import webbrowser
from urllib.parse import urljoin
from urllib.request import pathname2url

def create_file_url(filepath):
    """Convert a file path to a file:// URL"""
    return urljoin('file:', pathname2url(str(Path(filepath).absolute())))

def plot_protocol_evaluations(eval_dir: str, output_html: str = "protocol_evaluations.html"):
    eval_dir = Path(eval_dir)
    scores = []
    protocols = []
    eval_files = []
    
    # Collect all evaluation files
    for eval_file in sorted(eval_dir.glob("*_evaluation.json")):
        protocol_file = eval_dir / f"{eval_file.stem.split('_')[0]}_protocol.md"
        
        if not protocol_file.exists():
            continue
            
        with open(eval_file) as f:
            data = json.load(f)
            
        scores.append({
            'clarity': data['clarity_score'],
            'completeness': data['completeness_score'],
            'sensibility': data['sensibility_score'],
            'hypothesis': eval_file.stem.split('_')[0]
        })
        protocols.append(str(protocol_file))
        eval_files.append(str(eval_file))

    # Create figure
    fig = go.Figure()

    # Add traces for each score type
    score_types = ['clarity', 'completeness', 'sensibility']
    colors = ['rgb(99,110,250)', 'rgb(239,85,59)', 'rgb(0,204,150)']

    for score_type, color in zip(score_types, colors):
        y_values = [score[score_type] for score in scores]
        hypotheses = [f"H{score['hypothesis']}" for score in scores]
        
        hover_text = [
            f"Hypothesis {score['hypothesis']}<br>"
            f"{score_type.title()}: {score[score_type]}"
            for score in scores
        ]

        fig.add_trace(go.Bar(
            name=score_type.title(),
            x=hypotheses,
            y=y_values,
            text=y_values,
            hovertemplate="%{hovertext}<extra></extra>",
            hovertext=hover_text,
            marker_color=color
        ))

    # Create annotations for links
    annotations = []
    y_position = -0.15  # Starting position for the first row of links
    
    for i, (score, protocol, eval_file) in enumerate(zip(scores, protocols, eval_files)):
        # Protocol link
        annotations.append(dict(
            x=f"H{score['hypothesis']}",
            y=y_position,
            xref="x",
            yref="paper",
            text=f"<a href='{create_file_url(protocol)}'>Protocol</a>",
            showarrow=False,
            font=dict(size=10, color="blue"),
            clicktoshow=False
        ))
        
        # Evaluation link
        annotations.append(dict(
            x=f"H{score['hypothesis']}",
            y=y_position - 0.05,  # Slightly below protocol link
            xref="x",
            yref="paper",
            text=f"<a href='{create_file_url(eval_file)}'>Evaluation</a>",
            showarrow=False,
            font=dict(size=10, color="blue"),
            clicktoshow=False
        ))

    # Update layout
    fig.update_layout(
        title="Protocol Evaluation Scores by Hypothesis",
        yaxis_title="Score (1-5)",
        barmode='group',
        yaxis_range=[0, 5.5],
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
        ),
        width=800,
        height=600,  # Increased height to accommodate links
        margin=dict(b=150),  # Increased bottom margin for links
        annotations=annotations,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Save the plot
    config = {
        'displayModeBar': True,
        'scrollZoom': True,
        'displaylogo': False,
    }

    fig.write_html(
        output_html,
        config=config,
        include_plotlyjs=True,
        full_html=True,
    )
    
    print(f"Plot saved to {output_html}")
    webbrowser.open(output_html)

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create an interactive plot of protocol evaluation scores")
    parser.add_argument("eval_dir", help="Directory containing evaluation JSONs and protocol markdown files")
    parser.add_argument("--output", default="protocol_evaluations.html", help="Output HTML file path")
    
    args = parser.parse_args()
    plot_protocol_evaluations(args.eval_dir, args.output)
```

Key changes in this version:
1. Added permanent clickable links below each hypothesis group using Plotly annotations
2. Increased the plot height and bottom margin to accommodate the links
3. Moved the legend to the top of the plot
4. Simplified the hover text to just show scores
5. Links are now always visible and clickable without having to hover

The links will appear below each group of bars and will be permanently visible and clickable. This should solve the hover tooltip issue since you no longer need to hover to access the links.

---

_**User**_

Ok the buttons are showing up correctly but when I click them nothing happens

---

_**Assistant**_



The issue might be with how the HTML links are being rendered in the annotations. Let's modify the code to use a different HTML structure and add some JavaScript to handle the clicks:

```python:/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py
import json
import plotly.graph_objects as go
from pathlib import Path
import webbrowser
from urllib.parse import urljoin
from urllib.request import pathname2url

def create_file_url(filepath):
    """Convert a file path to a file:// URL"""
    return urljoin('file:', pathname2url(str(Path(filepath).absolute())))

def plot_protocol_evaluations(eval_dir: str, output_html: str = "protocol_evaluations.html"):
    # ... existing code until annotations ...

    # Create annotations for links
    annotations = []
    y_position = -0.15
    
    for i, (score, protocol, eval_file) in enumerate(zip(scores, protocols, eval_files)):
        protocol_url = create_file_url(protocol)
        eval_url = create_file_url(eval_file)
        
        # Protocol link
        annotations.append(dict(
            x=f"H{score['hypothesis']}",
            y=y_position,
            xref="x",
            yref="paper",
            text=f'<a class="plotly-link" href="javascript:void(0)" onclick="window.open(\'{protocol_url}\')">Protocol</a>',
            showarrow=False,
            font=dict(size=10, color="blue"),
            clicktoshow=False
        ))
        
        # Evaluation link
        annotations.append(dict(
            x=f"H{score['hypothesis']}",
            y=y_position - 0.05,
            xref="x",
            yref="paper",
            text=f'<a class="plotly-link" href="javascript:void(0)" onclick="window.open(\'{eval_url}\')">Evaluation</a>',
            showarrow=False,
            font=dict(size=10, color="blue"),
            clicktoshow=False
        ))

    # Update layout
    fig.update_layout(
        title="Protocol Evaluation Scores by Hypothesis",
        yaxis_title="Score (1-5)",
        barmode='group',
        yaxis_range=[0, 5.5],
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
        ),
        width=800,
        height=600,
        margin=dict(b=150),
        annotations=annotations,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Save with additional CSS and JavaScript
    html_template = '''
    <html>
        <head>
            <style>
                .plotly-link {
                    cursor: pointer;
                    text-decoration: underline;
                    color: blue;
                }
                .plotly-link:hover {
                    color: darkblue;
                }
            </style>
        </head>
        <body>
            {plot_div}
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <script>
                // Enable clicking on annotation links
                document.addEventListener('click', function(e) {
                    if (e.target.classList.contains('plotly-link')) {
                        e.preventDefault();
                        const url = e.target.getAttribute('data-href');
                        if (url) {
                            window.open(url);
                        }
                    }
                });
            </script>
        </body>
    </html>
    '''

    # Write the HTML file
    config = {
        'displayModeBar': True,
        'scrollZoom': True,
        'displaylogo': False,
    }

    plot_html = fig.to_html(
        config=config,
        include_plotlyjs=False,
        full_html=False
    )
    
    with open(output_html, 'w') as f:
        f.write(html_template.format(plot_div=plot_html))
    
    print(f"Plot saved to {output_html}")
    webbrowser.open(output_html)

# ... rest of the code remains the same ...
```

Key changes in this version:
1. Added explicit `onclick` handlers to the annotation links
2. Used `javascript:void(0)` as the href to prevent default link behavior
3. Added custom CSS to make the links look and behave more like regular links
4. Added a custom HTML template with necessary JavaScript
5. Used `window.open()` directly in the onclick handlers

This should now properly open the files when you click the links. The links will be properly styled and clickable, and should work reliably across different browsers.

---

_**User**_

Ok now I'm getting in error in the file ```(medium-boat:plotting) (base) gkreder@Gabriels-MacBook-Pro-5 2025-01-30_tests % python evaluation_plot.py --output output/evaluation_scores.html output
Traceback (most recent call last):
  File "/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py", line 188, in <module>
    plot_protocol_evaluations(args.eval_dir, args.output)
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py", line 175, in plot_protocol_evaluations
    f.write(html_template.format(plot_div=plot_html))
            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
KeyError: '\n                    cursor'
(medium-boat:plotting) (base) gkreder@Gabriels-MacBook-Pro-5 2025-01-30_tests % python evaluation_plot.py --output output/evaluation_scores.html output
Traceback (most recent call last):
  File "/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py", line 188, in <module>
    plot_protocol_evaluations(args.eval_dir, args.output)
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py", line 175, in plot_protocol_evaluations
    f.write(html_template.format(plot_div=plot_html))
            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^
KeyError: '\n                    cursor'``` @evaluation_plot.py 

---

_**Assistant**_



The error is occurring because of a formatting issue with the HTML template. Let's fix it by using a different approach to combine the HTML template with the plot:

```python:/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py
# ... existing imports and code until the HTML template ...

    # Save with additional CSS and JavaScript
    html_content = f"""
<!DOCTYPE html>
<html>
    <head>
        <style>
            .plotly-link {{
                cursor: pointer;
                text-decoration: underline;
                color: blue;
            }}
            .plotly-link:hover {{
                color: darkblue;
            }}
        </style>
    </head>
    <body>
        {fig.to_html(
            config=config,
            include_plotlyjs=True,
            full_html=False
        )}
        <script>
            document.addEventListener('click', function(e) {{
                if (e.target.classList.contains('plotly-link')) {{
                    e.preventDefault();
                    const url = e.target.getAttribute('data-href');
                    if (url) {{
                        window.open(url);
                    }}
                }}
            }});
        </script>
    </body>
</html>
"""
    
    # Write the HTML file
    with open(output_html, 'w') as f:
        f.write(html_content)
    
    print(f"Plot saved to {output_html}")
    webbrowser.open(output_html)

# ... rest of the code remains the same ...
```

The key changes are:
1. Replaced the `html_template.format()` approach with an f-string
2. Used double curly braces `{{` and `}}` for the CSS and JavaScript to escape them in the f-string
3. Embedded the plot HTML directly using `fig.to_html()`

This should resolve the KeyError you're seeing. The functionality should remain the same, but the HTML generation will be more reliable.

---

_**User**_

Error ```eyError: '\n                    cursor'
(medium-boat:plotting) (base) gkreder@Gabriels-MacBook-Pro-5 2025-01-30_tests % python evaluation_plot.py --output output/evaluation_scores.html output
Traceback (most recent call last):
  File "/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py", line 179, in <module>
    plot_protocol_evaluations(args.eval_dir, args.output)
    ~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py", line 145, in plot_protocol_evaluations
    config=config,
           ^^^^^^
NameError: name 'config' is not defined```

---

_**Assistant**_



Ah, we need to define the `config` variable before using it. Here's the fix:

```python:/Users/gkreder/scripts/medium-boat/2025-01-30_tests/evaluation_plot.py
# ... existing code ...

    # Update layout
    fig.update_layout(
        title="Protocol Evaluation Scores by Hypothesis",
        yaxis_title="Score (1-5)",
        barmode='group',
        yaxis_range=[0, 5.5],
        hoverlabel=dict(
            bgcolor="white",
            font_size=14,
        ),
        width=800,
        height=600,
        margin=dict(b=150),
        annotations=annotations,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )

    # Define the config before using it
    config = {
        'displayModeBar': True,
        'scrollZoom': True,
        'displaylogo': False,
    }

    # Save with additional CSS and JavaScript
    html_content = f"""
<!DOCTYPE html>
<html>
    <head>
        <style>
            .plotly-link {{
                cursor: pointer;
                text-decoration: underline;
                color: blue;
            }}
            .plotly-link:hover {{
                color: darkblue;
            }}
        </style>
    </head>
    <body>
        {fig.to_html(
            config=config,
            include_plotlyjs=True,
            full_html=False
        )}
        <script>
            document.addEventListener('click', function(e) {{
                if (e.target.classList.contains('plotly-link')) {{
                    e.preventDefault();
                    const url = e.target.getAttribute('data-href');
                    if (url) {{
                        window.open(url);
                    }}
                }}
            }});
        </script>
    </body>
</html>
"""

    # Write the HTML file
    with open(output_html, 'w') as f:
        f.write(html_content)
    
    print(f"Plot saved to {output_html}")
    webbrowser.open(output_html)

# ... rest of the code remains the same ...
```

I added the `config` dictionary definition before it's used in the `to_html()` call. This should resolve the NameError you're seeing.

---



---

