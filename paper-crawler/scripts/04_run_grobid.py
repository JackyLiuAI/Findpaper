import os
from pathlib import Path

from grobid_client.grobid_client import GrobidClient


def main():
    pdf_dir = Path("data/raw/pdf")
    out_dir = Path("data/parsed/grobid")
    out_dir.mkdir(parents=True, exist_ok=True)

    if not any(pdf_dir.glob("*.pdf")):
        raise SystemExit("No PDFs found in data/raw/pdf. Run 03_download_pdf.py first.")

    grobid_url = os.environ.get("GROBID_URL", "http://localhost:8070")
    client = GrobidClient(
        config={
            "grobid_server": grobid_url,
            "batch_size": 8,
            "sleep_time": 5,
            "timeout": 120,
        }
    )

    # GrobidClient writes TEI XML files directly to the output directory.
    client.process(
        service="processFulltextDocument",
        input_path=str(pdf_dir),
        output=str(out_dir),
        n=0,  # process all
        generateIDs=True,
        consolidate_header=True,
        consolidate_citations=False,
        force=True,
    )


if __name__ == "__main__":
    main()
