import plotly.graph_objects as go
from ftio.plot.helper import format_plot



def main():
    # Sample data for the stacked plot
    categories = ['JIT', 'JIT no FTIO', 'Pure']

    app_time = [207.3, 181.44, 181.56]
    stage_out_time = [3.95, 17.68, 0]
    stage_in_time = [0.72, 0.75, 0]
    title = "Nek5000 nodes 2 steps 100 write every 10 steps"
    plot_res(categories, app_time,stage_out_time, stage_in_time, title)

    app_time = [90.11, 84.81, 103]
    stage_out_time = [2.26, 61.0, 0]
    stage_in_time = [1.11, 1.11, 0]
    title = "Nek5000 nodes 3 steps 100 write every 10 steps"
    plot_res(categories, app_time,stage_out_time, stage_in_time, title)


def plot_res(categories, app_time,stage_out_time, stage_in_time, title):
    # Creating a stacked bar chart
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=categories,
        y=app_time,
        name='APP Time'
    ))

    fig.add_trace(go.Bar(
        x=categories,
        y=stage_out_time,
        name='Stage out'
    ))

    fig.add_trace(go.Bar(
        x=categories,
        y=stage_in_time,
        name='Stage in'
    ))

    # Update the layout to stack the bars
    fig.update_layout(
        barmode='stack',
        yaxis_title="Time (s)",
        xaxis_title=f"Runs",
        showlegend=True,
        title=title
        )

    format_plot(fig)
    
    # Display the plot
    fig.show()


if __name__ == "__main__":
    main()