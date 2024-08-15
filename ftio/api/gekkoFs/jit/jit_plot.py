import plotly.graph_objects as go
from ftio.plot.helper import format_plot



def main():
    # Sample data for the stacked plot
    categories = ['JIT', 'JIT no FTIO', 'Pure']
    # add nodes if need 
    nodes=[]
    fig = go.Figure()
    title = "Nek5000 with 100 steps and checkpointing every 10 steps"


    # run with 2 nodes [jit|jit_no_ftio|pure]
    ################ Edit area ############################
    app = [207.3, 181.44, 181.56]
    stage_out = [3.95,  17.68, 0]
    stage_in =  [0.72,  0.75, 0]
    nodes.append('node 2')

    # run with 3 nodes
    tmp_app = [90.11, 84.81, 103]
    tmp_stage_out = [2.26, 61.0, 0]
    tmp_stage_in = [1.11, 1.11, 0]
    nodes.append('node 3')
    app,stage_out,stage_in = add_experiment(app,stage_out,stage_in,tmp_app,tmp_stage_out,tmp_stage_in)


    tmp_app = [70.53, 72.71, 80.21]
    tmp_stage_out = [1.891,9.430, 0]
    tmp_stage_in = [1.149, 1.145, 0]
    nodes.append('node 4')
    app,stage_out,stage_in = add_experiment(app,stage_out,stage_in,tmp_app,tmp_stage_out,tmp_stage_in)


    ##################################
    repeated_strings = [s for s in categories for _ in nodes]
    repeated_numbers = nodes * len(categories)
    categories = [repeated_strings, repeated_numbers]

    fig.add_bar(x=categories, y=app, name="App")
    fig.add_bar(x=categories, y=stage_out, name="Stage out")
    fig.add_bar(x=categories, y=stage_out, name="Stage out")

    # Update the layout to stack the bars
    fig.update_layout(
        yaxis_title="Time (s)",
        xaxis_title=f"Runs",
        showlegend=True,
        title=title,
        barmode="relative"
        )

    format_plot(fig)
    
    # Display the plot
    fig.show()

def add_experiment(app,stage_out,stage_in,tmp_app,tmp_stage_out,tmp_stage_in):
    app = add_mode(app,tmp_app)
    stage_out = add_mode(stage_out,tmp_stage_out)
    stage_in = add_mode(stage_in,tmp_stage_in)
    return app,stage_out,stage_in


def add_mode(list1, list2):
    # Create a new list to store the result
    result = []
    

    
    # Iterate over the range of the lists' lengths
    for i in range(len(list2)):
        # Add the current element from each list    
        for j in range(int(len(list1)/3)):
            result.append(list1[i+j])
        result.append(list2[i])
    
    return result

if __name__ == "__main__":
    main()