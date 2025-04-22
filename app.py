import gradio as gr
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import csv
from fpdf import FPDF

# Initialize empty panel list
def initialize_panel_list():
    return pd.DataFrame(columns=["Panel Width (mm)", "Panel Height (mm)", "Panel Depth (mm)", "Quantity"])

# Function to add a new panel to the list
def add_panel(panel_list, width, height, depth, quantity):
    new_panel = {"Panel Width (mm)": width, "Panel Height (mm)": height, "Panel Depth (mm)": depth, "Quantity": quantity}
    panel_list = panel_list.append(new_panel, ignore_index=True)
    return panel_list

# Arrange panels into sheets
def arrange_panels(sheet_width, sheet_height, panel_list):
    panels = []
    for _, row in panel_list.iterrows():
        for _ in range(int(row["Quantity"])):
            panels.append((row["Panel Width (mm)"], row["Panel Height (mm)"], row["Panel Depth (mm)"]))

    panels.sort(key=lambda x: x[0]*x[1], reverse=True)

    sheets = []
    current_sheet = []
    x_cursor, y_cursor = 0, 0
    row_height = 0

    for width, height, depth in panels:
        placed = False

        if x_cursor + width <= sheet_width and y_cursor + height <= sheet_height:
            current_sheet.append((x_cursor, y_cursor, width, height, depth, False))
            x_cursor += width
            row_height = max(row_height, height)
            placed = True

        elif x_cursor + height <= sheet_width and y_cursor + width <= sheet_height:
            current_sheet.append((x_cursor, y_cursor, height, width, depth, True))
            x_cursor += height
            row_height = max(row_height, width)
            placed = True

        else:
            x_cursor = 0
            y_cursor += row_height
            row_height = 0

            if y_cursor + height <= sheet_height:
                current_sheet.append((x_cursor, y_cursor, width, height, depth, False))
                x_cursor += width
                row_height = max(row_height, height)
                placed = True
            elif y_cursor + width <= sheet_height:
                current_sheet.append((x_cursor, y_cursor, height, width, depth, True))
                x_cursor += height
                row_height = max(row_height, width)
                placed = True

        if not placed:
            sheets.append(current_sheet)
            current_sheet = []
            x_cursor, y_cursor, row_height = 0, 0, 0
            current_sheet.append((x_cursor, y_cursor, width, height, depth, False))
            x_cursor += width
            row_height = height

    sheets.append(current_sheet)
    return sheets

# Draw cutting layouts
def draw_cutting_layouts(sheet_width, sheet_height, sheets):
    images = []
    for idx, sheet in enumerate(sheets):
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.set_xlim(0, sheet_width)
        ax.set_ylim(0, sheet_height)
        ax.invert_yaxis()
        ax.set_aspect('equal')
        ax.set_title(f'Sheet {idx + 1}')

        for (x, y, w, h, d, rotated) in sheet:
            rect = patches.Rectangle((x, y), w, h, linewidth=1, edgecolor='black', facecolor='lightblue')
            ax.add_patch(rect)
            ax.text(x + w/2, y + h/2, f'{int(w)}×{int(h)}', ha='center', va='center', fontsize=6)

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        images.append(buf)
        plt.close(fig)

    return images

# Create CSV export
def export_csv(panel_list):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Panel Width (mm)", "Panel Height (mm)", "Panel Depth (mm)", "Quantity"])
    for _, row in panel_list.iterrows():
        writer.writerow(row.tolist())
    output.seek(0)
    return output

# Create PDF export
def export_pdf(summary_text):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in summary_text.strip().split('\n'):
        pdf.cell(0, 10, line.strip(), ln=True)
    output = io.BytesIO()
    pdf.output(output)
    output.seek(0)
    return output

# Placeholder function for optimization
def optimize_cutting(sheet_width, sheet_height, panel_list):
    sheets = arrange_panels(sheet_width, sheet_height, panel_list)
    images = draw_cutting_layouts(sheet_width, sheet_height, sheets)

    total_panels = panel_list["Quantity"].sum()
    total_panel_area = ((panel_list["Panel Width (mm)"] * panel_list["Panel Height (mm)"] * panel_list["Quantity"]).sum()) / 1000000
    total_sheet_area = sheet_width * sheet_height / 1000000 * len(sheets)
    waste_area = total_sheet_area - total_panel_area
    utilization = (total_panel_area / total_sheet_area) * 100

    summary = f"""
    **Materials Summary**
    - Total Panels Required: {total_panels}
    - Total Sheets Used: {len(sheets)}
    - Total Plywood Area Used: {total_panel_area:.2f} m²
    - Material Utilization: {utilization:.2f}%
    - Waste Area: {waste_area:.2f} m²
    - Waste Percentage: {100 - utilization:.2f}%
    """

    csv_file = export_csv(panel_list)
    pdf_file = export_pdf(summary)

    return summary, images, csv_file, pdf_file

with gr.Blocks(title="Compact Plywood Cutting Optimizer") as demo:
    gr.Markdown("# 📆 Compact Plywood Cutting Optimizer")
    gr.Markdown("Optimize plywood sheet cutting for panel layouts")

    panel_list = gr.State(initialize_panel_list())

    with gr.Row():
        with gr.Column():
            gr.Markdown("## 📄 Project Specifications")
            sheet_width = gr.Number(label="Plywood Sheet Width (mm)", value=2440)
            sheet_height = gr.Number(label="Plywood Sheet Height (mm)", value=1220)
            panel_width = gr.Number(label="Panel Width (mm)")
            panel_height = gr.Number(label="Panel Height (mm)")
            panel_depth = gr.Number(label="Panel Depth (mm)")
            quantity = gr.Number(label="Quantity", value=1)
            add_panel_btn = gr.Button("+ Add Panel")
        with gr.Column():
            gr.Markdown("## 📄 Project Overview")
            panel_table = gr.Dataframe(headers=["Panel Width (mm)", "Panel Height (mm)", "Panel Depth (mm)", "Quantity"], datatype=["number", "number", "number", "number"], label="Panels Added")

    optimize_btn = gr.Button("🚀 Optimize Cutting Plan")
    optimization_summary = gr.Markdown("")
    layout_gallery = gr.Gallery(label="Cutting Layouts", show_label=True)
    csv_file_output = gr.File(label="Download Cutting List (CSV)")
    pdf_file_output = gr.File(label="Download Summary (PDF)")

    add_panel_btn.click(
        fn=add_panel,
        inputs=[panel_list, panel_width, panel_height, panel_depth, quantity],
        outputs=[panel_list, panel_table]
    )

    optimize_btn.click(
        fn=optimize_cutting,
        inputs=[sheet_width, sheet_height, panel_list],
        outputs=[optimization_summary, layout_gallery, csv_file_output, pdf_file_output]
    )

if __name__ == "__main__":
    demo.launch()
