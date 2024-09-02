import argparse
import json
import os
import plotly.graph_objects as go
import numpy as np
from ftio.plot.helper import format_plot




def main(filenames):
    if not filenames:
        results = JitResult()
        # # run with x nodes  128 procs [jit | jit_no_ftio | pure] (now in old folder)
        # ################ Edit area ############################
        # title = "Nek5000 with 128 procs checkpointing every 10 steps with a total of 100 steps"
        # tmp_app = [207.3, 181.44, 181.56]
        # tmp_stage_out = [3.95,  17.68, 0]
        # tmp_stage_in =  [0.72,  0.75, 0]
        # results.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,"# 2")

        # # run with 3 nodes
        # tmp_app = [90.11, 84.81, 103]
        # tmp_stage_out = [2.26, 61.0, 0]
        # tmp_stage_in = [1.11, 1.11, 0]
        # results.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,"# 3")

        # tmp_app = [70.53, 72.71, 80.21]
        # tmp_stage_out = [1.891,9.430, 0]
        # tmp_stage_in = [1.149, 1.145, 0]
        # results.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,"# 4")

        # run with x nodes 32 procs [jit | jit_no_ftio | pure] (now in old folder)
        ################ Edit area ############################
        # # run with 3 nodes
        # tmp_app       = [ 157.8 , 156.51 , 160 ]
        # tmp_stage_out = [ 1.041 , 1.04 ,  0]
        # tmp_stage_in  = [ 1.099 ,  1.09,  0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 3")
        

        # tmp_app       = [ 114.72,122.07  ,  130.95]
        # tmp_stage_out = [ 1.04, 1.03 ,  0]
        # tmp_stage_in  = [ 1.11, 1.83  ,  0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 4")

        # tmp_app       = [ 97.11,106.31, 98.11]
        # tmp_stage_out = [ 1.05,1.12,0]
        # tmp_stage_in  = [ 1.13,1.12,0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 5")


        # tmp_app       = [ 126.93,119.06, 93.27]
        # tmp_stage_out = [ 1.12,1.159,0]
        # tmp_stage_in  = [ 1.59,1.96,0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 10")

        # tmp_app       = [ 182.58,174.67,90.64 ]
        # tmp_stage_out = [ 1.08,1.08,0]
        # tmp_stage_in  = [ 3.57,2.84,0]
        # add_experiment(data,tmp_app,tmp_stage_out,tmp_stage_in,"# 20")
        
        # title = "Nek5000 with 16 procs checkpointing every 10 steps with a total of 50 steps"
        # filename = "results_mogon/procs16_steps50_writeinterval10.json "
        
        title = "Nek5000 with 16 procs checkpointing every 5 steps with a total of 50 steps"
        filename = "results_mogon/wacom++_app_proc_1_OMPthreads_64_12500000.json"
        current_directory =  os.path.dirname(os.path.abspath(__file__))
        json_file_path = os.path.join(current_directory, filename)
        
        extract_and_plot(results,json_file_path,title)
    else:
        for filename in filenames:
            print(f"Processing file: {filename}")
            results = JitResult()
            title = filename
            current_directory = os.getcwd()
            json_file_path = os.path.join(current_directory, filename)
            extract_and_plot(results,json_file_path,title)
        

def extract_and_plot(results,json_file_path:str, title:str):
    with open(json_file_path, "r") as json_file:
        data = json.load(json_file)
        data = sorted(data, key=lambda x: x['nodes'])
        for d in data:
            results.add_dict(d)
    
    results.plot(title)


def add_mode(list1, list2):
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



class JitResult:
    def __init__(self) -> None:
        self.app       = []
        self.stage_out = []
        self.stage_in  = []
        self.node = []

    def add_experiment(self,tmp_app:list[float],tmp_stage_out:list[float],tmp_stage_in:list[float],run:str):
        self.app = add_mode(self.app,tmp_app)
        self.stage_out = add_mode(self.stage_out,tmp_stage_out)
        self.stage_in = add_mode(self.stage_in,tmp_stage_in)
        self.node.append(run)


    def add_dict(self, data_list:list[dict]):
        tmp_app       = [0.0,0.0,0.0]
        tmp_stage_out = [0.0,0.0,0.0]
        tmp_stage_in  = [0.0,0.0,0.0]

        for i in data_list["data"]:
            if i["mode"] in {"DPCF","DCF"}:
                index = 0
            elif i["mode"] in {"DC","DPC"}:
                index = 1
            else:
                index = 2
            tmp_app[index] = i["app"]
            tmp_stage_out[index] = i["stage_out"]
            tmp_stage_in[index] = i["stage_in"]
                
        self.add_experiment(tmp_app,tmp_stage_out,tmp_stage_in,f"# {data_list["nodes"]}")
        

    def plot(self,title=""):
        # Sample data for the stacked plot
        categories = ['JIT', 'JIT no FTIO', 'Pure']
        repeated_strings = [s for s in categories for _ in self.node]
        repeated_numbers = self.node * len(categories)
        categories = [repeated_strings, repeated_numbers]

        fig = go.Figure()
        

        fig.add_bar(x=categories, y=self.app, text=self.app,  name="App")
        fig.add_bar(x=categories, y=self.stage_out, text=self.stage_out,  name="Stage out")
        fig.add_bar(x=categories, y=self.stage_in, text=self.stage_in,  name="Stage in")

        # text 
        # Update the layout to stack the bars
        fig.update_traces(textposition='inside', texttemplate = "%{text:.2f}", textfont_size=14, textangle=0, textfont=dict(
            # family="sans serif",
            color="white"
        ))
        # comment out to see all text
        fig.update_layout(uniformtext_minsize=8, uniformtext_mode='hide')
        # sum total
        total = list(np.round(np.array(self.app) + np.array(self.stage_out) + np.array(self.stage_in),2))
        # plot total
        fig.add_trace(go.Scatter(
            x=categories, 
            y=total,
            text=total,
            mode='text',
            textposition='top center',
            textfont=dict(
                size=14,
            ),
            showlegend=False
        ))

        
        fig.update_layout(
            yaxis_title="Time (s)",
            xaxis_title=f"Experimental Runs with # Nodes",
            showlegend=True,
            title=title,
            barmode="relative",
            width=1500,
            height=600,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=0.9,
                xanchor="right",
                x=0.995
                )
            )

        fig.show()
        format_plot(fig, x_minor=False)
        
        # Display the plot
        fig.show()




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load JSON data from files and plot.")
    parser.add_argument(
        'filenames',
        type=str,
        nargs="*",  # '*' allows zero or more filenames
        default=[],
        help="The paths to the JSON file(s) to plot."
    )
    args = parser.parse_args()
    
    main(args.filenames)
    