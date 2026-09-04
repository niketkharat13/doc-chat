from langchain_text_splitters import HTMLHeaderTextSplitter


def split_html(html: str):

    headers_to_split_on = [
        ("h1", "Header 1"),
        ("h2", "Header 2"),
        ("h3", "Header 3"),
        ("h4", "Header 4"),
        ("h5", "Header 5"),
        ("h6", "Header 6"),
    ]


    splitter = HTMLHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on
    )

    documents = splitter.split_text(html)

    return documents