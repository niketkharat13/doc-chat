import pymupdf
from langchain_core.documents import Document


def load_pdf(file_path: str) -> list[Document]:
    pdf = pymupdf.open(file_path)

    documents = []

    for page_number, page in enumerate(pdf):
        tabs = page.find_tables()
        table_bboxes = [pymupdf.Rect(t.bbox) for t in tabs.tables]
        blocks = page.get_text("blocks")
        text_parts = []
        for b in blocks:
            block_rect = pymupdf.Rect(b[:4])
            if not any(block_rect.intersects(tb) for tb in table_bboxes):
                text_parts.append(b[4])
        text_ = "\n".join(text_parts).strip()
        tables_md = []
        for table in tabs.tables:
            try:
                df = table.to_pandas()
                if not df.empty and df.shape[1] > 1:
                    tables_md.append(df.to_markdown(index=False))
            except Exception as e:
                print(f"Page {page_number+1}: table extraction failed - {e}")

        combined_parts = [p for p in [text_] + tables_md if p]
        combined_content = "\n\n".join(combined_parts)
        print(combined_content)
        if combined_content.strip():
            documents.append(
                Document(
                    page_content=combined_content,
                    metadata={
                        "source": file_path,
                        "page": page_number + 1,
                        "has_tables": len(tabs.tables) > 0,
                    },
                )
            )

    pdf.close()
    return documents