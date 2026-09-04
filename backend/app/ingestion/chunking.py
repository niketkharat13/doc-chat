from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
import logging
from typing import List
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def split_documents(chunking_size, chunking_overlap, documents: List[Document]) -> List[Document]:
    """
    Splits the input text into chunks of specified size and overlap.

    Args:
        chunking_size (int): The maximum size of each chunk.
        chunking_overlap (int): The number of characters to overlap between chunks.
        documents (List[Document]): The list of documents to be split into chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunking_size,
        chunk_overlap=chunking_overlap,
        separators=["\n\n", "\n", " ", ""],
    )
    return text_splitter.split_documents(documents)