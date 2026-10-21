from lxml import etree
from pathlib import Path
import json


def main():
    xml_dir = Path("data/parsed/grobid")
    out = Path("data/parsed/papers.jsonl")
    out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as fw:
        for xml_path in xml_dir.glob("*.xml"):
            tree = etree.parse(str(xml_path))
            ns = {"tei": "http://www.tei-c.org/ns/1.0"}

            sections = {}
            for div in tree.xpath("//tei:div", namespaces=ns):
                head = div.find("tei:head", namespaces=ns)
                if head is None:
                    continue
                title = head.text.lower() if head.text else ""
                text = " ".join(div.xpath(".//tei:p//text()", namespaces=ns))
                sections[title] = text

            fw.write(
                json.dumps({"paper_id": xml_path.stem, "sections": sections}, ensure_ascii=False)
                + "\n"
            )


if __name__ == "__main__":
    main()
