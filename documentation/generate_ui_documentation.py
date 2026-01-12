# -*- coding: utf-8 -*-
"""
This script is a first attempt to automate documentation of the Rattlesnake user interface,
pulling the layout of the widgets and their tooltips and creating a markdown file that can
be included in the main Rattlesnake documentation.

Rattlesnake Vibration Control Software
Copyright (C) 2021  National Technology & Engineering Solutions of Sandia, LLC
(NTESS). Under the terms of Contract DE-NA0003525 with NTESS, the U.S.
Government retains certain rights in this software.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import re

# from glob import glob

from qtpy import QtWidgets, uic

# files = glob('../src/rattlesnake/components/*.ui')
files = [
    "../src/rattlesnake/components/random_vibration_definition.ui",
]


class UIAnalyzer(QtWidgets.QMainWindow):
    """A Class to analyze the contents of a .ui file and create a markdown file documenting it
    """

    def __init__(self, ui_file):
        """Initializes the UI Analyzer object

        Parameters
        ----------
        file : str
            Path to a .ui file to analyze and document
        """
        super().__init__()
        self.load_ui(ui_file)
        self.print_depth = 0
        self.all_widgets = None
        self.all_layouts = None
        self.currently_in_groupboxes = []

    def load_ui(self, ui_file):
        """Loads in a ui file and shows it in a main window

        Parameters
        ----------
        ui_file : str
            The path to the ui file to load
        """
        # Load the UI file
        self.form_class, self.base_class = uic.loadUiType(ui_file)

        # Check if the loaded UI is a QMainWindow
        if issubclass(self.base_class, QtWidgets.QMainWindow):
            # If it's a QMainWindow, load it directly into self
            self.ui = self.form_class()
            self.ui.setupUi(self)
        else:
            # If it's a QWidget, create a central widget and load the UI into it
            self.central_widget = QtWidgets.QWidget(self)
            self.setCentralWidget(self.central_widget)
            self.ui = self.form_class()
            self.ui.setupUi(self.central_widget)

        self.show()

    def export_structure(self):
        """Creates a nested dictionary structure of the widgets and layouts in the user interface"""
        # Start the recursive structure export from the central widget or self
        if self.base_class == QtWidgets.QMainWindow:
            self.all_widgets = self.findChildren(QtWidgets.QWidget)
            self.all_layouts = self.findChildren(QtWidgets.QLayout)
            self.all_widgets.append(self)
            return self._get_widget_structure(self)
        else:
            self.all_widgets = self.central_widget.findChildren(QtWidgets.QWidget)
            self.all_layouts = self.central_widget.findChildren(QtWidgets.QLayout)
            self.all_widgets.append(self.central_widget)
            return self._get_widget_structure(self.central_widget)

    def _get_widget_structure(self, item):
        try:
            name = item.objectName()
        except AttributeError:
            name = type(item).__name__
        print(f"Analyzing {name}")
        try:
            position = item.mapToGlobal(item.rect().topLeft())
            position = [position.x(), position.y()]
        except AttributeError:
            position = None
        try:
            tool_tip = item.toolTip()
        except AttributeError:
            tool_tip = None
        structure = {
            "name": name,
            "type": type(item),
            "tooltip": tool_tip,
            "pos": position,
            "children": [],
            "widget": item,
        }
        # Remove ourselves from the list since we've been accounted for
        if isinstance(item, QtWidgets.QWidget):
            self.all_widgets.remove(item)
        if isinstance(item, QtWidgets.QLayout):
            self.all_layouts.remove(item)
        print(f"Removed {name} from global lists")

        # If we are a layout, go through all of the items in the layout
        if isinstance(item, QtWidgets.QLayout):
            print("Stepping through Layout")
            for index in range(item.count()):
                print(f"Item {index}")
                # Get the item
                childitem = item.itemAt(index)
                widget = childitem.widget()
                if widget is None:
                    # If the item is not a widget, it will be a layout
                    child = childitem
                else:
                    # Otherwise, it will be an item that we need to get the
                    # widget from
                    child = widget
                structure["children"].append(self._get_widget_structure(child))

        try:
            # Get the remaining children layouts and widgets
            child_layouts = [
                it
                for it in item.children()
                if isinstance(it, QtWidgets.QLayout)
                if it in self.all_layouts
            ]
            print(f"Remaining Child Layouts {child_layouts}")
            for child in child_layouts:
                structure["children"].append(self._get_widget_structure(child))
            child_widgets = [
                it
                for it in item.children()
                if not isinstance(it, QtWidgets.QLayout)
                if it in self.all_widgets
            ]
            print(f"Remaining Child Widgets {child_widgets}")
            for child in child_widgets:
                structure["children"].append(self._get_widget_structure(child))
        except AttributeError:
            child_layouts = []
            child_widgets = []

        # Sort the children based on left-to-right, top-to-bottom
        structure["children"].sort(key=lambda child: (child["pos"][1], child["pos"][0]))

        # Go through the children and set the position of this widget based on
        # the values of the children
        if position is None and len(structure["children"]) > 0:
            xs = []
            ys = []
            for child in structure["children"]:
                pos = child["pos"]
                if pos is not None:
                    x, y = child["pos"]
                    xs.append(x)
                    ys.append(y)
            structure["pos"] = [min(xs), min(ys)]
        elif position is None and len(structure["children"]) == 0:
            structure["pos"] = [100000000, 1000000000]

        return structure

    def print_structure(self):
        """Prints a representation of the ui hierarchy"""
        struct = self.export_structure()
        self._print_struct_item(struct)

    def _print_struct_item(self, struct):
        name = struct["name"]
        position = struct["pos"]
        # tooltip = struct['tooltip']
        typ = struct["type"]
        children = struct["children"]
        print(" " * self.print_depth * 4 + f" {name} ({typ}) at {position}")
        self.print_depth += 1
        for child in children:
            self._print_struct_item(child)
        self.print_depth -= 1

    def parse_tooltip(self, tooltip):
        """Parses a tooltip to extract the widget's label and documentation

        Parameters
        ----------
        tooltip : str
            HTML-based tooltip from the UI.  It will be separated by paragraph tags (</p>).  The
            first line is used as the label.  The remaining lines are used as documentation.  All
            other HTML tags are discarded.

        Returns
        -------
        label : str
            The name of the widget in the documentation
        documentation : str
            The documentation to go along with the widget
        """
        # Use regex to remove HTML tags
        tooltip_data = []
        lines = tooltip.split("</p>")
        for line in lines:
            text = re.sub(r"<[^>]+>", "", line)  # Remove all HTML tags
            text = text.strip()  # Remove leading and trailing whitespace
            if len(text) > 0:
                tooltip_data.append(text)
        tooltip_data = [tooltip_data[0], "\n\n".join(tooltip_data[1:])]
        return tooltip_data

    def generate_markdown(self):
        """Generates a string of markdown text describing the user interface

        Returns
        -------
        str
            A string containing markdown text that can be included into the main documentation.
        """
        self.currently_in_groupboxes = []
        struct = self.export_structure()
        markdown = self._generate_item_markdown(struct)
        return markdown

    def _generate_item_markdown(self, struct):
        this_markdown = ""

        if isinstance(struct["widget"], QtWidgets.QGroupBox):
            this_markdown = (
                this_markdown + f'\nIn the {struct["widget"].title()} section of the window:\n'
            )

        if struct["tooltip"] is not None and struct["tooltip"].strip() != "":
            label, message = self.parse_tooltip(struct["tooltip"])
            this_markdown = this_markdown + f"\n* **{label}** {message}"

        # Go through its children
        for child in struct["children"]:
            this_markdown = this_markdown + self._generate_item_markdown(child)

        if isinstance(struct["widget"], QtWidgets.QGroupBox):
            this_markdown = this_markdown + "\n"

        return this_markdown


for file in files:
    print(f"Analyzing {file}")
    ui = UIAnalyzer(file)
    markdown_text = ui.generate_markdown()
    filename = os.path.splitext(os.path.split(file)[1])[0]
    with open(f"mdbook/src/{filename}_doc.md", "w", encoding='utf-8') as f:
        f.write(markdown_text)
