from IPython import display
def expand_cell():

    display.display(display.HTML(data="""
<style>
/* Classic Jupyter Notebook styles */
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

/* Aggressively prevent ALL scroll bars in output cells - Classic Jupyter */
div.output_scroll {
    resize: vertical !important;
    max-height: none !important;
    height: auto !important;
    overflow: visible !important;
    overflow-y: visible !important;
    overflow-x: visible !important;
}

.output_wrapper {
    max-height: none !important;
    height: auto !important;
    overflow: visible !important;
}

.output_wrapper .output {
    height: auto !important;
    max-height: none !important;
    overflow: visible !important;
}

.output_area {
    max-height: none !important;
    height: auto !important;
    overflow: visible !important;
}

.output_subarea {
    max-height: none !important;
    height: auto !important;
    overflow: visible !important;
}

.output_scroll {
    box-shadow: none !important;
    webkit-box-shadow: none !important;
}

/* Modern Jupyter Notebook 7+ and JupyterLab styles */
.jp-OutputArea {
    max-height: none !important;
    overflow: visible !important;
}

.jp-OutputArea-output {
    max-height: none !important;
    height: auto !important;
    overflow: visible !important;
    overflow-y: visible !important;
}

.jp-OutputArea-child {
    max-height: none !important;
    height: auto !important;
    overflow: visible !important;
}

.jp-OutputArea-output pre {
    max-height: none !important;
    overflow: visible !important;
}

.jp-RenderedText {
    max-height: none !important;
    overflow: visible !important;
}

.jp-RenderedText pre {
    max-height: none !important;
    overflow: visible !important;
}

/* Additional overrides for all possible scrollable containers */
pre.jp-RenderedText {
    max-height: none !important;
    overflow: visible !important;
}

div.jp-OutputArea-output.jp-OutputArea-executeResult {
    max-height: none !important;
    overflow: visible !important;
}

/* Widget-specific overrides */
.widget-area {
    max-height: none !important;
    overflow: visible !important;
}

.widget-subarea {
    max-height: none !important;
    overflow: visible !important;
}

.jp-OutputArea-output[data-mime-type*="widget"] {
    max-height: none !important;
    overflow: visible !important;
}

/* Catch-all for any remaining scrollable elements */
div.output,
div[class*="output"],
div[class*="Output"] {
    max-height: none !important;
    overflow: visible !important;
}
</style>
"""))
