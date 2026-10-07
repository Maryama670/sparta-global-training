from pathlib import Path


KNOWLEDGE_DIR = Path(__file__).parent / "knowledge"


def load_documents():
    documents = []

    for file_path in KNOWLEDGE_DIR.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")

        lines = content.splitlines()

        document_id = ""
        title = ""
        document_type = ""
        date = ""

        for line in lines[:10]:
            if line.startswith("ID:"):
                document_id = line.replace("ID:", "").strip()

            elif line.startswith("Title:"):
                title = line.replace("Title:", "").strip()

            elif line.startswith("Type:"):
                document_type = line.replace("Type:", "").strip()

            elif line.startswith("Date:"):
                date = line.replace("Date:", "").strip()

        documents.append(
            {
                "id": document_id,
                "title": title,
                "text": content,
                "type": document_type,
                "date": date,
            }
        )

    return documents