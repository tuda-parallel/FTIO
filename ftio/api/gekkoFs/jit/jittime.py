import json
import os
from rich.console import Console
from rich.table import Table
from ftio.api.gekkoFs.jit.jitsettings import JitSettings


class JitTime:
    def __init__(self) -> None:
        self._app = 0
        self._stage_in = 0
        self._stage_out = 0

    @property
    def app(self):
        return self._app

    # setting the apps
    @app.setter
    def app(self, app):
        self._app = app

    # deleting the values
    @app.deleter
    def app(self):
        del self._app

    @property
    def stage_out(self):
        return self._stage_out

    # setting the stage_outs
    @stage_out.setter
    def stage_out(self, stage_out):
        self._stage_out = stage_out

    # deleting the stage_outs
    @stage_out.deleter
    def stage_out(self):
        del self._stage_out

    @property
    def stage_in(self):
        return self._stage_in

    # setting the stage_ins
    @stage_in.setter
    def stage_in(self, stage_in):
        self._stage_in = stage_in

    # deleting the stage_ins
    @stage_in.deleter
    def stage_in(self):
        del self._stage_in

    def print_time(self):
        console = Console()
        text = (
            f"App time      : {self._app:.6f}s\n"
            f"Stage out time: {self._stage_out:.6f}s\n"
            f"Stage in time : {self._stage_in:.6f}s\n"
            "--------------------------------\n"
            f"Total time : {self._app + self._stage_out + self._stage_in:.6f}s\n"
        )
        
# This block of code is creating a table using the `rich` library in Python to display the time data
# in a structured format. Here's a breakdown of what each part does:
# This block of code is creating a table using the `rich` library in Python to display the time data
# related to different stages. Here's a breakdown of what each part does:
        # Create a Table object
        table = Table(show_header=True, header_style="bold magenta")

        # Add columns to the table
        table.add_column("Task", justify="left")
        table.add_column("Time (s)", justify="left")

        # Add rows with the time data
        table.add_row("App", f"{self._app:.8f}")
        table.add_row("Stage out", f"{self.stage_out:.8f}")
        table.add_row("Stage in",f"{self.stage_in:.8f}")
        table.add_row("-" * 10, "")
        table.add_row("Total", f"{self._app + self._stage_out + self._stage_in:.8f}",style="bold green")

        # Print the table to the console
        console.print(table)
        
        return text

    def to_dict(self):
        return {
            "app": self._app,
            "stage_in": self._stage_in,
            "stage_out": self._stage_out,
        }

    def dump_json(self, settings: JitSettings):
        data = {**self.to_dict(), **settings.to_dict()}
        parent = os.path.dirname(settings.log_dir)
        json_path = os.path.join(parent, "result.json")
        try:
            with open(json_path, "r+") as file:
                try:
                    existing_data = json.load(file)
                except json.JSONDecodeError:
                    existing_data = []

                # Check if there is an existing entry with the same number of nodes and mode
                for entry in existing_data:
                    if entry.get("nodes") == data["nodes"]:
                        for i, data_entry in enumerate(entry["data"]):
                            if data_entry["mode"] == data["mode"]:
                                entry["data"][i] = data  # Overwrite the existing data
                                break
                        else:
                            entry["data"].append(data)  # Add new entry if no mode match
                        break
                else:
                    # If no entry with the same nodes exists, add a new one
                    existing_data.append({"nodes": data["nodes"], "data": [data]})

                # Write the updated data back to the file
                file.seek(0)
                json.dump(existing_data, file, indent=4)
                file.truncate()

        except FileNotFoundError:
            # If the file does not exist, create it with the new data
            with open(json_path, "w") as file:
                json.dump([{"nodes": data["nodes"], "data": [data]}], file, indent=4)


    def print_and_save_time(self, settings: JitSettings):
        # get the time
        text = self.print_time()
        # write it out to the file
        time_log_file = os.path.join(settings.log_dir, "time.log")
        with open(time_log_file, "a") as file:
            file.write(text)

        self.dump_json(settings)
