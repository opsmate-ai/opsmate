from fasthtml.common import *
from opsmate.gui.models import Cell
import json

editor_script = Script(
    """

function initEditor(id, default_value) {
    let editor;
    let completionTippy;
    let currentCompletion = '';

    editor = ace.edit(id);
    editor.setTheme("ace/theme/monokai");
    editor.session.setMode("ace/mode/markdown");
    editor.setOptions({
        fontSize: "14px",
        showPrintMargin: false,
        showGutter: true,
        highlightActiveLine: true,
        // maxLines: Infinity,
        wrap: true
    });

    editor.setValue(default_value);

    window.addEventListener('resize', function() {
        editor.resize();
    });
    completionTippy = tippy(document.getElementById('editor'), {
        content: 'Loading...',
        trigger: 'manual',
        placement: 'top-start',
        arrow: true,
        interactive: true
    });

    // Override the default tab behavior
    editor.commands.addCommand({
        name: 'insertCompletion',
        bindKey: {win: 'Tab', mac: 'Tab'},
        exec: function(editor) {
            if (currentCompletion) {
                editor.insert(currentCompletion);
                currentCompletion = '';
                completionTippy.hide();
            } else {
                editor.indent();
            }
        }
    });
}

"""
)


def CodeEditor(cell: Cell):
    return (
        editor_script,
        Div(
            # Toolbar(),
            Div(
                Div(
                    id=f"cell-input-{cell.id}",
                    cls="w-full h-64",
                    name="input",
                    value=cell.input,
                ),
                Script(
                    f"""
                    // Initialize immediately instead of waiting for DOMContentLoaded
                    initEditor('cell-input-{cell.id}', {json.dumps(cell.input)});

                    // Also listen for htmx:afterSwap event to reinitialize after HTMX updates
                    document.body.addEventListener('htmx:afterSwap', function(evt) {{
                        if (document.getElementById('cell-input-{cell.id}')) {{
                            initEditor('cell-input-{cell.id}', {json.dumps(cell.input)});
                        }}
                    }});
                """
                ),
                cls="flex-grow w-full",
            ),
            cls="flex flex-col h-auto w-full",
            hidden=cell.hidden,
        ),
    )
