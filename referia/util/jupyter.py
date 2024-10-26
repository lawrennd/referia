from IPython import display
def expand_cell():

    display.display(display.HTML(data="""
<style>
.container {
    width: 100% !important;
}

div.notebook-container {
    width: 100% !important;
    height: fit-content;
}

div.menubar-container {
    width: 100% !important;
    height: fit-content;
}

div.maintoolbar-container {
    width: 100% !important;
    height: fit-content;
}

div.cell.selected {
    border-left-width: 1px !important;
}

div.output_scroll {
    resize: vertical !important;
}

.output_wrapper .output {
    height:auto !important;
}


.output_scroll {
    box-shadow:none !important;
    webkit-box-shadow:none !important;
}
</style>
"""))
