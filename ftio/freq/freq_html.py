import os
from sys import platform
from threading import Thread
import plotly.offline
from rich.console import Console

def create_html(figs:list,render :str,configuration:dict,name:str="freq") -> None:
    if platform == "linux" or platform == "linux2":
        os.system(f"rm -f ./{name}.html || true")
        os.system("rm -rf io_anomality_freq_images || true ")

    if render == "dynamic":
        template = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
        <meta charset="utf-8"/>
        <script>{plotly}</script>
        </head>
        <body>
        {plots}
        </body>
        </html>
        """
        s = ""
        for fig in figs:
            # s = s + fig.to_html(include_plotlyjs=False) + "\n"
            s= s + fig.to_html(config=configuration,include_plotlyjs=False) + "\n"
        template = template.format(
            plotly=plotly.offline.get_plotlyjs(), plots=s
        )
        with open(f"{name}.html", "a") as file:
            file.write(template)
        os.system(f"open ./{name}.html &\n")
    else:
        os.mkdir("io_predicition_anomality_images")
        # extension='jpg'
        extension='svg'
        # extension = "png"
        print("-> Generating %s figures" % extension.upper())
        threads = []
        length = len(figs)
        plotly.io.json.config.default_engine = "orjson"
        for fig in figs:
            index = figs.index(fig)
            threads.append(
                Thread(
                    target=create_static_figure,
                    args=(fig, index, length, extension),
                )
            )

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        os.system("open . &")


def create_static_figure(fig, index:int, length:int, extension:str)-> None:
    """Creates static HTML figures

    Args:
        fig (plotly figure): _description_
        index (int): index of the figure
        length (int): total figures
        extension (str): desired extension
    """
    console = Console()
    scale = 1
    console.print("working on [cyan]figure (%i/%i) [/]" % (index + 1, length))
    if fig.layout.title.text:
        file_name = f"io_predicition_freq_images/{fig.layout.title.text.replace(' ', '_').replace('(', '_').replace(')', '_')}.{extension}"
    else:
        file_name = f"io_predicition_freq_images/{index}.{extension}"

    if "svg" not in extension and "pdf" not in extension:
        scale = 5

    fig.write_image(file_name, scale=scale)
    if index == 0:
            os.system(f"open {file_name} || true ")

    console.print(f"[cyan]figure ({index + 1}/{length}) [/]created")

