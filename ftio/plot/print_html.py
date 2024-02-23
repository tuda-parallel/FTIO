"""Generates HTML page out of plotly images
    Used by plot_core.py
"""
import os
import platform as plat
from sys import platform
import plotly.offline
from threading import Lock




class print_html:

    def __init__(self, args, path, names, filename = "main.html", outdir = "io_results") -> None:
        """generates HTML report
        Args:
            filename (str): main html file name
            args (list): contains render (static or dynamic) 
                        and show (True or False) flag
            path (str): output location
            outdir (str): output dir name
        """
        self.render = args.render
        self.path = path
        self.names = names
        self.filename = filename
        self.outdir = outdir
        self.show = not args.no_disp
        self.lock = Lock()

    #! ----------------------- Plot to HTML ------------------------------
    #**********************************************************************
    #*                       1. generate_html
    #**********************************************************************
    def generate_html_start(self) -> None:
        
        if not "stat" in self.render:  # only generate a single image
            pwd = os.getcwd()
            if len(self.path) <= 1 and not any(ext in self.path[0] for ext in ["json","darshan","msgpack", "txt"]):
                pwd = os.path.join(pwd,os.path.relpath(self.path[0],pwd))

            self.path = os.path.join(pwd,self.outdir)
            print(f"\n\033[1;34mGenerating HTML report \033[1;0m\n '->Directory is: {self.path}")
            if not os.path.exists(self.path):
                os.mkdir(self.path)
                print(f" '-> Directory {self.outdir} created in {pwd}")
            else:
                print(f" '-> Directory {self.outdir}  exists  in {pwd}")
        
            #?* create main HTML file
            #*-------------------------
            # html_files = ["async_write.html","async_read.html","sync_write.html","sync_read.html","time.html"] 
            print(f"\n '-> To see intermediate result call: \n     open {self.path}/main.html \n")
            self.filename = os.path.join(self.path,self.filename)
            print(" '-> Generated main.html ")
            with open(self.filename, "w") as file:
                file.write("<html><head></head><body>\n")
                file.write("<center><h1 style=\"color:black;\"> Results </h1> </center><hr style=\"height:2px;border-width:0;color:gray;background-color:gray\">\n")

            print("\033[1;32m '-> Creating plots I/O time\033[1;0m") 


    def generate_html_core(self,html_file, f) -> None:
        # create sub HTML files
        print(f"\033[1;34m  '-> Started generating {html_file}\033[1;0m")
        figures_to_html(f, os.path.join(self.path,html_file), self.names)    
        # Mark entry in main.html
        with open(self.filename, "a") as file:
            self.lock.acquire()
            tmp = html_file.replace("_"," ").replace("html"," ").capitalize()
            file.write(f"<h3 ><a href=\"file://{self.path}/{html_file}\" style=\"color:black;\">{tmp}: {len(f)} figures </a>\n")
            self.lock.release()

        print(f" '-> Finished generating {html_file}")


    def generate_html_end(self) -> None:
        # clsoe the file
        with open(self.filename, 'a') as file:
            file.write("<hr style=\"height:2px;border-width:0;color:gray;background-color:gray\">\n")
            if self.names:
                # self.names = list(set(self.names))
                file.write("<br><br> Folders map to:<ul>\n")    
                for i in self.names:
                    file.write(f"<li> Run {self.names.index(i)}: {i} </li>\n")    
                file.write("</ul> \n")
            file.write("</body></html> \n")

        print(f"\nTo see the result call \nopen {self.path}/main.html \n")
        if self.show:
            if platform == "linux" or platform == "linux2":
                if "WSL" in plat.uname().release:
                    os.system(f"powershell.exe start ./{self.outdir}/main.html ")
                else:
                    os.system(f"open {self.path}/main.html \n")

            if "windows" in platform:
                try:
                    os.system(f"powershell.exe start {self.path}/main.html &\n" )
                except:
                    os.system(f"powershell.exe start./{self.path}/main.html")


#**********************************************************************
#*                       1. figures_to_html
#**********************************************************************
def figures_to_html(figs, filename="async_write.html",names=[]) -> None:
    # conf = {  "toImageButtonOptions": {     "format": "svg", "scale":1  }}
    conf = {  "toImageButtonOptions": {     "format": "png", "scale":2 }}
    template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="utf-8"/>
    <script>{plotly}</script>
    </head>
    <body>
    {names}
    {plots}
    </body>
    </html>
    """
    html_parts = ""
    for fig in figs:
        if figs.index(fig)+1 == len(figs):
            print("    '-> figure (%i/%i) "%(figs.index(fig)+1,len(figs)), end="\n")
        else:
            print("    '-> \033[1;32mfigure (%i/%i) \033[1;0m"%(figs.index(fig)+1,len(figs)), end="\r")
        html_parts= html_parts + fig.to_html(config=conf,include_plotlyjs=False,include_mathjax = "cdn") + "\n"

    run_names = ""
    if names:                
        run_names ="<br><br> Folders map to:<ul>\n"
        for i in names:
            run_names = run_names + (f"<li> Run {names.index(i)}: {i} </li>\n")    
        run_names = run_names + "</ul> \n"

    template = template.format(plotly=plotly.offline.get_plotlyjs(), plots = html_parts, names = run_names)
    with open(filename, "w") as file:
        file.write(template)


