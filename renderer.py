from docxtpl import DocxTemplate


def render_resume(data: dict, template_path: str, output_path: str):
    doc = DocxTemplate(template_path)
    doc.render(data)
    doc.save(output_path)