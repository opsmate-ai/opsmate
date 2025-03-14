from fasthtml.common import *
from opsmate.gui.models import Cell
import json

editor_script = Script(
    """
// Global map to keep track of editor instances
window.editorInstances = window.editorInstances || {};
window.currentCompletion = window.currentCompletion || {};
function initEditor(editor_id, default_value, cellId) {
    // Clean up any existing editor instance for this element
    if (window.editorInstances[cellId]) {
        // window.editorInstances[editor_id].destroy();
        // window.editorInstances[editor_id].container.remove();
        window.editorInstances[cellId] = null;
        window.currentCompletion[cellId] = null;
    }

    let editor;
    let completionTippy;

    editor = ace.edit(editor_id);
    editor.setTheme("ace/theme/monokai-light");
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

    // Store the editor instance for later cleanup
    window.editorInstances[cellId] = editor;
    window.currentCompletion[cellId] = '';
    window.addEventListener('resize', function() {
        editor.resize();
    });
    completionTippy = tippy(document.getElementById(editor_id), {
        content: 'Loading...',
        trigger: 'manual',
        placement: 'top-start',
        arrow: true,
        interactive: true
    });

    editor.session.on('change', function(delta) {
        if (delta.action === 'insert' && (delta.lines[0] === '.' || delta.lines[0] === ' ')) {
            showCompletionSuggestion(editor, completionTippy, cellId);
        }
    });

    // Override the default tab behavior
    editor.commands.addCommand({
        name: 'insertCompletion',
        bindKey: {win: 'Tab', mac: 'Tab'},
        exec: function(editor) {
            if (window.currentCompletion[cellId]) {
                editor.insert(window.currentCompletion[cellId]);
                window.currentCompletion[cellId] = '';
                completionTippy.hide();
            } else {
                editor.indent();
            }
        }
    });
}

async function showCompletionSuggestion(editor, completionTippy, cellId) {
    const cursorPosition = editor.getCursorPosition();
    const screenPosition = editor.renderer.textToScreenCoordinates(cursorPosition.row, cursorPosition.column);
    completionTippy.setContent('Loading...');
    completionTippy.setProps({
        getReferenceClientRect: () => ({
            width: 0,
            height: 0,
            top: screenPosition.pageY,
            bottom: screenPosition.pageY,
            left: screenPosition.pageX,
            right: screenPosition.pageX,
        })
    });
    completionTippy.show();

    try {
        const response = await fetch(`/cell/${cellId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                code: editor.getValue(),
                row: cursorPosition.row,
                column: cursorPosition.column
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        window.currentCompletion[cellId] = data.completion;
        editor.setGhostText(window.currentCompletion[cellId], cursorPosition);
        completionTippy.setContent(`${window.currentCompletion[cellId]} (Press Tab to insert)`);
    } catch (error) {
        console.error('Error:', error);
        completionTippy.setContent('Error fetching completion');
        window.currentCompletion[cellId] = '';
    }

    setTimeout(() => {
        if (window.currentCompletion[cellId]) {
            completionTippy.hide();
            window.currentCompletion[cellId] = '';
        }
    }, 5000);
}
"""
)


def CodeEditor(cell: Cell):
    return (
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
                    // Initial load
                    document.body.addEventListener('DOMContentLoaded', function(evt) {{
                        if (document.getElementById('cell-input-{cell.id}')) {{
                            initEditor('cell-input-{cell.id}', {json.dumps(cell.input)}, {cell.id});
                        }}
                    }});
                """
                ),
                cls="flex-grow w-full",
            ),
            cls="flex flex-col h-auto w-full",
            hidden=cell.hidden,
            id=f"cell-input-container-{cell.id}",
        ),
    )
