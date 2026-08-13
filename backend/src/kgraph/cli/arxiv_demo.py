import argparse

from kgraph.ingestion.arxiv import ArxivSource


def main():
    parser = argparse.ArgumentParser(
        description="Harvest papers from arXiv and preview them."
    )
    parser.add_argument(
        "--query",
        default='"chain of thought" AND "reinforcement learning"',
        help="arXiv API query (default: CoT + RL papers)",
    )
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument(
        "--download-dir",
        default="data/arxiv_pdfs",
        help="Folder where full-text PDFs are saved",
    )
    parser.add_argument(
        "--fulltext",
        action="store_true",
        help="Download and parse the PDFs (docling) instead of using the abstract",
    )
    args = parser.parse_args()

    source = ArxivSource(query=args.query, max_results=args.max_results)

    if args.fulltext:
        docs = source.fetch_fulltext(download_dir=args.download_dir)
        print(f"Parsed {len(docs)} full-text documents from arXiv")
        print(f"Saved PDFs + parsed .md to {args.download_dir}/")
    else:
        docs = source.fetch()
        print(f"Fetched {len(docs)} documents from arXiv")
        print(f"PDFs cached in {args.download_dir} (use --fulltext to parse them)")

    for i, doc in enumerate(docs, 1):
        m = doc.metadata
        print(f"\n[{i}] {m['title']}")
        print(f"    id: {m['arxiv_id']}  ({m['primary_category']})")
        print(f"    authors: {', '.join(m['authors'][:5])}")
        print(f"    published: {m['published'][:10]}")
        print(f"    url: {m['url']}")
        preview = " ".join(doc.content.split())
        print(f"    content: {preview[:200]}...")


if __name__ == "__main__":
    main()
