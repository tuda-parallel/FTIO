import numpy as np
import plotly.graph_objects as go
from ftio.plot.helper import format_plot_and_ticks

class JitResult:
    def __init__(self) -> None:
        """
        Initialize a JitResult object to store experimental data.
        """
        self.app       = []
        self.stage_out = []
        self.stage_in  = []
        self.node = []

    def add_experiment(self,tmp_app:list[float],tmp_stage_out:list[float],tmp_stage_in:list[float],run:str):
        """
        Add an experiment's data to the JitResult object.

        Args:
            tmp_app (list[float]): Application times.
            tmp_stage_out (list[float]): Stage out times.
            tmp_stage_in (list[float]): Stage in times.
            run (str): Identifier for the experiment run.
        """
        self.app = add_mode(self.app,tmp_app)
        self.stage_out = add_mode(self.stage_out,tmp_stage_out)
        self.stage_in = add_mode(self.stage_in,tmp_stage_in)
        self.node.append(run)


    def add_dict(self, data_list:list[dict]):
        """
        Add data from a dictionary to the JitResult object.

        Args:
            data_list (list[dict]): List of dictionaries containing experimental data.
        """
        tmp_app       = [0.0,0.0,0.0]
        tmp_stage_out = [0.0,0.0,0.0]
        tmp_stage_in  = [0.0,0.0,0.0]

        for i in data_list["data"]: # jit
            if i["mode"] in {"DPCF","DCF"}:
                index = 0
            elif i["mode"] in {"DC","DPC"}: # lustre + Gekko
                index = 1
            else: # Lustre
                index = 2
            tmp_app[index] = i["app"]
            tmp_stage_out[index] = i["stage_out"]
            tmp_stage_in[index] = i["stage_in"]
                
        self.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,f"# {data_list["nodes"]}")
        
    def plot(self, title=""):
        """
        Plot the experimental data stored in the JitResult object.

        Args:
            title (str): Title for the plot.
        """
        # Sample data for the stacked plot
        categories = ['JIT', 'Lustre & Gekko', 'Lustre']
        repeated_strings = [s for s in categories for _ in self.node]
        repeated_numbers = self.node * len(categories)
        categories = [repeated_strings, repeated_numbers]

        fig = go.Figure()

        fig.add_bar(x=categories, y=self.app, text=self.app, name="App")
        fig.add_bar(x=categories, y=self.stage_out, text=self.stage_out, name="Stage out")
        fig.add_bar(x=categories, y=self.stage_in, text=self.stage_in, name="Stage in")

        # Update text formatting
        fig.update_traces(
            textposition='inside',
            texttemplate="%{text:.2f}",
            textfont_size=16,  # Increased font size
            textangle=0,
            textfont=dict(color="white")
        )

        # Comment out to see all text
        fig.update_layout(uniformtext_minsize=10, uniformtext_mode='hide')

        # Sum total
        total = list(np.round(np.array(self.app) + np.array(self.stage_out) + np.array(self.stage_in), 2))

        # Plot total
        fig.add_trace(go.Scatter(
            x=categories, 
            y=total,
            text=total,
            mode='text',
            textposition='top center',
            textfont=dict(size=18),  # Increased font size for total labels
            showlegend=False
        ))

        # Update layout with larger font sizes
        fig.update_layout(
            yaxis_title="Time (s)",
            xaxis_title=f"Experimental Runs with # Nodes",
            showlegend=True,
            title=title,
            title_font_size=24,  # Increased title font size
            barmode="relative",
            width=1000 + 100 * len(self.node),
            height=700,
            xaxis=dict(title_font=dict(size=24)),  # Increased x-axis title font size
            yaxis=dict(title_font=dict(size=24)),  # Increased y-axis title font size
            legend=dict(
                font=dict(size=20),  # Increased legend font size
                orientation="h",
                yanchor="bottom",
                y=0.9,
                xanchor="right",
                x=0.995
            )
        )

        
        format_plot_and_ticks(fig, x_minor=False)
        # Display the plot
        fig.show()


def add_mode(list1, list2):
    """
    Combine two lists by interleaving elements from the first list with
    elements from the second list.

    Args:
        list1 (list): The first list.
        list2 (list): The second list.

    Returns:
        list: The combined list.
    """
    # Create a new list to store the result
    result = []
    step = int(len(list1)/3)
    
    # Iterate over the range of the lists' lengths
    for i in range(len(list2)):
        # Add the current element from each list    
        for j in range(step):
            result.append(list1[i*step+j])
        result.append(list2[i])
    
    return result
