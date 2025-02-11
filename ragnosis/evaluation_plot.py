import json
import plotly.graph_objects as go
from pathlib import Path
import webbrowser
from urllib.parse import urljoin
from urllib.request import pathname2url

def create_file_url(filepath):
    """Convert a file path to a file:// URL"""
    return urljoin('file:', pathname2url(str(Path(filepath).absolute())))

def plot_protocol_evaluations(eval_dir: str | Path, output_html: str | Path = "protocol_evaluations.html", open_browser: bool = True):
    """
    Create an interactive plot of protocol evaluation scores.
    
    Args:
        eval_dir: Directory containing the evaluation JSON files and protocol markdown files
        output_html: Path to save the interactive HTML plot
        open_browser: Whether to automatically open the plot in a browser
    """
    eval_dir = Path(eval_dir)
    output_html = Path(output_html)
    scores = []
    protocols = []
    eval_files = []
    
    # Collect all evaluation files
    for eval_file in sorted(eval_dir.glob("*_evaluation.json")):
        protocol_file = eval_dir / f"{eval_file.stem.split('_')[0]}_protocol.md"
        
        if not protocol_file.exists():
            print(f"Warning: Protocol file not found for {eval_file}")
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

    if not scores:
        print("No evaluation files found to plot")
        return None

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
    output_html.parent.mkdir(parents=True, exist_ok=True)
    with open(output_html, 'w') as f:
        f.write(html_content)
    
    print(f"Plot saved to {output_html}")
    if open_browser:
        webbrowser.open(str(output_html))
    
    return output_html

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create an interactive plot of protocol evaluation scores")
    parser.add_argument("eval_dir", help="Directory containing evaluation JSONs and protocol markdown files")
    parser.add_argument("--output", default="protocol_evaluations.html", help="Output HTML file path")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    
    args = parser.parse_args()
    plot_protocol_evaluations(args.eval_dir, args.output, not args.no_browser)