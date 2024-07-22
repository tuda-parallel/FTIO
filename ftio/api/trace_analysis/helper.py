import plotly.express as px

def quick_plot(x,y, x_label='time', y_label='Bandwidth'):
    fig = px.scatter(x=x, y=y, labels={'x':x_label, 'y':y_label}) 
    fig.show()