import numpy as np
from sklearn.cluster import OPTICS, DBSCAN
import plotly.express as px
import pandas as pd


def optics(df:pd.DataFrame, s1:str, s2:str)-> pd.DataFrame:
    # Combine x and y into a 2D array
    data = np.column_stack((df[s1],df[s2]))

    # Apply OPTICS clustering
    optics = OPTICS(min_samples=5, xi=0.05, min_cluster_size=0.05)
    optics.fit(data)

    # Extract cluster labels
    labels = optics.labels_

    plot_cluster(df,s1,s2,labels)
    # plot_cluster_simple(df,s1,s2,labels)

    return  pd.concat([df, pd.DataFrame({'label':labels})], axis=1)


def dbscan(df: pd.DataFrame, s1: str, s2: str) -> pd.DataFrame:
    # Combine s1 and s2 columns into a 2D array for clustering
    data = np.column_stack((df[s1], df[s2]))

    # Apply DBSCAN clustering
    dbscan = DBSCAN(eps=0.5, min_samples=5)
    dbscan.fit(data)

    # Extract cluster labels
    labels = dbscan.labels_

    plot_cluster(df, s1, s2, labels, "DBscan")

    return pd.concat([df, pd.DataFrame({'label': labels})], axis=1)


def plot_cluster_simple(df:pd.DataFrame, s1:str, s2:str, labels:np.ndarray, method="Optics") -> None:    
    # Plot the clusters
    fig = px.scatter(x=df[s1], y=df[s2], color=labels.astype(str), 
                    title=f'{method} Clustering',
                    labels={'color': 'Cluster'},
                    color_discrete_sequence=px.colors.qualitative.Dark24)
    fig.show()


def plot_cluster(df:pd.DataFrame, s1:str, s2:str, labels:np.ndarray, method="Optics")  -> None:    
    x = df[s1]
    y = df[s2]
    # Define unique labels and their corresponding colors and symbols
    unique_labels = set(labels)
    colors = px.colors.qualitative.Dark24[:len(unique_labels)]
    symbols = ['circle', 'square', 'diamond', 'cross', 'x', 'triangle-up', 'triangle-down'] * (len(unique_labels) // 7 + 1)
    color_map = {label: colors[i % len(colors)] for i, label in enumerate(unique_labels)}
    symbol_map = {label: symbols[i % len(symbols)] for i, label in enumerate(unique_labels)}

    # Map each point to its corresponding color and symbol
    point_colors = [color_map[label] for label in labels]
    point_symbols = [symbol_map[label] for label in labels]

    # Create a DataFrame for plotting with Plotly (optional)
    df = pd.DataFrame({'x': x, 'y': y, 'label': labels.astype(str), 'color': point_colors, 'symbol': point_symbols, 'metric':df['Metric']})

    # Plot the clusters using Plotly with increased marker size and different symbols
    fig = px.scatter(df, x='x', y='y', color='label',
                    title=f'{method} Clustering',
                    labels={'color': 'Cluster'},
                    symbol='symbol',
                    size_max=15,  # Set maximum size for markers
                    color_discrete_sequence=colors,
                    )

    # Customize the marker size and add cluster annotations
    fig.update_traces(marker=dict(size=10),
                  hovertemplate=(
                      'x: %{x}<br>'
                      'y: %{y}<br>'
                      'Metric: %{customdata}<br>'
                      'Cluster: %{marker.color}<br>'
                  ))
    fig.update_layout(uniformtext_mode='hide')
    fig.update_traces(customdata=df['metric'])
    fig.show()