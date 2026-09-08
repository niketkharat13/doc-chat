import re
import pymupdf
import pandas as pd
from langchain_core.documents import Document


def clean_text(text: str) -> str:
    """
    Aggressively clean PDF extracted text.
    """

    if not text:
        return ""

    # Replace non-breaking spaces
    text = text.replace("\xa0", " ")

    # Replace tabs
    text = text.replace("\t", " ")

    # Remove spaces before/after newlines
    text = re.sub(r"[ ]*\n[ ]*", "\n", text)

    # Collapse multiple spaces
    text = re.sub(r"[ ]{2,}", " ", text)

    # Collapse multiple newlines
    text = re.sub(r"\n{2,}", "\n", text)

    # Remove leading/trailing whitespace
    text = text.strip()

    return text


def clean_table(df: pd.DataFrame) -> str:

    # Replace NaN with empty string
    df = df.fillna("")

    def clean_cell(value):
        if value is None:
            return ""
        value = str(value)
        # Replace non-breaking spaces
        value = value.replace("\xa0", " ")
        # Replace tabs/newlines with spaces
        value = re.sub(r"[\t\r\n]+", " ", value)
        # Collapse ALL multiple spaces
        value = re.sub(r"\s+", " ", value)
        return value.strip()
    # Clean every cell
    df = df.map(clean_cell)
    # Remove completely empty rows
    df = df.loc[~(df == "").all(axis=1)]
    # Remove completely empty columns
    df = df.loc[:, ~(df == "").all(axis=0)]
    if df.empty:
        return ""
    # Convert to markdown
    markdown = df.to_markdown(
        index=False
    )
    # IMPORTANT:
    # Clean the generated markdown too
    markdown = clean_text(markdown)
    return markdown


def load_pdf(file_path: str) -> list[Document]:
    pdf = pymupdf.open(file_path)
    documents = []
    for page_number, page in enumerate(pdf):
        # Find tables
        tabs = page.find_tables()
        table_bboxes = [
            pymupdf.Rect(table.bbox)
            for table in tabs.tables
        ]
        # Extract normal text
        blocks = page.get_text("blocks")
        text_parts = []
        for block in blocks:
            block_rect = pymupdf.Rect(block[:4])
            # Ignore text inside tables
            if not any(
                block_rect.intersects(table_bbox)
                for table_bbox in table_bboxes
            ):
                text = clean_text(block[4])
                if text:
                    text_parts.append(text)
        text_ = "\n".join(text_parts)
        # Extract tables
        tables_md = []
        for table in tabs.tables:
            try:
                df = table.to_pandas()
                if df.empty or df.shape[1] <= 1:
                    continue
                cleaned_table = clean_table(df)
                if cleaned_table:
                    tables_md.append(cleaned_table)
            except Exception as e:
                print(
                    f"Page {page_number + 1}: "
                    f"table extraction failed - {e}"
                )
        # Combine
        combined_parts = [
            part
            for part in [text_] + tables_md
            if part.strip()
        ]
        combined_content = "\n\n".join(combined_parts)
        # Final cleanup
        combined_content = clean_text(combined_content)
        print(
            f"\n========== PAGE {page_number + 1} =========="
        )
        if combined_content:
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
