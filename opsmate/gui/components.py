from fasthtml.components import *
from opsmate.gui.models import Cell, CellLangEnum, CreatedByType, ThinkingSystemEnum
from opsmate.gui.assets import *
import pickle


class CellComponent:
    def __init__(self, cell: Cell, cell_render_funcs: dict):
        self.cell = cell
        self.cell_size = len(self.cell.workflow.cells)
        self.cell_render_funcs = cell_render_funcs
        self.blueprint = self.cell.workflow.blueprint

    def __ft__(self):
        """Renders a single cell component"""
        # Determine if the cell is active
        active_class = "border-green-500" if self.cell.active else "border-gray-300"

        return Div(
            # Add Cell Button Menu
            self.cell_insert_dropdown(),
            # Main Cell Content
            Div(
                # Cell Header
                self.cell_header(),
                # Cell Input - Updated with conditional styling
                self.cell_input_form(),
                # Cell Output (if any)
                self.cell_output(),
                cls=f"rounded-lg shadow-sm border {active_class}",  # Apply the active class here
            ),
            cls="group relative",
            key=self.cell.id,
            id=f"cell-component-{self.cell.id}",
        )

    def cell_insert_dropdown(self):
        return (
            Div(
                Div(
                    Button(
                        plus_icon_svg,
                        tabindex="0",
                        cls="btn btn-ghost btn-xs",
                    ),
                    Ul(
                        Li(
                            Button(
                                "Insert Above",
                                hx_post=f"/blueprint/{self.blueprint.id}/cell/{self.cell.id}?above=true",
                            )
                        ),
                        Li(
                            Button(
                                "Insert Below",
                                hx_post=f"/blueprint/{self.blueprint.id}/cell/{self.cell.id}?above=false",
                            )
                        ),
                        tabindex="0",
                        cls="dropdown-content z-10 menu p-2 shadow bg-base-100 rounded-box",
                    ),
                    cls="dropdown dropdown-right",
                ),
                cls="absolute -left-8 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity",
            ),
        )

    def cell_header(self):
        return (
            Div(
                Div(
                    Span(
                        f"In [{self.cell.execution_sequence}]:",
                        cls="text-gray-500 text-sm",
                    ),
                    # Add cell type selector
                    cls="flex items-center gap-2",
                ),
                Div(
                    Select(
                        Option(
                            "Text Instruction",
                            value=CellLangEnum.TEXT_INSTRUCTION.value,
                            selected=self.cell.lang == CellLangEnum.TEXT_INSTRUCTION,
                        ),
                        Option(
                            "Bash",
                            value=CellLangEnum.BASH.value,
                            selected=self.cell.lang == CellLangEnum.BASH,
                        ),
                        Option(
                            "Notes",
                            value=CellLangEnum.NOTES.value,
                            selected=self.cell.lang == CellLangEnum.NOTES,
                        ),
                        name="lang",
                        hx_put=f"/blueprint/{self.blueprint.id}/cell/{self.cell.id}",
                        hx_trigger="change",
                        disabled=self.cell.created_by == CreatedByType.ASSISTANT,
                        cls="select select-sm ml-2",
                    ),
                    Select(
                        Option(
                            "Type 1 - Fast",
                            value=ThinkingSystemEnum.TYPE1.value,
                            selected=self.cell.thinking_system
                            == ThinkingSystemEnum.TYPE1
                            or self.cell.lang == CellLangEnum.BASH,
                        ),
                        Option(
                            "Type 2 - Slow but thorough",
                            value=ThinkingSystemEnum.TYPE2.value,
                            selected=self.cell.thinking_system
                            == ThinkingSystemEnum.TYPE2,
                        ),
                        name="thinking_system",
                        hx_put=f"/blueprint/{self.blueprint.id}/cell/{self.cell.id}",
                        hx_trigger="change",
                        cls="select select-sm ml-2 min-w-[240px]",
                        hidden=self.cell.lang != CellLangEnum.TEXT_INSTRUCTION,
                        disabled=self.cell.created_by == CreatedByType.ASSISTANT,
                    ),
                    Button(
                        trash_icon_svg,
                        hx_delete=f"/blueprint/{self.blueprint.id}/cell/{self.cell.id}",
                        cls="btn btn-ghost btn-sm opacity-0 group-hover:opacity-100 hover:text-red-500",
                        disabled=self.cell_size == 1,
                    ),
                    Button(
                        edit_icon_svg,
                        Input(type="hidden", value="false", name="hidden"),
                        hx_put=f"/blueprint/{self.blueprint.id}/cell/{self.cell.id}",
                        cls="btn btn-ghost btn-sm",
                        disabled=self.cell.created_by == CreatedByType.ASSISTANT,
                    ),
                    Form(
                        Input(type="hidden", value=self.cell.id, name="cell_id"),
                        Button(
                            run_icon_svg,
                            cls="btn btn-ghost btn-sm",
                            disabled=self.cell.created_by == CreatedByType.ASSISTANT,
                        ),
                        ws_connect=f"/cell/run/ws/",
                        ws_send=True,
                        hx_ext="ws",
                    ),
                    cls="ml-auto flex items-center gap-2",
                ),
                id=f"cell-header-{self.cell.id}",
                cls="flex items-center px-4 py-2 bg-gray-100 border-b justify-between rounded-t-lg overflow-hidden",
            ),
        )

    def cell_input_form(self):
        return (
            Div(
                Form(
                    self.cell_text_area(),
                    Div(
                        hx_put=f"/blueprint/{self.blueprint.id}/cell/input/{self.cell.id}",
                        hx_trigger=f"keyup[!(shiftKey&&keyCode===13)] changed delay:500ms from:#cell-input-{self.cell.id}",
                        hx_swap=f"#cell-input-form-{self.cell.id}",
                    ),
                    # xxx: shift+enter is being registered as a newline
                    Div(
                        Input(type="hidden", value=self.cell.id, name="cell_id"),
                        ws_connect=f"/cell/run/ws/",
                        ws_send=True,
                        hx_ext="ws",
                        hx_trigger=f"keydown[shiftKey&&keyCode===13] from:#cell-input-{self.cell.id}",
                        hx_swap=f"#cell-input-form-{self.cell.id}",
                    ),
                    id=f"cell-input-form-{self.cell.id}",
                ),
                hx_include="input",
                cls="p-4",
            ),
        )

    def cell_text_area(self):
        return Textarea(
            self.cell.input,
            name="input",
            cls=f"w-full h-24 p-2 font-mono text-sm border rounded focus:outline-none focus:border-blue-500",
            placeholder="Enter your instruction here...",
            id=f"cell-input-{self.cell.id}",
            hidden=self.cell.hidden,
        )

    def cell_output(self):
        if self.cell.output:
            outputs = pickle.loads(self.cell.output)
            outputs = [
                # xxx: import the render funcs
                self.cell_render_funcs[output["type"]](output["output"])
                for output in outputs
            ]
        else:
            outputs = []
        return Div(
            Span(f"Out [{self.cell.execution_sequence}]:", cls="text-gray-500 text-sm"),
            Div(
                *outputs,
                id=f"cell-output-{self.cell.id}",
            ),
            cls="px-4 py-2 bg-gray-50 border-t rounded-b-lg overflow-hidden",
        )
